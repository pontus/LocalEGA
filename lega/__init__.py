# -*- coding: utf-8 -*-
# __init__ is here so that we don't collapse in sys.path with another lega module

"""The lega package contains code to start a *NeIC SDA*."""

__title__ = 'SDA'
__version__ = VERSION = '1.2'
__author__ = 'NeIC System Developers'
__license__ = 'Apache 2.0'
__copyright__ = 'NeIC Tryggve2'

# Set default logging handler to avoid "No handler found" warnings.
import logging

# This updates the logging class from all loggers used in this package.
# The new logging class injects a correlation id to the log record.
from .utils.logging import LEGALogger
logging.setLoggerClass(LEGALogger)

# Send warnings using the package warnings to the logging system
# The warnings are logged to a logger named 'py.warnings' with a severity of WARNING.
# See: https://docs.python.org/3/library/logging.html#integration-with-the-warnings-module
logging.captureWarnings(True)
