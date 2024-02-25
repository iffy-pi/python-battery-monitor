import os
import logging.handlers
import sys
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from datetime import datetime
from time import time
from scripts.functions import get_log_format, get_console_log_format, get_log_stdout_format

"""
Logger Configuration:
We use the following loggers in our script, which are provided as global variables:
- logger
    - Logs records to file using LOG_FORMAT
    - Prints to stdout if print logs is enabled
    - if logs are disabled or no log file:
        - Records are not logged
    - If printing logs:
        - Records are printed to stdout
    - If headless:
        - Printing logs has no effect
- console
    - Records are printed to stdout with PRINT_FORMAT
    - If script is headless
        - Printing logs has no effect
        - Records are logged to log file with LOG_CONSOLE_FORMAT
        - If logs are disabled or no log file:
            - Records are not logged
- printer
    - Prints and logs at the same time
    - Records are logged to file with LOG_CONSOLE_FORMAT and printed to stdout using PRINT_FORMAT
    - If printing logs:
        - Records will now be printed to stdout using LOG_CONSOLE_FORMAT
    - If logs are disabled or no log file:
        - Records are ONLY printed to stdout using PRINT_FORMAT
    - If script is headless
        - Printing logs does nothing
        - Records are only logged to file with LOG_CONSOLE_FORMAT
        - If logs are disabled or no log file:
            - Nothing will be logged

You can change logging behaviour with the global controller variable
- controller
    - Provides methods to set headless, logs enabled, logging to file and printing logs
    - Also allows you to change the log file being used
"""


