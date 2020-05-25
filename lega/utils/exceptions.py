# -*- coding: utf-8 -*-
"""
Module for handling custom LEGA exceptions.
"""

#############################################################################
# User Errors
#############################################################################


class FromUser(Exception):
    """
    Raised Exception on incorrect user input.
    """

    def __str__(self):  # Informal description
        """
        Return readable informal description.

        :return: An indicative message showing that the user input was not correct.
        :rtype: str
        """
        return 'Incorrect user input'

    def __repr__(self):  # Technical description
        """
        Return detailed, technical description

        :return: A more detailed message showing that the user input was not correct.
        :rtype: str
        """
        return str(self)


class NotFoundInInbox(FromUser):
    """
    Raised Exception on incorrect user input.

    Exception should be raised if the input file was not found in Inbox.
    """

    def __init__(self, filename):
        """
        Initialize NotFoundInInbox Exception.

        :param filename: Name of the file
        :type filename: str
        """
        self.filename = filename

    def __str__(self):
        """
        An informal exception description.

        :return: A readable informal exception description
        :rtype: str
        """
        return 'File not found in inbox'

    def __repr__(self):
        """
        Return the file name for the missing file

        :return: A file name
        :rtype: str
        """
        return f'Inbox missing file: {self.filename}'


class UnsupportedHashAlgorithm(FromUser):
    """Raised Exception when a specific algorithm is not supported."""

    def __init__(self, algo):
        """
        Initialize UnsupportedHashAlgorithm Exception.

        :param algo: Unsupported algorithm name
        :type algo: str
        """
        self.algo = algo

    def __str__(self):
        """
        Return the unsupported algorithm name.

        :return: Message including the unsupported algorithm name
        :rtype: str
        """
        return f'Unsupported hash algorithm: {self.algo!r}'


class CompanionNotFound(FromUser):
    """Raised Exception if Companion file is not found."""

    def __init__(self, name):
        """
        Initialize CompanionNotFound Exception.

        :param name: Companion file name
        :type name: str
        """
        self.name = name

    def __str__(self):
        """
        Return readable informal exception description.

        :return: Not found message
        :rtype: str
        """
        return 'Companion file not found in inbox'

    def __repr__(self):
        """
        Return readable informal exception description.

        :return: Not found message with file name
        :rtype: str
        """
        return f'Companion file not found for {self.name}'


class Checksum(FromUser):
    """Raised Exception related to an invalid checksum."""

    def __init__(self, algo, file=None, decrypted=False):
        """
        Return readable informal exception description.

        :param algo: Algorithm name
        :type algo: str
        :param file: File name, defaults to None
        :type file: str, optional
        :param decrypted: Whether the checksum is decrypted or not, defaults to False
        :type decrypted: bool, optional
        """
        self.algo = algo
        self.decrypted = decrypted
        self.file = file

    def __str__(self):
        """
        Return readable informal exception description about checksumed exception.

        :return: Exception about checksum
        :rtype: str
        """
        return 'Invalid {} checksum for the {} file'.format(self.algo, 'original' if self.decrypted else 'encrypted')

    def __repr__(self):
        """
        Return readable informal exception description about checksumed exception, with file name

        :return: Exception about checksum with file name
        :rtype: str
        """
        return 'Invalid {} checksum for the {} file: {}'.format(self.algo, 'original' if self.decrypted else 'encrypted', self.file)


class SessionKeyDecryptionError(FromUser):
    """Raised Exception when header decryption fails."""

    def __init__(self, h):
        """
        Initialize Checksum Exception.

        :param h: header content
        :type h: bytes
        """
        self.header = h.hex().upper()

    def __str__(self):
        """
        Return readable informal exception description.

        :return: Exception about header decryption
        :rtype: str
        """
        return 'Unable to decrypt header with master key'

    def __repr__(self):
        """
        Return readable technical exception description.

        :return: Exception about header decryption with header
        :rtype: str
        """
        return f'Unable to decrypt header with master key: {self.header}'


# Is it really a user error?
class SessionKeyAlreadyUsedError(FromUser):
    """Raised Exception related a session key being already in use."""

    def __init__(self, checksum):
        """
        Initialize Checksum in Exception.

        :param checksum: Checksum of the session key
        :type checksum: str
        """
        self.checksum = checksum

    def __str__(self):
        """
        Return readable informal exception description.

        :return: Exception about already used session key
        :rtype: str
        """
        return 'Session key (likely) already used.'

    def __repr__(self):
        """
        Return the checksum of the session key which was already used.

        :return: Exception about already used session key with checksum
        :rtype: str
        """
        return f'Session key (likely) already used [checksum: {self.checksum}].'


#############################################################################
# Any other exception is caught by us
#############################################################################

class AlreadyProcessed(Warning):
    """Raised when a file has already been processed."""

    def __init__(self, user, filename, enc_checksum_hash, enc_checksum_algorithm):
        """
        Initialize AlreadyProcessed Exception.

        :param user: Name of the user
        :type user: str
        :param filename: Name of the already processed file
        :type filename: str
        :param enc_checksum_hash: The encrypted checksum
        :type enc_checksum_hash: str
        :param enc_checksum_algorithm: Algorithm used for encryption
        :type enc_checksum_algorithm: str
        """
        self.user = user
        self.filename = filename
        self.enc_checksum_hash = enc_checksum_hash
        self.enc_checksum_algorithm = enc_checksum_algorithm

    def __repr__(self):
        """
        Return detailed information about the file which was already processed.

        :return: Information about the already processed file
        :rtype: str
        """
        return (f'Warning: File already processed\n'
                f'\t* user: {self.user}\n'
                f'\t* name: {self.filename}\n'
                f'\t* Encrypted checksum: {self.enc_checksum_hash} (algorithm: {self.enc_checksum_algorithm}')
