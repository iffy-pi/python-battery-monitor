import os
import logging.handlers
import sys
from datetime import datetime
from time import time
from scripts.functions import get_log_format

"""
Logger Configuration:
We use the following loggers in our script:
- logger
    - Logs records to assigned log file
    - Prints to stdout if print logs is enabled
    - Does not log records if logs are disabled
- console
    - Prints to stdout (raw format)
    - If script is headless, then it will log to the log file with console format
    - If script is headless and logs are disabled, nothing will be logged
- printer
    - Logs to log file with console format
    - Prints to stdout 
    - If script is headless, it only logs to log file with console format
    - If print logs is enabled, it will output console logs to stdout
    - If logs are disabled and script is headless, nothing will be saved
    
- Available functions
    - enable_logs(bool) : Enable or disable logs
    - print_logs(bool) : Start printing or stop printing logs to stdout
        - This is inactive when script is in headless mode
    - is_printing_logs(): Returns if the script is currently printing logs
    - set_headless(bool) : Set headless state of the script
        - Headless mode, i.e. script has no stdout
        - If set_headless(False), it will only be false if sys.stdout is None
    
Log Format example:
2024-02-23 10:14:54 INFO     test.py                   [   9]: Help Me

"""

# Do our initial configuration
LOG_FORMAT = get_log_format()
CONSOLE_LOG_FORMAT = logging.Formatter('%(asctime)s  CONSOLE   %(filename)-25s [%(lineno)4d] %(message)s',
                               datefmt='%Y-%m-%d %H:%M:%S')
PRINT_FORMAT = logging.Formatter('%(message)s')
NO_LOGS_AT_ALL_LEVEL = 90
CONSOLE_OUTPUT_LOGGER = 'console'
DATA_LOGGER = 'log'
PRINTER_LOGGER = 'printer'

log_file_addr = os.path.expanduser('~\\Battery_Monitor_Initial_Log.log')
headless = sys.stdout is None
bPrintingLogs = False

# Logger object definitions
logger = logging.getLogger(DATA_LOGGER)
console = logging.getLogger(CONSOLE_OUTPUT_LOGGER)
printer = logging.getLogger(PRINTER_LOGGER)

# Records are written to file using log format
# Used by logger
log_file_handler = logging.handlers.RotatingFileHandler(log_file_addr, 'a')
log_file_handler.setFormatter(LOG_FORMAT)

# Records are printed to stdout with log format
# Used by logger when print_logs is enabled
log_stdout_handler = logging.StreamHandler(sys.stdout)
log_stdout_handler.setFormatter(LOG_FORMAT)

# Records are printed to stdout using console log format
# Used by printer when print_logs is enabled
log_console_stdout_handler = logging.StreamHandler(sys.stdout)
log_console_stdout_handler.setFormatter(CONSOLE_LOG_FORMAT)


# Records are written to console as messages, equivalent to calling print
# Used by console and printer
console_stdout_handler = logging.StreamHandler(sys.stdout)
console_stdout_handler.setFormatter(PRINT_FORMAT)

# Records are written to log file using console log format
# Used by printer
# Used by console when headless
console_file_handler = logging.handlers.RotatingFileHandler(log_file_addr, 'a')
console_file_handler.setFormatter(CONSOLE_LOG_FORMAT)

# Logger Base Configuration
logger.addHandler(log_file_handler)
logger.setLevel(logging.INFO)

# Console base configuration
if headless:
    console.addHandler(console_file_handler)
else:
    console.addHandler(console_stdout_handler)
console.setLevel(logging.INFO)

# Printer base configuration
printer.setLevel(logging.INFO)
printer.addHandler(console_file_handler)
printer.addHandler(console_stdout_handler)

def is_logs_enabled():
    return logger.hasHandlers()

def enable_logs(enable: bool):
    if not enable:
        # When logs are dsiabled, there will be no logging at all to log file
        # Console only prints to stdout, printer only prints to stdout
        # Therefore remove all hanlders  that log to file
        logger.removeHandler(log_file_handler)
        logger.removeHandler(log_stdout_handler)

        console.removeHandler(console_file_handler)

        printer.removeHandler(console_file_handler)
        printer.removeHandler(log_console_stdout_handler)
    else:
        logger.addHandler(log_file_handler)
        printer.addHandler(console_file_handler)

        if bPrintingLogs:
            printer.addHandler(log_console_stdout_handler)
            logger.addHandler(log_stdout_handler)

        if headless:
            # If headless, console logs to file
            console.addHandler(console_file_handler)

def set_headless(enable: bool):
    global headless
    if enable:
        headless = True
    else:
        # We are not headless only if we have stdout
        headless = sys.stdout is None

    if headless:
        # Script is running headlessly, so all console logs must be written to log file using log file format
        # Replace print handler with log handler
        logger.removeHandler(log_stdout_handler)

        printer.removeHandler(console_stdout_handler)
        printer.removeHandler(log_console_stdout_handler)

        console.removeHandler(console_stdout_handler)
        console.addHandler(console_file_handler)
    else:
        # Not headless, so we can print to stdout
        console.removeHandler(console_file_handler)
        console.addHandler(console_stdout_handler)
        printer.addHandler(console_stdout_handler)

        if bPrintingLogs:
            printer.addHandler(log_stdout_handler)
            logger.addHandler(log_stdout_handler)

    # Respect enabled rules
    enable_logs(is_logs_enabled())

def print_logs(enable: bool):
    global bPrintingLogs
    if headless or sys.stdout is None:
        return

    if enable:
        bPrintingLogs = True
        # Function automatically checks if handler is already in list, so we can just do this
        logger.addHandler(log_stdout_handler)
        printer.addHandler(log_console_stdout_handler)
        printer.removeHandler(console_stdout_handler)
    else:
        bPrintingLogs = False
        logger.removeHandler(log_stdout_handler)
        printer.removeHandler(log_console_stdout_handler)
        printer.addHandler(console_stdout_handler)

    enable_logs(is_logs_enabled())

def is_printing_logs():
    if headless or sys.stdout is None:
        return False
    return bPrintingLogs

def log_to_file(file_addr: str):
    global log_file_handler
    global console_file_handler
    global log_file_addr

    old_console_handler = console_file_handler
    old_log_handler = log_file_handler
    log_file_addr = file_addr

    log_file_handler = logging.handlers.RotatingFileHandler(log_file_addr, 'a')
    log_file_handler.setFormatter(LOG_FORMAT)
    console_file_handler = logging.handlers.RotatingFileHandler(log_file_addr, 'a')
    console_file_handler.setFormatter(CONSOLE_LOG_FORMAT)

    logger.removeHandler(old_log_handler)
    logger.addHandler(log_file_handler)

    printer.removeHandler(old_console_handler)
    printer.addHandler(console_file_handler)

    if headless:
        console.removeHandler(old_console_handler)
        console.addHandler(console_file_handler)

def get_log_file_addr():
    return log_file_addr

def flush_logs():
    log_file_handler.flush()
    console_file_handler.flush()

def logging_to_file():
    return log_file_handler in logger.handlers


def new_log_file(logdir):
    return os.path.join(logdir,
                 'status_{}_{}.log'.format(
                     datetime.today().strftime('%H%M_%d_%m_%Y'),
                     int(time())
                 ))
