from datetime import datetime

class ScriptOutputStream:
    """
    Manages the script output and logging. Is a singleton class
    """
    instance = None

    def __init__(self, logFileAddr, enableLogs, headless, printLogs):
        self.logFile = None
        self.logFileAddr = None
        self.enableLogs = None
        self.printLogs = None
        self.headless = None
        self.setConfig(logFileAddr=logFileAddr, enableLogs=enableLogs, headless=headless, printLogs=printLogs)

    def setConfig(self, logFileAddr=None, enableLogs=None, headless=None, printLogs=None):
        # set config after instance initialization

        # close the old file if there was any
        if self.logFile is not None:
            self.logFile.close()
            self.logFile = None

        # receive the new parameters
        # only replace if it changes the parameters
        if logFileAddr is not None: self.logFileAddr = logFileAddr
        if enableLogs is not None: self.enableLogs = enableLogs
        if printLogs is not None: self.printLogs = printLogs
        if headless is not None: self.headless = headless

        if self.enableLogs and self.logFileAddr is not None:
            self.logFile = open(self.logFileAddr, 'a')

        if self.headless:
            if self.logFile is None:
                raise Exception('Cannot be headless without log file!')

    @staticmethod
    def getInstance(logFileAddr=None, enableLogs=False, headless=False, printLogs=False):
        if ScriptOutputStream.instance is None:
            ScriptOutputStream.instance = ScriptOutputStream(logFileAddr, enableLogs, headless, printLogs)

        return ScriptOutputStream.instance

    def flushToFile(self):
        # flushes logfile object to file
        if self.logFile is None:
            return

        self.logFile.close()
        self.logFile = open(self.logFileAddr, 'a')

    def log(self, text, headlessprint=False, logAndPrint=None):

        if logAndPrint is None:
            logAndPrint = self.printLogs

        if not self.enableLogs:
            return

        if self.logFile is None:
            raise Exception('No log file!')

        if headlessprint:
            text = '(headless stdout): {}'.format(text)

        self.logFile.write('{}: {}\n'.format(
            datetime.today().strftime('%d/%m/%Y %H:%M:%S'),
            text.strip()))

        if logAndPrint and (not self.headless):
            self.print(text)

    def print(self, text):
        """
        Print the text input to stdout if available
        """
        if self.headless:
            # headless script does not have a stdout, so just log it to the file
            self.log(text, headlessprint=True)
        else:
            print(text)

    def printlg(self, text):
        """
        Print the text and also log to logfile
        """
        # if headless, a print writes to log file, so remove duplicate call
        if (not self.headless): self.print(text)

        # if printlogs is enabled, then the print call above has already printed the log
        # so set as false
        self.log(text, logAndPrint=(False if self.printLogs else None))