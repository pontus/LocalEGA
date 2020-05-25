# -*- coding: utf-8 -*-

"""File I/O for disk or S3 Object storage."""

import os
import io
import logging
from contextlib import contextmanager
import shutil
from pathlib import Path

from ..conf import CONF

LOG = logging.getLogger(__name__)


class FileStorage():
    """Storage on disk and related I/O."""

    def __init__(self, config_section, user):
        """
        Initialize backend storage to a POSIX file system.

        :param config_section: Section in the configuration file
        :type config_section: str
        :param user: User of the POSIX file system
        :type user: str
        """
        self.prefix = (CONF.get_value(config_section, 'location', raw=True) % user).rstrip('/')
        self.separator = CONF.get_value(config_section, 'separator', raw=True)

    def location(self, file_id):
        """
        Retrieve file location.

        :param file_id: Id of the file to locate in the file system
        :type file_id: str
        :return: The location of the file
        :rtype: str
        """
        name = f"{file_id:0>20}"  # filling with zeros, and 20 characters wide
        name_bits = [name[i:i+3] for i in range(0, len(name), 3)]
        target = Path('/').joinpath(*name_bits)
        return str(target)

    def filesize(self, path):
        """
        Return the size of the file pointed by ``path``.

        :param path: File path
        :type path: str
        :return: File size
        :rtype: int
        """
        return os.stat(Path(self.prefix + self.separator + path.lstrip('/'))).st_size

    def copy(self, fileobj, location):
        """
        Copy file object at a specific location.

        :param fileobj: File object
        :type fileobj: file
        :param location: Target file object location
        :type location: str
        :return: File size of file at location
        :rtype: int
        """
        target = Path(self.prefix + self.separator + location.lstrip('/'))
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'wb') as h:
            shutil.copyfileobj(fileobj, h)
        return self.filesize(location)

    @contextmanager
    def open(self, path, mode='rb'):
        """
        Open stored file.

        :param path: Path to the file
        :type path: str
        :param mode: File opening mode, defaults to 'rb'
        :type mode: str, optional
        :yield: The specified file
        :rtype: file
        """
        fp = Path(self.prefix + self.separator + path.lstrip('/'))
        f = open(fp, mode)
        yield f
        f.close()

    def exists(self, filepath):
        """
        Return true if the path exists.

        :param filepath: Path to the file
        :type filepath: str
        :return: Whether the file path exists or not
        :rtype: bool
        """
        fp = Path(self.prefix + self.separator + filepath.lstrip('/'))
        return fp.exists()

    def __str__(self):
        """
        Return inbox prefix.

        :return: The prefix of the inbox
        :rtype: str
        """
        return str(self.prefix)


