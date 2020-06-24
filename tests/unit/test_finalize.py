import unittest
from lega.finalize import main, work
from unittest import mock


class testFinalize(unittest.TestCase):
    """Finalize.

    Testing Finalizer functionalities.
    """

    def setUp(self):
        """Initialise fixtures."""
        pass

    def tearDown(self):
        """Remove anything that was setup."""
        pass

    @mock.patch('lega.finalize.db')
    def test_work(self, mock_db):
        """Test finalize worker, should insert into database."""
        # mock_db.set_stable_id.return_value = mock.Mock()
        data = {'accession_id': '1', 'filepath': '/123.c4gh', 'user': 'user',
                "decrypted_checksums": [{'type': 'sha256', 'value': '7c03e8b0789ecf5ecdeb34ef37a6ec8620912e8b1a9f15f22233471e9b457130'},
                                        {'type': 'md5', 'value': 'b5a2d2075f200552829ab0c3a056bf13'}]}
        work(data)
        mock_db.set_stable_id.assert_called_with('/123.c4gh', 'user',
                                                 '7c03e8b0789ecf5ecdeb34ef37a6ec8620912e8b1a9f15f22233471e9b457130', '1')

    @mock.patch('lega.finalize.consume')
    def test_main(self, mock_consume):
        """Test main finalize, by mocking cosume call."""
        mock_consume.return_value = mock.MagicMock()
        main()
        mock_consume.assert_called()
