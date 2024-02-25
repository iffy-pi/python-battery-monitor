import argparse
import json
import sys
from argparse import Namespace
from os import path


from scripts.TimeString import TimeString
from scripts.functions import get_plug_password, get_emailer_password, PLUG_CREDENTIAL_STORE, EMAIL_CREDENTIAL_STORE

class ArgumentException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class CommandLineArgs:
    def __init__(self, args: Namespace):
        self.headless = args.headless
        self.configJSON = args.config
        self.plugIP = args.plug_ip
        self.plugName = args.plug_name
        self.wifi = args.home_wifi
        self.logDir = args.logdir
        self.batteryMin = args.min
        self.batteryMax = args.max
        self.grain = args.grain
        self.adaptivity = args.adaptivity
        self.alertPeriod = args.alert
        self.maxAttempts = args.max_attempts
        self.emailUsername = args.email_creds
        self.emailRecipient = args.email_to
        self.plugAccUsername = args.plug_creds
        self.noLogs = args.nologs
        self.printLogs = args.printlogs
        self.noLogFile = args.nologfile
        self.testing = args.testing

    def checkArgs(self):
        """
        Checks args for semantic legality
        """

        if not path.exists(self.logDir):
            raise ArgumentException(f'Log Directory "{self.logDir}" does not exist')


        nonEmpties = [
            ('-plug-ip', self.plugIP),
            ('-plug-name', self.plugName),
            ('-home-wifi', self.wifi)
        ]
        for name, value in nonEmpties:
            if not value:
                raise ArgumentException(f'{name} must be non-empty string')

        gtZero = [
            ('-min', self.batteryMin),
            ('-max', self.batteryMax),
            ('-grain', self.grain),
            ('-max-attempts', self.maxAttempts)
        ]

        for name, value in gtZero:
            if value <= 0:
                raise ArgumentException(f'{name} must be non-zero positive integer')

        if self.batteryMin >= self.batteryMax:
            raise ArgumentException(f'Minimum battery ({self.batteryMin}%) must be less than maximum battery ({self.batteryMax}%)')

        try:
            secs = TimeString.parse(self.alertPeriod)
        except Exception:
            raise ArgumentException('Could not parse time string specified for -alert')

        if self.emailRecipient is not None and self.emailUsername is None:
            raise ArgumentException('Specified email recipient but no email credentials')

        if self.emailUsername is not None and get_emailer_password(self.emailUsername) is None:
            raise ArgumentException(f'Could not retrieve email credentials for email "{self.emailUsername}", are they stored in generic credential "{EMAIL_CREDENTIAL_STORE}"?')

        if self.plugAccUsername is not None and get_plug_password(self.plugAccUsername) is None:
            raise ArgumentException(f'Could not retrieve TP Link credentials for username "{self.plugAccUsername}", are they stored in generic credential "{PLUG_CREDENTIAL_STORE}"?')


