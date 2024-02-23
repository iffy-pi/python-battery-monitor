import argparse
import json
import sys
from argparse import Namespace
from os import path

import keyring

from scripts.TimeString import TimeString

PLUG_CREDENTIAL_STORE = 'Battery_Monitor_TP_Link_Credentials'
EMAIL_CREDENTIAL_STORE = 'Battery_Monitor_Email_Credentials'


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
        self.alertPeriod = args.alert
        self.maxAttempts = args.max_attempts
        self.emailUsername = args.email_cred
        self.emailRecipient = args.email_to
        self.plugAccUsername = args.plug_cred
        self.noLogs = args.nologs
        self.printLogs = args.printlogs
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

        if self.emailUsername is not None and keyring.get_password(EMAIL_CREDENTIAL_STORE, self.emailUsername) is None:
            raise ArgumentException(f'Could not retrieve email credentials for email "{self.emailUsername}", are they stored in generic credential "{EMAIL_CREDENTIAL_STORE}"?')

        if self.plugAccUsername is not None and keyring.get_password(PLUG_CREDENTIAL_STORE, self.plugAccUsername) is None:
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
        help="The percentage increment the script should check the battery at, e.g means check every 5%%",
        default=5,
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
        "-email-cred",
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
        help="The recipient of alert emails",
    )

    argParser.add_argument(
        "-plug-cred",
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

def convert_config_to_args(configFile, sysArgs, overrideSysArgs=False):
    with open(configFile, 'r') as file:
        config = json.load(file)

    args = []
    for key in config:
        cmdLineFlag = f'--{key}' if type(config[key]) == bool else f'-{key}'

        if not overrideSysArgs and cmdLineFlag in sysArgs:
            continue

        if type(config[key]) == bool and config[key]:
            args.append(f'--{key}')
            continue

        args.append(f'-{key}')
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
        newArgs = convert_config_to_args(args.config, sys.argv)
        sys.argv += newArgs

    args = make_arg_parser().parse_args()
    return CommandLineArgs(args)


if __name__ == '__main__':
    parse_args()