class S3FileReader(object):
    """
    Implements a few of the BufferedIOBase methods.

    see https://docs.python.org/3/library/io.html#io.BufferedIOBase
    """

    def __init__(self, s3, bucket, path, mode='rb', blocksize=1 << 22):  # 1<<22 = 4194304 = 4MB
        """
        Create a S3 file reader object.

        :param s3: boto S3 client object
        :type s3: botocore.client.S3
        :param bucket: S3 bucket
        :type bucket: str
        :param path: Path to read within the bucket
        :type path: str
        :param mode: File opening mode, defaults to 'rb'
        :type mode: str, optional
        :param blocksize: Maximum block size to fetch at a time, defaults to 1<<22
        :type blocksize: int, optional
        :raises NotImplementedError: File opening mode not supported
        """
        if mode != 'rb':  # if mode not in ('rb', 'wb', 'ab'):
            raise NotImplementedError(f"File mode '{mode}' not supported")
        self.mode = mode
        self.path = path
        self.s3 = s3
        self.loc = 0
        self.start = None
        self.end = None
        self.closed = False
        self.bucket = bucket
        self.info = s3.head_object(Bucket=bucket, Key=path)
        self.size = self.info['ContentLength']
        # self.buffer = io.BytesIO() # cache
        # self.blocksize = blocksize
        # # If file is less than 5MB, read it all in the buffer
        # if self.size < blocksize:
        #     # existing file too small for multi-upload: download
        #     self.buffer.write(self.read())

    def tell(self):
        """
        Return position.

        :return: The position of the file reader
        :rtype: int
        """
        return self.loc

    def seek(self, loc, whence=0):
        """
        Change position to the given byte offset.

        :param loc: Position of the read/write pointer within the file
        :type loc: int
        :param whence: Search relative to, defaults to 0
        :type whence: int, optional
        :raises ValueError: Not valid whence
        :raises ValueError: Position before start of file
        :return: Current file's position
        :rtype: int
        """
        if whence == 0:  # from start
            nloc = loc
        elif whence == 1:  # from here
            nloc = self.loc + loc
        elif whence == 2:  # from end
            nloc = self.size + loc
        else:
            raise ValueError("invalid whence (%s, should be 0, 1 or 2)" % whence)
        if nloc < 0:
            raise ValueError('Seek before start of file')
        self.loc = nloc
        return self.loc

    def read(self, length=-1):
        """
        Read and return up to size bytes.

        :param length: Length of bytes to read, defaults to -1
        :type length: int, optional
        :raises ValueError: The file is closed
        :return: Specified byte range
        :rtype: bytes
        """
        if self.closed:
            raise ValueError('I/O operation on closed file.')

        if self.loc == self.size:  # at the end already
            return b''

        if length < 0:  # the rest of the file
            length = self.size - self.loc

        end = min(self.loc + length, self.size)  # in case it's too much
        out = self._fetch(self.loc, end)
        self.loc += len(out)
        return out

    def close(self):
        """Close object reader."""
        if self.closed:
            return
        self.closed = True

    def __del__(self):
        """Prepare for object destruction."""
        self.close()

    def __str__(self):
        """
        Return string representation.

        :return: String representation of S3FileReader
        :rtype: str
        """
        return f"<S3FileReader {self.path}>"

    __repr__ = __str__

    def __enter__(self):
        """Set things."""
        return self

    def __exit__(self, *args):
        """Prepare for object destruction."""
        self.close()

    # Implementations of BufferedIOBase stub methods

    def read1(self, length=-1):
        """
        Read and return up to size bytes, with at most one call to the underlying raw stream’s read().

        :param length: Length of bytes to read,, defaults to -1
        :type length: int, optional
        :return: Specified byte range
        :rtype: bytes
        """
        return self.read(length)

    def detach(self):
        """
        Raise unssuported operation.

        :raises io.UnsupportedOperation: Detaching is not supported
        """
        raise io.UnsupportedOperation()

    def readinto(self, b):
        """
        Read bytes into a pre-allocated object b and return the number of bytes read.

        :param b: Pre-allocated object
        :type b: object
        :return: Number of bytes read
        :rtype: int
        """
        datalen = len(b)
        data = self.read(datalen)
        b[:datalen] = data
        return datalen

    def readinto1(self, b):
        """
        Read bytes into an object.

        :param b: Pre-allocated object
        :type b: object
        :return: int
        :rtype: Number of bytes read
        """
        return self.readinto(b)

    def _fetch(self, start, end, max_attempts=10):
        """
        Get objects from S3.

        :param start: Start of byte range
        :type start: int
        :param end: End of byte range
        :type end: int
        :param max_attempts: Number of attempts, defaults to 10
        :type max_attempts: int, optional
        :raises RuntimeError: Objects could not be fetched from S3 after all retries
        :return: The bytes corresponding to a S3 object
        :rtype: bytes
        """
        # if end > self.size:
        #     end = self.size
        assert end <= self.size
        # LOG.debug("Fetch: Bucket: %s, File=%s, Range: %s-%s, Chunk: %s", self.bucket, self.path, start, end, end-start)
        for i in range(max_attempts):
            try:
                resp = self.s3.get_object(Bucket=self.bucket, Key=self.path, Range='bytes=%i-%i' % (start, end - 1))
                return resp['Body'].read()
            # except socket.timeout as e:
            #     LOG.debug('Exception %e on S3 download, retrying', e, exc_info=True)
            #     continue
            # except self.s3.exceptions.ClientError as e:
            #     if e.response['Error'].get('Code', 'Unknown') in ('416', 'InvalidRange'):
            #         return b''
            #     else:
            #         raise
            except Exception as e:
                LOG.debug('Exception %e', e, exc_info=True)
                if 'time' in str(e).lower():  # Actual exception type changes often
                    continue
                raise
        raise RuntimeError("Max number of S3 retries exceeded")


