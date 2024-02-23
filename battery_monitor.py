import os
import sys
import traceback

import keyring

script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
if script_loc_dir not in sys.path:
    sys.path.append(script_loc_dir)

from scripts.functions import send_notification, error_notification, new_log_file
from scripts.BatteryMonitor import BatteryMonitor, EmailNotifier
from scripts.SmartPlugController import *
from scripts.TimeString import TimeString
from scripts.ScriptOutputStream import ScriptOutputStream
from scripts.arg_parsing import parse_args, PLUG_CREDENTIAL_STORE, EMAIL_CREDENTIAL_STORE

UNLOCK_FILE = ''

def started_notif(logFileAddr):
    send_notification('Headless Battery Monitor', 'Battery monitor started successfully and running in headless mode. Log file: {}'.format(os.path.split(logFileAddr)[1]))

def testing():
    pass

def main():
    headless = (sys.stdout is None)
    # Will be used to capture any argument parsing failures before actual logs are created
    initLogFile = os.path.expanduser('~\\Battery_Monitor_Initial_Log.log')
    actualLogFile = None
    scout = ScriptOutputStream.getInstance(logFileAddr=initLogFile, enableLogs=True, headless=headless, printLogs=False)

    try:
        # Parse arguments
        args = parse_args()
        headless = args.headless

        # Check if the log directory exists
        if not os.path.exists(args.logDir):
            raise Exception(f'Log Directory "{args.logDir}" does not exist')

        # Verified log directory exists, set proper logging configuration
        actualLogFile = new_log_file(args.logDir)
        scout.setConfig(
            logFileAddr=actualLogFile,
            enableLogs=(not(args.testing or args.noLogs)),
            headless=headless,
            printLogs=args.printLogs,
        )

        # Print logging information
        if scout.enableLogs:
            scout.print('Logging To: {}\n'.format(scout.logFileAddr))
            if scout.printLogs:
                scout.print('Printing logs is turned on!')
        else:
            scout.print('No logs are being made. \n')

        # Run test at this point
        if args.testing:
            testing()
            return 0

        # Check argument logic
        args.checkArgs()

        plugCreds = None
        if args.plugAccUsername is not None:
            plugPass = keyring.get_password(PLUG_CREDENTIAL_STORE, args.plugAccUsername)
            plugCreds = (args.plugAccUsername, plugPass)

        emailCreds = None
        if args.emailUsername is not None:
            emailPass = keyring.get_password(EMAIL_CREDENTIAL_STORE, args.emailUsername)
            emailCreds = (args.emailUsername, emailPass)

        smartPlug = SmartPlugController(
            args.plugIP,
            args.plugName,
            args.wifi,
            tplink_creds=plugCreds,
            TPLinkAvail=plugCreds is not None)

        emailer = None
        if emailCreds is not None and args.emailRecipient is not None:
            emailer = EmailNotifier(emailCreds, args.emailRecipient)

        bm = BatteryMonitor(
            args.batteryMin,
            args.batteryMax,
            args.grain,
            TimeString.parse(args.alertPeriod),
            args.maxAttempts,
            scout,
            smartPlug,
            emailer,
            headless=headless
        )

        if headless:
            started_notif(scout.logFileAddr)

        bm.printConfig()
        scout.print('')
        scout.flushToFile()

        bm.monitorBattery()
        scout.log('Script Ended')

    except Exception as e:
        scout.printlg('\nScript Exception: "{}"'.format(e))
        if headless:
            # WRITE error to script
            scout.log(traceback.format_exc())
            error_notification(e, actualLogFile if actualLogFile is not None else initLogFile)
        else:
            traceback.print_exc()

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())