"""
These functions are called at the beginning of instantiation of a CELLO object.
Loggers are generated as specified in the logging.config file.
Unhandled exceptions are also captured by the logger (other than keyboard interrupts).
To use the loggers, 'out.[level]' will print to console and log file, and 'log.[level]' will only print to log file.
Levels include: debug, info, warning, critical and others as specified in Python logging library documentation.
(To only print to console, just use 'print()' as normal.)
"""

import sys
import logging.config
from datetime import datetime


def logger(vname, ucfname):
    log_file_name = 'logs/' + vname + '+' + ucfname + '_' + datetime.now().strftime("%Y-%m-%d_%H%M%S") + '.log'
    logging.config.fileConfig('utils/logging.config', disable_existing_loggers=False,
                              defaults={'logfilename': log_file_name})


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    out.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


out = logging.getLogger('root')  # Both print out to console and out to log
log = logging.getLogger('app')  # Only log (for tracking warnings/errors)
sys.excepthook = handle_exception
