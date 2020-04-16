#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Worker reading messages from the ``files`` queue, splitting the Crypt4GH header from the remainder of the file.

The header is stored in the database and the remainder is sent to the backend storage:
either a regular file system or an S3 object store.

It is possible to start several workers.

When a message is consumed, it must at least contain the following fields:

* ``filepath``
* ``user_id``

Upon completion, a message is sent to the local exchange with the
routing key :``archived``.
"""

import sys
import logging
from functools import partial
import io
import hashlib

from crypt4gh import header

from .conf import CONF
from .utils import db, exceptions, errors, sanitize_user_id, storage
from .utils.amqp import consume

LOG = logging.getLogger(__name__)


def get_header(input_file):
    """Extract the header bytes, and leave the ``input_file`` file handle at the beginning of the data portion."""
    _ = list(header.parse(input_file))
    pos = input_file.tell()
    input_file.seek(0, io.SEEK_SET)  # rewind
    return input_file.read(pos)
    # That's ok to rewind, we are not reading a stream
    # Alternatively, get the packets and recombine them
    # header_packets = header.parse(input_file)
    # return header.serialize(header_packets)


@errors.catch(ret_on_error=(None, True))
def work(fs, inbox_fs, data):
    """Read a message, split the header and send the remainder to the backend store."""
    filepath = data['filepath']
    LOG.info('Processing %s', filepath)

    # Remove the host part of the user name
    user_id = sanitize_user_id(data['user'])

    # Keeping data as-is (cuz the decorator is using it)
    # It will be augmented, but we keep the original data first
    org_msg = data.copy()
    data['org_msg'] = org_msg

    # this uses a function to set the filepath and user_id
    # in order to set the encrypted key we will do an update based on them
    file_id = db.insert_file(filepath, user_id)

    data['file_id'] = file_id  # must be there: database error uses it

    # we will be working with sha256 only and let us see if we get in the message this for now
    # if this is not present we will calculate it
    file_checksum = []
    if 'encrypted_checksums' in data:
        file_checksum = [item for item in data['encrypted_checksums'] if item.get('type') == 'sha256']

    # Instantiate the inbox backend
    inbox = inbox_fs(user_id)
    LOG.info("Inbox backend: %s", str(inbox))

    # Check if file is in inbox
    if not inbox.exists(filepath):
        raise exceptions.NotFoundInInbox(filepath)  # return early

    # Ok, we have the file in the inbox

    # Record in database
    db.mark_in_progress(file_id)

    sha = hashlib.sha256()
    # Strip the header out and copy the rest of the file to the archive
    LOG.debug('Opening %s', filepath)
    with inbox.open(filepath, 'rb') as infile:
        LOG.debug('Reading header | file_id: %s', file_id)

        # if it is not provided in the message let us calculate the checksum
        if not file_checksum:
            file_buffer = infile.read(65536)
            while len(file_buffer) > 0:
                sha.update(file_buffer)
                file_buffer = infile.read(65536)

        # return to start of file
        infile.seek(0)

        header_bytes = get_header(infile)
        header_hex = header_bytes.hex()
        data['header'] = header_hex
        db.store_header(file_id, header_hex)  # header bytes will be .hex()

        target = fs.location(file_id)
        LOG.info('[%s] Moving the rest of %s to %s', fs.__class__.__name__, filepath, target)
        target_size = fs.copy(infile, target)  # It will copy the rest only

        LOG.info('Archive copying completed. Updating database')
        db.set_archived(file_id, target, target_size)
        data['archive_path'] = target

    if not file_checksum:
        encrypted_checksum = sha.hexdigest()
        encrypted_checksum_type = 'sha256'
        LOG.debug("calculated encrypted file checksum: %s", encrypted_checksum)
    else:
        encrypted_checksum = file_checksum[0]['value']
        encrypted_checksum_type = file_checksum[0]['type']
        LOG.debug("file checksum from message: %s", encrypted_checksum)

    # No need to pass this arround as this is registered in the db
    data.pop('encrypted_checksums', None)

    # Keep it in the messages to indentify the file
    data['file_checksum'] = encrypted_checksum
    # Insert in database
    db.set_file_encrypted_checksum(file_id, encrypted_checksum, encrypted_checksum_type)

    LOG.debug("Reply message: %s", data)
    return (data, False)


def setup_archive():
    """Configure the archive backend."""
    archive_fs = getattr(storage, CONF.get_value('archive', 'storage_driver', default='FileStorage'))
    fs_path = None
    if archive_fs is storage.FileStorage:
        fs_path = CONF.get_value('archive', 'user')
    elif archive_fs is storage.S3Storage:
        fs_path = CONF.get_value('archive', 's3_bucket')

    return archive_fs('archive', fs_path)


def setup_inbox():
    """Configure the inbox backend."""
    inbox_fs = getattr(storage, CONF.get_value('inbox', 'storage_driver', default='FileStorage'))

    inbox = None
    if inbox_fs is storage.FileStorage:
        inbox = partial(inbox_fs, 'inbox')
    elif inbox_fs is storage.S3Storage:
        inbox = partial(inbox_fs, 'inbox', CONF.get_value('inbox', 's3_bucket'))

    return inbox


def main(args=None):
    """Run ingest service."""
    if not args:
        args = sys.argv[1:]

    CONF.setup(args)  # re-conf

    archive = setup_archive()
    inbox = setup_inbox()

    do_work = partial(work, archive, inbox)

    # upstream link configured in local broker
    consume(do_work, 'files', 'archived')


if __name__ == '__main__':
    main()
