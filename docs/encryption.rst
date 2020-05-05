Encryption Algorithm - Crypt4GH
===============================

The encryption procedure uses the :download:`Crypt4GH file format
<http://samtools.github.io/hts-specs/crypt4gh.pdf>`, which works as follows.

A random session key (of 256 bits) is generated to seed a ChaCha20
engine, with Poly1305 authentication mode. For each segment of at most
64kB of data, a nonce is randomly generated and prepended to the
segment. Using the two latters, the original file is segmented and
each segment is encrypted.

The header is prepended to the encrypted data, it also contains, the word ``crypt4gh``,
the format version, the number of header packets, and the sequence of header packets.

A header packet consists of length followed by its content. 
The content can be a data encryption packet or an edit list packet.

All packets are encrypted using a Curve25519-based encryption.

.. image:: /static/crypt4gh_structure.png
   :target: http://samtools.github.io/hts-specs/crypt4gh.pdf
   :alt: Crypt4GH Encryption

The advantages of the format are, among others:

* Re-encrypting the file for another user requires only to decrypt the header and encrypt it with the user's public key.
* Header packets can be encrypted for multiple recipients.
* Re-arranging the file to chunk a portion requires only to decrypt the header, 
  re-encrypt with an edit list, and select the cipher segments surrounding the portion. The file itself is not decrypted and reencrypted.

In order to encrypt files using this standard we recommend the following tools:

* https://github.com/samtools/htslib-crypt4gh/ - samtools extension
* https://github.com/EGA-archive/crypt4gh - python library (recommned to be used with Openssl 1.1.+)
* https://github.com/elixir-oslo/crypt4gh - golang library
* https://github.com/uio-bmi/crypt4gh - Java library
* https://github.com/CSCfi/crypt4gh-gui - GUI using the python library
