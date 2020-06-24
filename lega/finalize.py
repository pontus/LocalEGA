#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Consumes messages to update the database with stable IDs to file IDS mappings.

It also sends a message to files.completed to mark a file as completed in the CEGA side.

Messages can be delivered to a local broker by registering an upstream queue.

"""

import sys
import logging

from .conf import CONF
from .utils import db, errors
from .utils.amqp import consume

LOG = logging.getLogger(__name__)


@errors.catch(ret_on_error=(None, True))
def work(data):
    """
    Read a message containing the ids and add it to the database.

    :param data: a dictionary containing the stable id, user, file checksum and file path
    :type data: dict
    :return: A tuple indicating the stable id has been mapped.
    :rtype: tuple
    """

    filepath = data['filepath']
    user = data['user']
    checksum_data = list(filter(lambda x : x['type'] == 'sha256', data['decrypted_checksums']))
    decrypted_checksum = checksum_data[0]['value']
    stable_id = data['accession_id']
    LOG.info("Mapping file with path %s and checksum %s to stable_id %s", filepath, decrypted_checksum, stable_id)

    # Remove file from the inbox
    # TODO

    db.set_stable_id(filepath, user, decrypted_checksum, stable_id)  # That will flag the entry as 'Ready'

    LOG.info("Stable ID %s mapped to %s", stable_id, filepath)
 
    # Send message to mark file as completed on the CEGA side
    completed_data = data
    completed_data.pop("type", None)
    LOG.info(f"Reply message to files.completed: {completed_data}")

    return (completed_data, False)

def main(args=None):
    """
    Consume incoming stable IDs from the local broker.

    :param args: Service configuration arguments, defaults to None
    :type args: list, optional
    """
    if not args:
        args = sys.argv[1:]

    CONF.setup(args)  # re-conf

    # upstream link configured in local broker
    consume(work, 'stableIDs', 'completed')


if __name__ == '__main__':
    main()
