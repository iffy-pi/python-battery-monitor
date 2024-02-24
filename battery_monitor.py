import os
import sys
import traceback

import keyring

script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
if script_loc_dir not in sys.path:
    sys.path.append(script_loc_dir)

from scripts.bm_logging import log_to_file, logger, console, enable_logs, print_logs, get_log_file_addr, \
    flush_logs, is_logs_enabled, new_log_file, is_printing_logs, set_headless

from scripts.functions import send_notification, error_notification
from scripts.BatteryMonitor import BatteryMonitor, EmailNotifier
from scripts.SmartPlugController import *
from scripts.TimeString import TimeString
from scripts.arg_parsing import parse_args, PLUG_CREDENTIAL_STORE, EMAIL_CREDENTIAL_STORE

UNLOCK_FILE = ''

def started_notif(logFileAddr):
    send_notification('Headless Battery Monitor', 'Battery monitor started successfully and running in headless mode. Log file: {}'.format(os.path.split(logFileAddr)[1]))

def testing():
    pass

def main():
    headless = (sys.stdout is None)
    try:
        # Parse arguments
        args = parse_args()
        headless = args.headless

        # Check if the log directory exists
        if not os.path.exists(args.logDir):
            raise Exception(f'Log Directory "{args.logDir}" does not exist')

        # Verified log directory exists, set proper logging configuration
        actualLogFile = new_log_file(args.logDir)
        log_to_file(actualLogFile)
        set_headless(headless)
        enable_logs(not(args.testing or args.noLogs))
        print_logs(args.printLogs)

        # Print logging configuration
        if is_logs_enabled():
            console.info(f'Logging To {get_log_file_addr()}')
            if is_printing_logs():
                console.info(f'Logs are also printed to stdout.')
        else:
            console.info('Logs are not being made')

        flush_logs()

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
            smartPlug,
            emailer,
            headless=headless
        )

        logger.info('Script Started')

        if headless:
            started_notif(get_log_file_addr())
            logger.info('Running in headless mode')

        logger.info(f'min={args.batteryMin}%, max={args.batteryMax}%, grain={args.grain}%, alertEvery={TimeString.parse(args.alertPeriod)}s, maxAttempts={args.maxAttempts}')
        logger.info(f'Plug Info: Network="{smartPlug.home_network}", Plug IP={smartPlug.plug_ip}, Plug Name="{smartPlug.plug_name}"')

        if plugCreds is not None:
            logger.info(f'Plug Credentials: {plugCreds[0]}')
        if emailCreds is not None:
            logger.info(f'Email Credentials: {emailCreds[0]}')

        if emailer is not None:
            logger.info(f'Email Alerts To: {emailer.recipient}')

        flush_logs()

        bm.monitorBattery()
        logger.info('Script Ended')

    except Exception as e:
        logger.error('Script Exception: "{}"'.format(e))
        if headless:
            # WRITE error to script
            logger.error(traceback.format_exc())
            error_notification(e, get_log_file_addr())
        else:
            traceback.print_exc()

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())