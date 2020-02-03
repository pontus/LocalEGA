import unittest
from lega.utils.amqp import AMQPConnection


class TestAMQPConnection(unittest.TestCase):
    """MQ Broker.

    Test broker connections.
    """
    def setUp(self):
        """Initialise fixtures."""
        self._amqp = AMQPConnection()

    def tearDown(self):
        """Close DB connection."""
        self._amqp.close()