def make_arg_parser(configFirst=False):
    def required_if_no_config():
        if not configFirst:
            return True
        return '-config' not in sys.argv

    # Contains all regular arguments
    argParser = argparse.ArgumentParser()
    argParser.add_argument(
        '--headless',
        '--headless',
        action='store_true',
        help='Will not have an interactive console'
    )

    argParser.add_argument(
        "-config",
        required=False,
        type=str,
        metavar='<file path>',
        help="Path to config.json file which holds configuration to use",
    )

    argParser.add_argument(
        "-plug-ip",
        required=required_if_no_config(),
        type=str,
        metavar='<IP Address>',
        help="The IP Address of the Kasa Smart Plug e.g. 192.168.1.1",
    )

    argParser.add_argument(
        "-plug-name",
        required=required_if_no_config(),
        type=str,
        metavar='<Plug Name>',
        help="The name of the Kasa Smart Plug as is on your Kasa Account",
    )

    argParser.add_argument(
        "-home-wifi",
        required=required_if_no_config(),
        type=str,
        metavar='<Home Wifi Name>',
        help="The name of your home wifi network, used to determine if your laptop is at home",
    )

    argParser.add_argument(
        "-logdir",
        required=required_if_no_config(),
        type=str,
        metavar='<file path>',
        help="The directory to store logs in",
    )

    argParser.add_argument(
        "-min",
        required=False,
        type=int,
        metavar='<Minimum Battery Percentage>',
        help="Lowest battery percentage to trigger alert, default: 25",
        default=25,
    )

    argParser.add_argument(
        "-max",
        required=False,
        type=int,
        metavar='<Maximum Battery Percentage>',
        help="Highest battery percentage to trigger alert, default: 85",
        default=85,
    )

    argParser.add_argument(
        "-grain",
        required=False,
        type=int,
        metavar='<Battery Check Increment>',
        help="How often (in battery percentage) should the script check the battery e.g. 5 for every 5% ",
        default=5,
    )

    argParser.add_argument(
        "-adaptivity",
        required=False,
        type=float,
        metavar='<Battery Check Increment>',
        help="How adaptive sleep predictions are. A floating point value between 0 and 1",
        default=0.90,
    )

    argParser.add_argument(
        "-alert",
        required=False,
        type=str,
        metavar='<alert_period>',
        help="Amount of time between sending battery alerts, default: 5m",
        default='5m'
    )

    argParser.add_argument(
        "-max-attempts",
        required=False,
        type=int,
        metavar='<Alert Attempts>',
        help="The maximum number of times an attempts made to notify you (Only done when smart plug control fails)",
        default=20,
    )

    argParser.add_argument(
        "-email-creds",
        required=False,
        type=str,
        metavar='<username>',
        help=f"The email of the account used to send emails. Password must be stored as a generic credential under '{EMAIL_CREDENTIAL_STORE}'",
    )

    argParser.add_argument(
        "-email-to",
        required=False,
        type=str,
        metavar='<email>',
        help="The recipient of alert emails. Requires -email-cred argument",
    )

    argParser.add_argument(
        "-plug-creds",
        required=False,
        type=str,
        metavar='<email>',
        help=f"The email of your TP Link Account. Only use if you have TP Link Command Line Utility installed. Password must be stored as a generic credential under '{PLUG_CREDENTIAL_STORE}'",
    )

    argParser.add_argument(
        '--nologs',
        '--nologs',
        action='store_true',
        help='Disable logs'
    )

    argParser.add_argument(
        '--nologfile',
        '--nologfile',
        action='store_true',
        help='Logs will not be saved to any file, but instead will be printed to console'
    )

    argParser.add_argument(
        '--printlogs',
        '--printlogs',
        action='store_true',
        help='print all log messages to the console'
    )

    argParser.add_argument(
        '--testing',
        '--testing',
        action='store_true',
        help='Run code in testing function and then exit'
    )

    return argParser

def gen_cli_args_from_config(configFile: str, sysArgs: list, useSysArgIfExists: bool=True) -> list:
    """
    Generates the list of command line arguments from the JSON config fil
    @param configFile: The JSON config file
    @param sysArgs: The original command line argumentts
    @param useSysArgIfExists: When true, if a command line flag is specified in the original set of arguments it will NOT be replaced by the one in the config file
    @return:
    """
    with open(configFile, 'r') as file:
        config = json.load(file)

    args = []
    for key in config:
        cmdLineFlag = key
        if useSysArgIfExists and cmdLineFlag in sysArgs:
            # Do not generate this argument if it exists in the system arguments
            continue

        if type(config[key]) == bool and config[key]:
            args.append(cmdLineFlag)
            continue

        args.append(cmdLineFlag)
        args.append(str(config[key]))

    return args

def parse_args() -> CommandLineArgs:
    argParser = make_arg_parser(configFirst=True)

    # If config arg is available, translate to command line args
    # Then parse again
    args = argParser.parse_args()
    if args.config is not None:
        if not path.exists(args.config):
            raise ArgumentException(f'Config file "{args.config}" does not exist!')
        newArgs = gen_cli_args_from_config(args.config, sys.argv)
        sys.argv += newArgs

    args = make_arg_parser().parse_args()
    return CommandLineArgs(args)

def get_args_from_config_in_sysargs() -> CommandLineArgs:
    """
    Returns set of arguments for -config in command line, and restores the original set of system arguments
    """
    sysArgs = list(sys.argv)

    if '-config' not in sysArgs:
        raise ArgumentException('-config not in arguments')

    ind = sysArgs.index('-config')
    configFile = sysArgs[ind+1]
    sysArgs.pop(ind+1)
    sysArgs.pop(ind)

    if not path.exists(configFile):
        raise ArgumentException(f'Config file "{configFile}" does not exist!')

    newArgs = gen_cli_args_from_config(configFile, [])
    sys.argv = [sys.argv[0]] + newArgs
    args = make_arg_parser().parse_args()
    sys.argv = sysArgs

    return CommandLineArgs(args)


if __name__ == '__main__':
    parse_args()