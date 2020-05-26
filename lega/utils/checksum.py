# -*- coding: utf-8 -*-
"""Computes the checksum."""

import logging
import hashlib

from .exceptions import UnsupportedHashAlgorithm, CompanionNotFound

LOG = logging.getLogger(__name__)

# Main map
_DIGEST = {
    'md5': hashlib.md5,
    'sha256': hashlib.sha256,
}


def supported_algorithms():
    """
    Supported hashing algorithms, currently ``md5`` and ``sha256``.

    :return: A tuple containing supported hashing algorithms
    :rtype: tuple
    """
    return tuple(_DIGEST.keys())


def instantiate(algo):
    """
    Instantiate algorithm.

    :param algo: Key to instantiate a hashing algorithm
    :type algo: str
    :raises UnsupportedHashAlgorithm: Key does not exist
    :return: md5 or sha256
    :rtype: haslib.md5 or hashlib.sha256
    """
    try:
        return (_DIGEST[algo])()
    except KeyError:
        raise UnsupportedHashAlgorithm(algo)


def calculate(filepath, algo, bsize=8192):
    """
    Compute the checksum of a file using the message digest ``m``.

    :param filepath: Target file path
    :type filepath: str
    :param algo: Key used to instantiate hashing algorithm
    :type algo: str
    :param bsize: Number of bytes to read at a time, defaults to 8192
    :type bsize: int, optional
    :return: Checksum of the specified file
    :rtype: str
    """
    try:
        m = instantiate(algo)
        with open(filepath, 'rb') as f:  # Open the file in binary mode. No encoding dance.
            while True:
                data = f.read(bsize)
                if not data:
                    break
                m.update(data)
        return m.hexdigest()
    except OSError as e:
        LOG.error('Unable to calculate checksum: %r', e)
        return None


def is_valid(filepath, digest, hashAlgo='md5'):
    """
    Verify the integrity of a file against a hash value.

    :param filepath: Target file path
    :type filepath: str
    :param digest: Checksum digest
    :type digest: str
    :param hashAlgo: Hashing algorithm used, defaults to 'md5'
    :type hashAlgo: str, optional
    :return: Whether checksum is valid or not
    :rtype: bool
    """
    assert(isinstance(digest, str))

    res = calculate(filepath, hashAlgo)
    LOG.debug('Calculated digest: '+res)
    LOG.debug('  Original digest: '+digest)
    return res is not None and res == digest


def get_from_companion(filepath):
    """
    Attempt to read a companion file.

    For each supported algorithms, we check if a companion file exists.
    If so, we read its content and return it, along with the selected current algorithm.

    We exit at the first one found and raise a CompanionNotFound exception in case none worked.

    :param filepath: Target companion file path
    :type filepath: str
    :raises CompanionNotFound: Companion file not found
    :return: Whether a companion file exists for each supported algorithm or not
    :rtype: tuple(bytes, str)
    """
    for h in _DIGEST:
        companion = str(filepath) + '.' + h
        try:
            with open(companion, 'rt', encoding='utf-8') as f:
                return f.read(), h
        except OSError as e:  # Not found, not readable, ...
            LOG.debug('Companion %s: %r', companion, e)
            # Check the next

    else:  # no break statement was encountered
        raise CompanionNotFound(filepath)
