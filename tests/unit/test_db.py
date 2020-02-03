import unittest
from lega.utils.db import DBConnection
from unittest import mock


class TestDBConnection(unittest.TestCase):
    """DBConnection.

    Testing DBConnection."""

    def setUp(self):
        """Initialise fixtures."""
        self._db = DBConnection()

    def tearDown(self):
        """Close DB connection."""
        self._db.close()

    @mock.patch('lega.utils.db.psycopg2')
    def test_connect(self, mock_db_connect):
        """Test that connection is returning a connection."""
        self._db.connect()
        mock_db_connect.connect.assert_called()

    @mock.patch('lega.utils.db.psycopg2')
    def test_cursor(self, mock_db_connect):
        """Test that cursor is executed."""
        with self._db.cursor():
            mock_db_connect.connect().cursor().__enter__().execute.assert_called()

    @mock.patch('lega.utils.db.psycopg2')
    def test_close(self, mock_db_connect):
        """Test that cursor is returning a connection."""
        self._db.close()
        self.assertEqual(self._db.curr, None)
        self.assertEqual(self._db.conn, None)

    @mock.patch('lega.utils.db.CONF')
    @mock.patch('lega.utils.db.psycopg2')
    def test_connects(self, mock_db_connect, mock_conf):
        """Test that connection is returning a connection."""
        # For CONF.get_value(....)
        def values(domain, value, conv=str, default=None, raw=True):
            d = {
                'connection': r'postgresql://user:passwd@db:5432/lega',
                'interval': 10,
                'attempts': 30
            }
            return d.get(value, default)
        mock_conf.get_value = mock.MagicMock(side_effect=values)

        self._db.ping()
        mock_db_connect.connect.assert_called()