class LoggingController:
    LOG_FORMAT = get_log_format()
    CONSOLE_LOG_FORMAT = get_console_log_format()
    PRINT_FORMAT = logging.Formatter('%(message)s')
    NO_LOGS_AT_ALL_LEVEL = 90
    CONSOLE_OUTPUT_LOGGER = 'console'
    DATA_LOGGER = 'log'
    PRINTER_LOGGER = 'printer'
    def __init__(self, initLogFileAddr:str=None):
        self.logFileAddr = initLogFileAddr

        self.bHeadless = sys.stdout is None
        self.bLoggingEnabled = True
        self.bLoggingToFile = self.logFileAddr is not None
        self.bPrintingLogs = False

        self.hLogFile, self.hConsoleFile = None, None

        if self.bLoggingToFile:
            self.hLogFile, self.hConsoleFile = self.createFileHandlers()

        self.hConsoleOut, self.hLogOut, self.hLogConsoleOut = self.createStdOutHandlers()

        # Our loggers
        self.logger = logging.getLogger(self.DATA_LOGGER)
        self.console = logging.getLogger(self.CONSOLE_OUTPUT_LOGGER)
        self.printer = logging.getLogger(self.PRINTER_LOGGER)
        self.logger.setLevel(logging.INFO)
        self.console.setLevel(logging.INFO)
        self.printer.setLevel(logging.INFO)

        self.configureLoggers()

    def createFileHandlers(self) -> tuple[RotatingFileHandler, RotatingFileHandler]:
        # Records are written to file using log format
        # Used by logger
        logs_to_file = logging.handlers.RotatingFileHandler(self.logFileAddr, 'a')
        logs_to_file.setFormatter(LoggingController.LOG_FORMAT)

        # Records are written to log file using console log format
        # Used by printer
        # Used by console when headless
        console_file = logging.handlers.RotatingFileHandler(self.logFileAddr, 'a')
        console_file.setFormatter(LoggingController.CONSOLE_LOG_FORMAT)

        return logs_to_file, console_file

    def createStdOutHandlers(self) -> tuple[StreamHandler, StreamHandler, StreamHandler]:
        # Records are printed to stdout with log format
        # Used by logger when print_logs is enabled
        log_stdout_handler = logging.StreamHandler(sys.stdout)
        log_stdout_handler.setFormatter(get_log_stdout_format())

        # Records are printed to stdout using console log format
        # Used by printer when print_logs is enabled
        log_console_stdout_handler = logging.StreamHandler(sys.stdout)
        log_console_stdout_handler.setFormatter(LoggingController.CONSOLE_LOG_FORMAT)

        # Records are written to console as messages, equivalent to calling print
        # Used by console and printer
        console_stdout_handler = logging.StreamHandler(sys.stdout)
        console_stdout_handler.setFormatter(LoggingController.PRINT_FORMAT)
        return console_stdout_handler, log_stdout_handler, log_console_stdout_handler

    def getConsole(self):
        return self.console

    def getLogger(self):
        return self.logger

    def getPrinter(self):
        return self.printer

    def emptyHandlersFromLoggers(self):
        loggers = (self.console, self.logger, self.printer)
        for lg in loggers:
            handlers = list(lg.handlers)
            for h in handlers:
                lg.removeHandler(h)


    def configureLoggers(self):
        self.emptyHandlersFromLoggers()

        has_head = not self.bHeadless

        if has_head:
            self.console.addHandler(self.hConsoleOut)
            self.printer.addHandler(self.hConsoleOut)

            if self.bLoggingEnabled:
                if self.bLoggingToFile:
                    self.logger.addHandler(self.hLogFile)
                    self.printer.addHandler(self.hConsoleFile)

                if self.bPrintingLogs:
                    self.logger.addHandler(self.hLogOut)
                    self.printer.removeHandler(self.hConsoleOut)
                    self.printer.addHandler(self.hLogConsoleOut)

        else:
            if self.bLoggingEnabled and self.bLoggingToFile:
                self.logger.addHandler(self.hLogFile)
                self.console.addHandler(self.hConsoleFile)
                self.printer.addHandler(self.hConsoleFile)

    def setHeadless(self, enable:bool):
        if enable:
            self.bHeadless = True
        else:
            self.bHeadless = sys.stdout is None
        self.configureLoggers()

    def setLoggingEnabled(self, enable:bool):
        self.bLoggingEnabled = enable
        self.configureLoggers()

    def setLoggingToFile(self, enable:bool):
        self.bLoggingToFile = enable
        self.configureLoggers()

    def setPrintLogs(self, enable:bool):
        self.bPrintingLogs = enable
        self.configureLoggers()

    def changeLogFile(self, newFileAddr):
        # Recreate log file handler and then reconfigure loggers
        self.logFileAddr = newFileAddr
        self.hLogFile, self.hConsoleFile = self.createFileHandlers()
        self.configureLoggers()

    def getLogFile(self):
        return self.logFileAddr

    def isHeadless(self):
        return self.bHeadless

    def isLoggingdEnabled(self):
        return self.bLoggingEnabled

    def isLoggingToFile(self):
        return self.bLoggingToFile

    def isPrintingLogs(self):
        return self.bPrintingLogs

    def flushLogs(self):
        self.hLogFile.flush()
        self.hConsoleFile.flush()


    @staticmethod
    def selfTest():

        controller = LoggingController('bm.log')

        # Set of tests and the expected handlers the loggers should have
        tests = [
            {
                "test_no": 0,
                "has_head": True,
                "logs_enabled": True,
                "logging_to_file": True,
                "printing_logs": True,
                "logger": [controller.hLogFile, controller.hLogOut],
                "console": [controller.hConsoleOut],
                "printer": [controller.hConsoleFile, controller.hLogConsoleOut]
            },
            {
                "test_no": 1,
                "has_head": True,
                "logs_enabled": True,
                "logging_to_file": True,
                "printing_logs": False,
                "logger": [controller.hLogFile],
                "console": [controller.hConsoleOut],
                "printer": [controller.hConsoleOut, controller.hConsoleFile]
            },
            {
                "test_no": 2,
                "has_head": True,
                "logs_enabled": True,
                "logging_to_file": False,
                "printing_logs": True,
                "logger": [controller.hLogOut],
                "console": [controller.hConsoleOut],
                "printer": [controller.hLogConsoleOut]
            },
            {
                "test_no": 3,
                "has_head": True,
                "logs_enabled": True,
                "logging_to_file": False,
                "printing_logs": False,
                "logger": [],
                "console": [controller.hConsoleOut],
                "printer": [controller.hConsoleOut]
            },
            {
                "test_no": 4,
                "has_head": True,
                "logs_enabled": False,
                "logging_to_file": True,
                "printing_logs": True,
                "logger": [],
                "console": [controller.hConsoleOut],
                "printer": [controller.hConsoleOut]
            },
            {
                "test_no": 5,
                "has_head": True,
                "logs_enabled": False,
                "logging_to_file": True,
                "printing_logs": False,
                "logger": [],
                "console": [controller.hConsoleOut],
                "printer": [controller.hConsoleOut]
            },
            {
                "test_no": 6,
                "has_head": True,
                "logs_enabled": False,
                "logging_to_file": False,
                "printing_logs": True,
                "logger": [],
                "console": [controller.hConsoleOut],
                "printer": [controller.hConsoleOut]
            },
            {
                "test_no": 7,
                "has_head": True,
                "logs_enabled": False,
                "logging_to_file": False,
                "printing_logs": False,
                "logger": [],
                "console": [controller.hConsoleOut],
                "printer": [controller.hConsoleOut]
            },
            {
                "test_no": 8,
                "has_head": False,
                "logs_enabled": True,
                "logging_to_file": True,
                "printing_logs": True,
                "logger": [controller.hLogFile],
                "console": [controller.hConsoleFile],
                "printer": [controller.hConsoleFile]
            },
            {
                "test_no": 9,
                "has_head": False,
                "logs_enabled": True,
                "logging_to_file": True,
                "printing_logs": False,
                "logger": [controller.hLogFile],
                "console": [controller.hConsoleFile],
                "printer": [controller.hConsoleFile]
            },
            {
                "test_no": 10,
                "has_head": False,
                "logs_enabled": True,
                "logging_to_file": False,
                "printing_logs": True,
                "logger": [],
                "console": [],
                "printer": []
            },
            {
                "test_no": 11,
                "has_head": False,
                "logs_enabled": True,
                "logging_to_file": False,
                "printing_logs": False,
                "logger": [],
                "console": [],
                "printer": []
            },
            {
                "test_no": 12,
                "has_head": False,
                "logs_enabled": False,
                "logging_to_file": True,
                "printing_logs": True,
                "logger": [],
                "console": [],
                "printer": []
            },
            {
                "test_no": 13,
                "has_head": False,
                "logs_enabled": False,
                "logging_to_file": True,
                "printing_logs": False,
                "logger": [],
                "console": [],
                "printer": []
            },
            {
                "test_no": 14,
                "has_head": False,
                "logs_enabled": False,
                "logging_to_file": False,
                "printing_logs": True,
                "logger": [],
                "console": [],
                "printer": []
            },
            {
                "test_no": 15,
                "has_head": False,
                "logs_enabled": False,
                "logging_to_file": False,
                "printing_logs": False,
                "logger": [],
                "console": [],
                "printer": []
            }
        ]

        def get_handlers_str(handlers):
            strs = []
            for h in handlers:
                if h == controller.hLogFile:
                    strs.append('hLogFile')
                elif h == controller.hConsoleFile:
                    strs.append('hConsoleFile')
                elif h == controller.hConsoleOut:
                    strs.append('hConsoleOut')
                elif h == controller.hLogOut:
                    strs.append('hLogOut')
                elif h == controller.hLogConsoleOut:
                    strs.append('hLogConsoleOut')

            st = ', '.join(strs)
            return f'[{st}]'

        def check_handler_list(handlers1, handlers2):
            return set(handlers1) == set(handlers2)

        def pass_str(bPass):
            return 'PASS' if bPass else 'FAIL'

        failed = []

        for test in tests:
            has_head = test['has_head']
            logs_enabled = test['logs_enabled']
            logging_to_file = test['logging_to_file']
            printing_logs = test['printing_logs']

            # Set parameters
            controller.setHeadless(not has_head)
            controller.setLoggingEnabled(logs_enabled)
            controller.setLoggingToFile(logging_to_file)
            controller.setPrintLogs(printing_logs)

            # Check if handlers match expected listing
            loggerPassed = check_handler_list(test['logger'], controller.logger.handlers)
            consolePassed = check_handler_list(test['console'], controller.console.handlers)
            printerPassed = check_handler_list(test['printer'], controller.printer.handlers)

            no = test["test_no"]
            if not(loggerPassed and consolePassed and printerPassed):
                failed.append(no)

            print(f'Test {no} =================================================================')
            print(f'Has Head        : {has_head}')
            print(f'Logging Enabled : {logs_enabled}')
            print(f'Logging To File : {logging_to_file}')
            print(f'Printing Logs   : {printing_logs}')
            print()
            print(f'logger          : {pass_str(loggerPassed)} ({get_handlers_str(controller.logger.handlers)})')
            print(f'console         : {pass_str(consolePassed)} ({get_handlers_str(controller.console.handlers)})')
            print(f'printer         : {pass_str(printerPassed)} ({get_handlers_str(controller.printer.handlers)})')
            print('')

        print('Tests Completed')
        print(f'{len(tests)-len(failed)}/{len(tests)} Passed')

        if len(failed) > 0:
            print(f'Failed Tests: {failed}')



controller = LoggingController(os.path.expanduser('~\\Battery_Monitor_Initial_Log.log'))
logger = controller.getLogger()
console = controller.getConsole()
printer = controller.getPrinter()

def flush_logs():
    controller.flushLogs()

def new_log_file(logdir):
    return os.path.join(logdir,
                 'status_{}_{}.log'.format(
                     datetime.today().strftime('%H%M_%d_%m_%Y'),
                     int(time())
                 ))