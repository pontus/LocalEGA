"""Utility functions used internally."""

import logging

LOG = logging.getLogger(__name__)


def get_file_content(f, mode='rb'):
    """Retrieve a file content."""
    try:
        with open(f, mode) as h:
            return h.read()
    except OSError as e:
        LOG.error(f'Error reading {f}: {e!r}')
        return None
