# -*- coding: utf-8 -*-

"""Database operations handling module."""

import sys
import logging
import psycopg2
from socket import gethostname
from time import sleep
from contextlib import contextmanager


from ..conf import CONF

LOG = logging.getLogger(__name__)


######################################
#          DB connection             #
######################################

class DBConnection():
    """Databse connection setup."""

    conn = None
    curr = None
    args = None
    interval = None
    attempts = None

    def __init__(self, conf_section='db', on_failure=None):
        """
        Initialize config section parameters for DB and failure fallback.

        :param conf_section: Section in the configuration file, defaults to 'db'
        :type conf_section: str, optional
        :param on_failure: A callable object to be called in case of failure, defaults to None
        :type on_failure: callable object, optional
        """
        self.on_failure = on_failure
        self.conf_section = conf_section or 'db'

    def fetch_args(self):
        """Fetch arguments for initializing a connection to db."""
        self.args = CONF.get_value(self.conf_section, 'connection')
        self.interval = CONF.get_value(self.conf_section, 'try_interval', conv=int, default=1)
        self.attempts = CONF.get_value(self.conf_section, 'try', conv=int, default=1)
        assert self.attempts > 0, "The number of reconnection should be >= 1"

    def connect(self, force=False):
        """
        Get the database connection (which encapsulates a database session).

        Upon success, the connection is cached.

        Before success, we try to connect ``try`` times every ``try_interval`` seconds (defined in CONF)
        Executes ``on_failure`` after ``try`` attempts.

        :param force: Whether to force a new connection or not, defaults to False
        :type force: bool, optional
        """
        if force:
            self.close()

        if self.conn and self.curr:
            return

        if not self.args:
            self.fetch_args()

        LOG.info("Initializing a connection (%d attempts)", self.attempts)

        backoff = self.interval
        for count in range(self.attempts):
            try:
                LOG.debug("Connection attempt %d", count)
                self.conn = psycopg2.connect(self.args)
                # self.conn.set_session(autocommit=True) # default is False.
                LOG.debug("Connection successful")
                return
            except psycopg2.OperationalError as e:
                LOG.debug("Database connection error: %r", e)
            except psycopg2.InterfaceError as e:
                LOG.debug("Invalid connection parameters: %r", e)
                break
            sleep(backoff)
            backoff = (2 ** (count // 10)) * self.interval
            # from  0 to  9, sleep 1 * self.interval secs
            # from 10 to 19, sleep 2 * self.interval secs
            # from 20 to 29, sleep 4 * self.interval secs ... etc

        # fail to connect
        if self.on_failure and callable(self.on_failure):
            LOG.error("Failed to connect.")
            self.on_failure()

    def ping(self):
        """Ping DB connection."""
        if self.conn is None:
            self.connect()
        try:
            with self.conn:
                with self.conn.cursor() as cur:  # does not commit if error raised
                    cur.execute('SELECT 1;')
                    LOG.debug("Ping db successful")
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            LOG.debug('Ping failed: %s', e)
            self.connect(force=True)  # reconnect

    @contextmanager
    def cursor(self):
        """
        Return DB Cursor, thus reusing it.

        :yield: A cursor to execute PostgreSQL commands in a database session
        :rtype: psycopg2.extensions.cursor
        """
        self.ping()
        with self.conn:
            with self.conn.cursor() as cur:
                yield cur
                # closes cursor on exit
            # transaction autocommit, but connection not closed

    def close(self):
        """Close DB Connection."""
        LOG.debug("Closing the database")
        if self.curr:
            self.curr.close()
            self.curr = None
        if self.conn:
            self.conn.close()
            self.conn = None

    # Note, the code does not close the database connection nor the cursor
    # if everything goes fine.


# Instantiate the global connection
connection = DBConnection(on_failure=lambda: sys.exit(1))


######################################
#           Business logic           #
######################################


def insert_file(filename, user_id):
    """
    Insert a new file entry and returns its id.

    :param filename: Name of the file to be inserted
    :type filename: str
    :param user_id: Id of the user inserting the file
    :type user_id: str
    :raises Exception: Error when attempting to insert a file
    :return: The file id assigned to the file
    :rtype: str
    """
    with connection.cursor() as cur:
        cur.execute('SELECT local_ega.insert_file(%(filename)s,%(user_id)s);',
                    {'filename': filename,
                     'user_id': user_id})
        file_id = (cur.fetchone())[0]
        if file_id:
            LOG.debug('Created id %s for %s', file_id, filename)
            return file_id
        raise Exception('Database issue with insert_file')


def set_file_encrypted_checksum(file_id, encrypted_checksum, encrypted_checksum_type):
    """
    Insert encrypted checksum.

    :param file_id: The id of the file to set the checksum
    :type file_id: str
    :param encrypted_checksum: The encrypted hash of the file
    :type encrypted_checksum: str
    :param encrypted_checksum_type: Checksum type used
    :type encrypted_checksum_type: str
    """
    with connection.cursor() as cur:
        cur.execute('UPDATE local_ega.files '
                    'SET inbox_file_checksum = %(encrypted_checksum)s, '
                    '    inbox_file_checksum_type = %(encrypted_checksum_type)s'
                    'WHERE id = %(file_id)s;',
                    {'encrypted_checksum': encrypted_checksum,
                     'encrypted_checksum_type': encrypted_checksum_type.upper(),
                     'file_id': file_id})


def set_error(file_id, error, from_user=False):
    """
    Store and fetch errors related to ``file_id`` in database.

    :param file_id: The id of the file to set an error
    :type file_id: str
    :param error: object representing an error message
    :type error: object
    :param from_user: Whether it is an user error or not, defaults to False
    :type from_user: bool, optional
    :return: List of tuples containing the fetched records
    :rtype: list(tuple)
    """
    assert file_id, 'Eh? No file_id?'
    assert error, 'Eh? No error?'
    LOG.debug('Setting error for %s: %s | Cause: %s', file_id, error, error.__cause__)
    hostname = gethostname()
    with connection.cursor() as cur:
        cur.execute('SELECT * FROM local_ega.insert_error(%(file_id)s,%(h)s,%(etype)s,%(msg)s,%(from_user)s);',
                    {'h': hostname,
                     'etype': error.__class__.__name__,
                     'msg': repr(error),
                     'file_id': file_id,
                     'from_user': from_user})
        return cur.fetchall()


def get_info(file_id):
    """
    Retrieve information for ``file_id``.

    :param file_id: The id of the file to get info from
    :type file_id: str
    :return: A tuple containing the fetched record
    :rtype: tuple
    """
    with connection.cursor() as cur:
        query = 'SELECT inbox_path, archive_path, stable_id, header from local_ega.files WHERE id = %(file_id)s;'
        cur.execute(query, {'file_id': file_id})
        return cur.fetchone()


def get_header(file_id):
    """Retrieve information for ``file_id``."""
    with connection.cursor() as cur:
        query = 'SELECT header from local_ega.files WHERE id = %(file_id)s;'
        cur.execute(query, {'file_id': file_id})
        return cur.fetchone()


def mark_in_progress(file_id):
    """
    Mark file in progress.

    :param file_id: The id of the file to mark in progress
    :type file_id: str
    """
    LOG.debug('Marking file_id %s with "IN_INGESTION"', file_id)
    assert file_id, 'Eh? No file_id?'
    with connection.cursor() as cur:
        cur.execute('UPDATE local_ega.files SET status = %(status)s WHERE id = %(file_id)s;',
                    {'status': 'IN_INGESTION',
                     'file_id': file_id})


def set_stable_id(filepath, user, decrypted_checksum, stable_id):
    """
    Update File with stable ID.

    :param filepath: Target file path
    :type filepath: str
    :param user: User who submitted the file
    :type user: str
    :param decrypted_checksum: Decrypted checksum of the file
    :type decrypted_checksum: str
    :param stable_id: Accession id or stable id assigned to the file
    :type stable_id: str
    """
    LOG.debug('Updating filepath %s for user %s with stable ID "%s"', filepath, user, stable_id)
    with connection.cursor() as cur:
        cur.execute('UPDATE local_ega.files '
                    'SET status = %(status)s, '
                    '    stable_id = %(stable_id)s '
                    'WHERE elixir_id = %(user)s AND inbox_path = %(filepath)s '
                    ' AND archive_file_checksum = %(decrypted_checksum)s'
                    ' AND status != %(disabled)s;',
                    {'status': 'READY',
                     'user': user,
                     'stable_id': stable_id,
                     'filepath': filepath,
                     'decrypted_checksum': decrypted_checksum,
                     # The completed status is to avoid DISABLED file
                     # ingested twice with same checksum and file id and path
                     'disabled': 'DISABLED'})


def store_header(file_id, header):
    """
    Store header for ``file_id``.

    :param file_id: The id of the file to store the header
    :type file_id: str
    :param header: The header of the file
    :type header: str
    """
    assert file_id, 'Eh? No file_id?'
    assert header, 'Eh? No header?'
    LOG.debug('Store header for file_id %s', file_id)
    with connection.cursor() as cur:
        cur.execute('UPDATE local_ega.files '
                    'SET header = %(header)s '
                    'WHERE id = %(file_id)s;',
                    {'file_id': file_id,
                     'header': header})


def set_archived(file_id, archive_path, archive_filesize):
    """
    Archive ``file_id``.

    :param file_id: The id of the file to set as archived
    :type file_id: str
    :param archive_path: Archive path of the file to set as archived
    :type archive_path: str
    :param archive_filesize: Size of the file
    :type archive_filesize: str
    """
    assert file_id, 'Eh? No file_id?'
    assert archive_path, 'Eh? No archive name?'
    LOG.debug('Setting status to archived for file_id %s', file_id)
    with connection.cursor() as cur:
        cur.execute('UPDATE local_ega.files '
                    'SET status = %(status)s, '
                    '    archive_path = %(archive_path)s, '
                    '    archive_filesize = %(archive_filesize)s '
                    'WHERE id = %(file_id)s;',
                    {'status': 'ARCHIVED',
                     'file_id': file_id,
                     'archive_path': archive_path,
                     'archive_filesize': archive_filesize})


def check_session_keys_checksums(session_key_checksums):
    """
    Check if this session key is (likely) already used.

    :param session_key_checksums: Session key checksum to check against
    :type session_key_checksums: str
    :return: Whether the session keys were found or not
    :rtype: bool
    """
    assert session_key_checksums, 'Eh? No checksum for the session keys?'
    LOG.debug('Check if session keys (hash) are already used: %s', session_key_checksums)
    with connection.cursor() as cur:
        cur.execute('SELECT * FROM local_ega.check_session_keys_checksums_sha256(%(sk_checksums)s);',
                    {'sk_checksums': session_key_checksums})
        found = cur.fetchone()
        LOG.debug("Check session keys: %s", found)
        return (found and found[0])  # not none and check boolean value


def mark_completed(file_id, session_key_checksums, digest_sha256):
    """
    Mark file as completed.

    :param file_id: The id of the file to set as completed
    :type file_id: str
    :param session_key_checksums: Session key checksum
    :type session_key_checksums: str
    :param digest_sha256: sha256 digest of the file
    :type digest_sha256: str
    """
    LOG.debug('Marking file_id %s with "COMPLETED"', file_id)
    assert file_id, 'Eh? No file_id?'
    with connection.cursor() as cur:
        cur.execute('UPDATE local_ega.files '
                    'SET status = %(status)s, '
                    '    archive_file_checksum = %(archive_file_checksum)s, '
                    '    archive_file_checksum_type = %(archive_file_checksum_type)s '
                    'WHERE id = %(file_id)s;',
                    {'status': 'COMPLETED',
                     'file_id': file_id,
                     'archive_file_checksum': digest_sha256,
                     'archive_file_checksum_type': 'SHA256'})
        cur.executemany('INSERT INTO local_ega.session_key_checksums_sha256 '
                        '            (file_id, session_key_checksum) '
                        'VALUES (%s, %s);',
                        [(file_id, c) for c in session_key_checksums])
        # Note: no data-race is file status is DISABLED or ERROR


# Testing connection with `python -m lega.utils.db`
if __name__ == '__main__':
    CONF.setup()
    with connection.cursor() as cur:
        query = 'SELECT inbox_path, archive_path, stable_id, header from local_ega.files;'
        cur.execute(query)
        names = ('inbox_path', 'archive_path', 'stable_id', 'header')
        for row in cur.fetchall():
            res = [f'{k}: {v}' for k, v in zip(names, row)]
            print('-'*30)
            print(res)
