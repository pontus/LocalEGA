import unittest
from lega.ingest import work, main
from unittest import mock
from testfixtures import tempdir
from . import c4gh_data
from lega.utils.exceptions import FromUser


class testIngest(unittest.TestCase):
    """Ingest.

    Testing ingestion functionalities.
    """

    @mock.patch('lega.ingest.getattr')
    @mock.patch('lega.ingest.consume')
    def test_main(self, mock_consume, mock_getattr):
        """Test main verify, by mocking cosume call."""
        mock_consume.return_value = mock.MagicMock()
        main()
        mock_consume.assert_called()

    @tempdir()
    @mock.patch('lega.ingest.get_header')
    @mock.patch('lega.ingest.db')
    def test_work(self, mock_db, mock_header, filedir):
        """Test ingest worker, should send a messge."""
        # Mocking a lot of stuff, as it is previously tested
        mock_header.return_value = b'header'
        mock_db.insert_file.return_value = 32
        store = mock.MagicMock()
        store.location.return_value = 'smth'
        store.open.return_value = mock.MagicMock()
        mock_broker = mock.MagicMock(name='channel')
        mock_broker.channel.return_value = mock.Mock()
        infile = filedir.write('infile.in', bytearray.fromhex(c4gh_data.ENC_FILE))
        data = {'filepath': infile, 'user': 'user_id@elixir-europe.org',
                "encrypted_checksums": [{"type": "sha256", "value": "efa8ce457b27728b7af3351ed77793a6421190877128451830d68babbacf3021"}]}
        result = work(store, mock_broker, data)
        mocked = ({'filepath': infile, 'user': 'user_id@elixir-europe.org',
                   'file_id': 32,
                   'file_checksum': "efa8ce457b27728b7af3351ed77793a6421190877128451830d68babbacf3021",
                   'org_msg': {'filepath': infile, 'user': 'user_id@elixir-europe.org',
                               "encrypted_checksums": [{"type": "sha256", "value": "efa8ce457b27728b7af3351ed77793a6421190877128451830d68babbacf3021"}]},
                   'archive_path': 'smth'}, False)
        self.assertEqual(mocked, result)
        filedir.cleanup()

    @tempdir()
    @mock.patch('lega.ingest.get_header')
    @mock.patch('lega.ingest.db')
    def test_work_2(self, mock_db, mock_header, filedir):
        """Test ingest worker, should send a messge for generated checksum."""
        # Mocking a lot of stuff, as it is previously tested
        mock_header.return_value = b'header'
        mock_db.insert_file.return_value = 32
        store = mock.MagicMock()
        store.location.return_value = 'smth'
        store.open.return_value = mock.MagicMock()
        mock_broker = mock.MagicMock(name='channel')
        mock_broker.channel.return_value = mock.Mock()
        infile = filedir.write('infile.in', bytearray.fromhex(c4gh_data.ENC_FILE))
        data = {'filepath': infile, 'user': 'user_id@elixir-europe.org'}
        result = work(store, mock_broker, data)
        mocked = ({'filepath': infile, 'user': 'user_id@elixir-europe.org',
                   'file_id': 32,
                   'file_checksum': "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                   'org_msg': {'filepath': infile, 'user': 'user_id@elixir-europe.org'},
                   'archive_path': 'smth'}, False)
        self.assertEqual(mocked, result)
        filedir.cleanup()

    @tempdir()
    @mock.patch('lega.ingest.get_header')
    @mock.patch('lega.ingest.db')
    def test_db_fail(self, mock_db, mock_header, filedir):
        """Test ingest worker, insert_file fails."""
        # Mocking a lot of stuff, as it is previously tested
        mock_header.return_value = b'header'
        mock_db.insert_file.side_effect = Exception("Some strange exception")

        store = mock.MagicMock()
        store.location.return_value = 'smth'
        store.open.return_value = mock.MagicMock()
        mock_broker = mock.MagicMock(name='channel')
        mock_broker.channel.return_value = mock.Mock()
        infile = filedir.write('infile.in', bytearray.fromhex(c4gh_data.ENC_FILE))

        data = {'filepath': infile, 'user': 'user_id@elixir-europe.org'}
        result = work(store, mock_broker, data)
        self.assertEqual((None, True), result)
        filedir.cleanup()

    @tempdir()
    @mock.patch('lega.ingest.get_header')
    @mock.patch('lega.ingest.db')
    def test_mark_in_progress_fail(self, mock_db, mock_header, filedir):
        """Test ingest worker, mark_in_progress fails."""
        # Mocking a lot of stuff, as it is previously tested
        mock_header.return_value = b'header'
        mock_db.mark_in_progress.side_effect = Exception("Some strange exception")

        store = mock.MagicMock()
        store.location.return_value = 'smth'
        store.open.return_value = mock.MagicMock()
        mock_broker = mock.MagicMock(name='channel')
        mock_broker.channel.return_value = mock.Mock()
        infile = filedir.write('infile.in', bytearray.fromhex(c4gh_data.ENC_FILE))

        data = {'filepath': infile, 'user': 'user_id@elixir-europe.org'}
        result = work(store, store, mock_broker, data)
        self.assertEqual((None, True), result)
        filedir.cleanup()

    @tempdir()
    @mock.patch('lega.ingest.get_header')
    @mock.patch('lega.ingest.db')
    def test_mark_in_progress_fail_with_from_user_error(self, mock_db, mock_header, filedir):
        """Test ingest worker, mark_in_progress fails."""
        # Mocking a lot of stuff, as it is previously tested
        mock_header.return_value = b'header'
        mock_db.mark_in_progress.side_effect = FromUser()

        store = mock.MagicMock()
        store.location.return_value = 'smth'
        store.open.return_value = mock.MagicMock()
        mock_broker = mock.MagicMock(name='channel')
        mock_broker.channel.return_value = mock.Mock()
        infile = filedir.write('infile.in', bytearray.fromhex(c4gh_data.ENC_FILE))

        data = {'filepath': infile, 'user': 'user_id@elixir-europe.org'}
        result = work(store, store, mock_broker, data)
        self.assertEqual((None, True), result)
        filedir.cleanup()
