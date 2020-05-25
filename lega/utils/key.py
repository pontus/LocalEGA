import logging
from ..conf import CONF

LOG = logging.getLogger(__name__)


class Key():
    """
    Base class holding the information about a keypair.
    """

    def __init__(self, config):
        """
        Initiliaze the Key object from a dict.

        :param config: A dictionary containing key configuration
        :type config: dict
        """
        self.config = config

    def public(self):
        """
        Get the public key part.

        :raises NotImplementedError: It should return bytes
        """
        raise NotImplementedError('subclasses of Key must provide an public() method')

    def private(self):
        """
        Get the private key part.

        :raises NotImplementedError: It should return bytes
        """
        raise NotImplementedError('subclasses of Key must provide an private() method')


class C4GHFileKey(Key):
    """
    Loading a Crypt4GH-formatted file, and unlocking it using a passphrase.

    See https://crypt4gh.readthedocs.io/en/latest/keys.html
    """

    def __init__(self, config):
        """
        Initiliaze the Key object from a dict.

        :param config: A dictionary containing C4GH configuration
        :type config: dict
        """
        filepath = CONF.get_value(config, 'filepath')
        passphrase = CONF.get_value(config, 'passphrase')
        assert(filepath and passphrase)

        # We use the parser provided in the crypt4gh.keys module
        from crypt4gh.keys import get_private_key
        LOG.debug('Unlocking private key: %s', filepath)
        self.seckey = get_private_key(filepath, lambda: passphrase)  # callback

        # Don't bother reading the public key from file,
        # We can simply recompute it from the private key
        from nacl.public import PrivateKey
        self.pubkey = bytes(PrivateKey(self.seckey).public_key)
        LOG.debug('Setting public key: %s', self.pubkey.hex())

        LOG.info('Successfully loaded a Crypt4GH-formatted key from file')

    def public(self):
        """
        Get the public key part.

        :return: It returns 32 bytes
        :rtype: bytes
        """
        return self.pubkey

    def private(self):
        """
        Get the private key part.

        :return: It returns 32 bytes
        :rtype: bytes
        """
        return self.seckey


class HashiCorpVaultKey(Key):
    """
    Retrieve a key from a remote Hashicorp Vault.
    """

    pass


class HTTPSKey(Key):
    """
    Retrieve a key from a remote HTTP(s) server.
    """

    pass
