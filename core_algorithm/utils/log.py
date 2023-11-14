"""
These functions are called at the beginning of instantiation of a CELLO object.
Loggers are generated as specified in the logging.config file.
Unhandled exceptions are also captured by the logger (other than keyboard interrupts).
To use the loggers, 'log.cf.[level]' prints to console and log file, and 'log.f.[level]' only prints to log file.
Levels include: debug, info, warning, critical and others as specified in Python logging library documentation.
"""

import os
import sys
import traceback
import logging.config
from datetime import datetime
from config import BASE_DIR


iter_num = 0
iter_validity = "Valid"
log_counts = {'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0}  # Global issue counts (resets at new cello process)
last_log = "[None]"


def config_logger(vname: str, ucfname: str, ow: bool):
    """
    Generates log file and initializes the Logger class (for print() statements) every time a Cello process is created.
    :return: None
    """
    
    # Determine filename suffix based on the ow variable
    time_suffix = "" if ow else datetime.now().strftime("_%Y-%m-%d_%H%M%S")
    
    # Construct the log file name
    log_file_name = os.path.join('logs/', f"{vname}+{ucfname}{time_suffix}.log")
    
    # Configure logger
    logging.config.fileConfig(
        os.path.join(BASE_DIR, 'core_algorithm', 'utils', 'logging.config'),
        disable_existing_loggers=False,
        defaults={'logfilename': log_file_name}
    )
    
    # Disable logging for matplotlib's font manager to avoid potential clutter
    logging.getLogger('matplotlib.font_manager').disabled = True
    # sys.stdout = Logger(log_file_name)


def reset_logs():
    """
    Resets the issue counts every time a new Cello process object is created.
    :return: None
    """

    global iter_num
    global log_counts
    global last_log
    global iter_validity

    iter_num += 1
    log_counts = {'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0}
    last_log = "[None]"
    iter_validity = "Valid"


class ContextFilter(logging.Filter):
    """
    Counts the number of warnings, errors, and criticals (e.g. for reporting in the test_all_configs csv).
    """

    def filter(self, record):
        global log_counts
        global last_log
        global iter_validity

        if record.levelname in ('WARNING', 'ERROR', 'CRITICAL'):
            log_counts[record.levelname] += 1
            last_log = f"Caught exception: {record.msg}"
            cf.info(f"*****  !{record.levelname}!  *****\n{traceback.format_exc()}")
        elif record.levelname == 'DEBUG':  # 'debug' level reserved for invalid configs (e.g. gate mismatch)
            iter_validity = "Invalid"
        return True


def handle_exception(exc_type, exc_value, exc_traceback):
    """
    Captures unhandled exceptions so they can still be logged (and counted as criticals)
    :return:
    """

    global log_counts
    global last_log

    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    log_counts['CRITICAL'] += 1
    last_log = f"Uncaught exception: {exc_type}"
    cf.critical(f"Uncaught exception: {exc_type}: {exc_value}: {exc_traceback}",
                exc_info=(exc_type, exc_value, exc_traceback))


cf = logging.getLogger('both')  # Both print out to console and out to log
f = logging.getLogger('file')  # Only log (for tracking warnings/errors)
cf.addFilter(ContextFilter())  # Cannot be integrated into the logging.config
f.addFilter(ContextFilter())
sys.excepthook = handle_exception