class S3Storage():
    """S3 object storage and related I/O."""

    def __init__(self, config_section, bucket, prefix=""):
        """
        Initialize S3 object Storage.

        :param config_section: Section in the configuration file
        :type config_section: str
        :param bucket: S3 bucket
        :type bucket: str
        :param prefix: Prefix, defaults to ""
        :type prefix: str, optional
        """
        import boto3
        import botocore
        self.endpoint = CONF.get_value(config_section, 's3_url')
        region = CONF.get_value(config_section, 's3_region')
        access_key = CONF.get_value(config_section, 's3_access_key')
        secret_key = CONF.get_value(config_section, 's3_secret_key')
        verify = CONF.get_value(config_section, 'cacertfile', default=None) or False
        config_params = {
            'connect_timeout': CONF.get_value(config_section, 'connect_timeout', conv=int, default=60),
        }
        certfile = CONF.get_value(config_section, 'certfile', default=None)
        keyfile = CONF.get_value(config_section, 'keyfile', default=None)
        if certfile and keyfile:
            config_params['client_cert'] = (certfile, keyfile)
        config = botocore.client.Config(**config_params)
        self.s3 = boto3.client('s3',
                               endpoint_url=self.endpoint,
                               region_name=region,
                               use_ssl=self.endpoint.startswith('https'),
                               verify=verify,
                               aws_access_key_id=access_key,
                               aws_secret_access_key=secret_key,
                               config=config)
        # LOG.debug('S3 client: %r', self.s3)
        try:
            LOG.debug('Creating "%s" bucket', bucket)
            self.bucket = bucket
            self.s3.create_bucket(Bucket=self.bucket)
        except self.s3.exceptions.BucketAlreadyOwnedByYou as e:
            LOG.debug('Ignoring (%s): %s', type(e), e)
        # No need to close anymore?

    def location(self, file_id):
        """
        Retrieve object location.

        :param file_id: The id of the file to get the location
        :type file_id: str
        :return: Location of the object
        :rtype: str
        """
        return str(file_id)

    def filesize(self, path):
        """
        Return the size of the file pointed by ``path``.

        :param path: Path to the file
        :type path: str
        :return: Size of the specified file
        :rtype: int
        """
        resp = self.s3.head_object(Bucket=self.bucket, Key=path)
        return resp['ContentLength']

    def copy(self, fileobj, location):
        """
        Copy file object in a bucket.

        :param fileobj: File object
        :type fileobj: file
        :param location: Target file object location
        :type location: str
        :return: File size of file at location
        :rtype: int
        """
        from boto3.s3.transfer import TransferConfig
        chunksize = int(CONF.get_value('archive', 's3_chunk_size', default=32 * 1024 * 1024))
        transfer_config = TransferConfig(multipart_threshold=chunksize, max_concurrency=10,
                                         multipart_chunksize=chunksize, use_threads=True)
        self.s3.upload_fileobj(fileobj, self.bucket, location, Config=transfer_config)
        resp = self.s3.head_object(Bucket=self.bucket, Key=location)
        return resp['ContentLength']

    @contextmanager
    def open(self, path, mode='rb'):
        """
        Open stored object.

        :param path: Path to the file
        :type path: str
        :param mode: File opening mode, defaults to 'rb'
        :type mode: str, optional
        :yield: The specified file
        :rtype: S3FileReader
        """
        f = S3FileReader(self.s3, self.bucket, path, mode=mode)
        yield f
        f.close()

    def exists(self, path):
        """
        Return true if the path exists.

        :param path: Path to the file
        :type path: str
        :return: Whether the file path exists or not
        :rtype: bool
        """
        return bool(self.filesize(path))

    def __str__(self):
        """
        Return endpoint/bucket concatenation.

        :return: Endpoint plus bucket concatenation
        :rtype: str
        """
        return self.endpoint + '/' + self.bucket
