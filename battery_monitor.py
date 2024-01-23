import os
import sys
import traceback
from datetime import datetime as mydt
from time import time, sleep
import threading
from winsound import Beep as beep
import psutil
import argparse
from winotify import Notification

script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
if script_loc_dir not in sys.path:  
    sys.path.append(script_loc_dir)

from SmartPlugController import *
from EmailBot import EmailBot
from TimeString import TimeString
from TimerSleep import timerSleep

CONFIG = {
    'script' : {
        # Email address and password of the account used to send email alerts
        # A tuple in the format of (username, password)
        'email_bot_account_creds': None,

        # Email address that will receive email alerts generated by the script
        'email_alert_recipient': None,

        # Directory where log files are written to 
        'log_files_dir': None,

        # Set to true if the TP Link Command Line Utility (https://apps.microsoft.com/store/detail/tplink-kasa-control-command-line/9ND8C9SJB8H6?hl=en-ca&gl=ca) is installed on your computer 
        'tp_link_cmd_installed' : False,

        # TP Link Account Credentials, tuple in the format of (username, password)
        # Recommended to use keyring rather than storing credentials in the script directly
        'tp_link_account_creds': None
    },

    # Configurations for script arguments
    # These are also used to contain default values
    'args' : {
        # IP Address of the plug
        'plug_ip': None,
        'plug_name': None,
        # Home Wifi Network Name
        'home_wifi': None,
        # Battery minimums and maximums
        'battery_min': 25,
        'battery_max': 85,
        # Check battery every grain %
        'grain': 5,
        # How many seconds to wait between each alert
        'alert_period_secs': 300,
        # Maximum number of alert attempts
        'max_alert_attempts': 20
    }

}

# load a private config if we have any
# Private config contains information in CONFIG dictonary, in python file private/config.py
# Used for importing config that should not be visible to the public
privConfigFile  = os.path.join(script_loc_dir, 'private', 'config.py')
if os.path.exists(privConfigFile):
    from private.config import CONFIG as CONFIG


SCRIPT_CONFIG = CONFIG['script']
ARGS_CONFIG = CONFIG['args']

# Icon used for windows10 notification
WIN_NOTIF_ICON = os.path.join(script_loc_dir, 'roboticon.png')
LOG_FILE_ADDR = os.path.join( SCRIPT_CONFIG['log_files_dir'], 'status_{}_{}.log'.format(mydt.today().strftime('%H%M_%d_%m_%Y'), int(time.time())))
UNLOCK_FILE = os.path.join(CONFIG['script']['log_files_dir'], 'unlock_signal.txt')


class UnlockSignalException(Exception):
    def __init__(self):
        self.message = 'Unlock signal was set to high'
        super().__init__(self.message)


class ScriptOutputStream():
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
            mydt.today().strftime('%d/%m/%Y %H:%M:%S'), 
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


class ScriptSleepController():
    '''
    This class is used to manage putting the script to sleep until the next battery check is required
    
    Accounts for sleep predictions, modifying predictions when battery is near thresholds.

    Designed to be a  Singleton Class, so is used as a gloval variable in the script.
    '''
    def __init__(self, batteryFloor: int, batteryCeiling: int, checkIntervalPercentage:int = 5, initPred: int = 10, predAdaptivity: float = 0.89):
        '''
        Initialize a sleep controller object.
        - `batteryFloor`   : The minimum battery percentage.
        - `batteryCeiling` : The maximum battery percentage.
        - `checkIntervalPercentage` : Sleep controller will predict sleep periods such that battery will be checked every `checkIntervalPercentage`%.
        - `initPred` : The initial sleep prediction to make without any history. 
        - `predAdaptivity` : A value between 0 and 1 that indicates how adaptive the controller's predictions are to recent behaviour instead overall history. 
            Higher values result in recent behaviour having more weight than overall history.
        '''
        self.curPercent = None
        self.charging = None
        self.prevPercent = None
        self.sleepPeriod = None
        self.batteryFloor = batteryFloor
        self.batteryCeiling = batteryCeiling
        self.checkIntervalPercentage = checkIntervalPercentage
        self.predAdaptivity = predAdaptivity
        self.initSleepPred = initPred
        self.drift = 0
        self.lastUnlockTime = None

    @staticmethod
    def log(txt):
        SCOUT.log('{}'.format(txt))

    @staticmethod
    def printlg(txt):
        SCOUT.printlg('{}'.format(txt))

    @staticmethod
    def print(txt):
        SCOUT.print('{}'.format(txt))

    def unlock_signal_high(self):
        with open(UNLOCK_FILE, 'r') as file:
            cont = file.read().strip()

        if cont != '1':
            return False

        # Set the unlock signal to be read
        with open(UNLOCK_FILE, 'w') as file:
            file.write('0')

        # Ony raise exception if its within time limits
        if self.lastUnlockTime is not None:
            curTime = time.time_ns()
            diffSecs = (curTime - self.lastUnlockTime) / float(1E9)
            if diffSecs < 60 * 60:
                return False

        self.lastUnlockTime = time.time_ns()
        ScriptSleepController.log('Unlock Signal Was Read To Be High')
        return True


    def checkUnlockSignal(self):
        if self.unlock_signal_high():
            raise UnlockSignalException()


    def sleep(self, secs: int = 0, mins: int = 0, hours: int = 0, verbose=True, checkUnlockSignal=False):
        """
        Puts process to sleep for specified amount of time.

        If `verbose`, then a time remaining countdown will also be maintained on the console

        If script is headless, `verbose` will always be false.
        If checkUnlockSignal is true, unlock file will be checked
        Will throw UnlockSignalException if unlock signal caused it to break
        """
        if checkUnlockSignal:
            ScriptSleepController.log(f'Script will be checking unlock signal  in UNLOCK_FILE: {UNLOCK_FILE}')
        secs = secs + (mins*60) + (hours*3600)
        
        if secs == 0:
            return
        
        # if we are in headless there is no console
        verbose = False if HEADLESS else verbose

        # flush logs before going to sleep
        SCOUT.flushToFile()

        if verbose:
            timerSleep(secs, checkFnc=self.checkUnlockSignal if checkUnlockSignal else None)
            return

        if checkUnlockSignal:
            # Sleep 1 second and check the signal each time
            for _ in range(secs):
                sleep(1)
                self.checkUnlockSignal()
            return

        # Just regular timer sleep
        sleep(secs)
        return

    def addToDrift(self, secs):
        '''
        Adds `secs` to drift.
        Sleep predictions are based on the battery percentage between calls to sleep function.
        We can't use time.time() to track the time between calls as that is the UNIX timestamp, so if the PC hibernates then sleep periods become invalid
        To make predictions more accurate, significant time spent inbetween calls must be tracked e.g. alert sleeps
        These can be tracked with the drift member, which is included when predicting the next sleep period.
        '''
        self.drift += secs

    def trackedSleep(self, secs:int):
        """
        Sleep the specified number of seconds and adds it as drift
        """
        self.addToDrift(secs)
        self.sleep(secs=secs)

    def predictSleepPeriod(self):
        """
        Predicts the amount of time to sleep to check the battery every `checkIntervalPercentage`%
        """
        # predicts the amount of time to sleep so that we check the battery every (des_percent_drop)%

        # based on process burst prediction: q_(n+1) = a*t_n + (1-a)q_n 
        # init_prediction (q_0) is first prediction for amount of seconds to change delta%
        # window is the measured amount of time in seconds between current and prev battery measurements
        # a is weighting parameter, a=1 means only base on current behaviour, a=0 means based on previous behaviour
        # cur_ct (t_n) is the amount of time it took to change delta%
        # pred_ct (q_n) is the predicted time it took to change delta% ( corresponds to q_(n-1))
        # next_pred_ct (q_(n+1)) is the predicted time to change delta% for next iteration

        if self.prevPercent is None or self.sleepPeriod is None:
            ScriptSleepController.log('Initial Prediction')
            return self.initSleepPred

        # Include tracked drift as time between calls
        prev_period = self.sleepPeriod + self.drift
        self.drift = 0

        percent_drop_per_sec = abs(self.curPercent - self.prevPercent) / float(prev_period)

        if percent_drop_per_sec == 0.0:
            # double predictions until we get some percentage drop
            ScriptSleepController.log('No Change, doubled the prediction.')
            return prev_period*2

        # calculate the actual time it would take to drop by our desired percent
        actual_drop_period = self.checkIntervalPercentage / percent_drop_per_sec

        # use the round robin formulat to calculate our next prediction
        next_pred = int( self.predAdaptivity*actual_drop_period + (1-self.predAdaptivity)*prev_period )

        return next_pred

    def getNextSleepPeriod(self):
        '''
        Used to get the next sleep period for battery checks.

        Uses the prediction made with `predictSleepPeriod` but overrides it
        if the time to reach one of the thresholds is less than the prediction.
        '''
        cur_percent = self.curPercent
        pred_sleep_period = self.predictSleepPeriod()

        secs_per_percent = pred_sleep_period / self.checkIntervalPercentage

        percent_till_floor = abs(cur_percent - self.batteryFloor)
        percent_till_ceiling = abs(self.batteryCeiling - cur_percent)

        # minimum sleep period will not be shorter than 60 seconds
        fall_below_thresh_time = max(60, int(secs_per_percent * percent_till_floor))
        go_above_thresh_time = max(60, int(secs_per_percent * percent_till_ceiling))

        # Use threshold times if the time to reach them is less than prediction
        use_below_thresh = not self.charging and (fall_below_thresh_time < pred_sleep_period)
        use_above_thresh = self.charging and (go_above_thresh_time < pred_sleep_period)

        if use_below_thresh or use_above_thresh:
            ScriptSleepController.printlg('Using Pre-emptive threshold prediction')
            return fall_below_thresh_time if use_below_thresh else go_above_thresh_time

        ScriptSleepController.printlg('Using standard prediction')
        return pred_sleep_period

    def sleepTillNextBatteryCheck(self):
        self.prevPercent = self.curPercent
        battery = psutil.sensors_battery()
        self.curPercent, self.charging = battery.percent, battery.power_plugged

        self.sleepPeriod = self.getNextSleepPeriod()

        ScriptSleepController.printlg(f'Sleeping {TimeString.make(self.sleepPeriod)}...')
        try:
            self.sleep( secs=self.sleepPeriod , checkUnlockSignal=True)
        except UnlockSignalException as e:
            ScriptSleepController.log('Recieved UnlockSignalException. Resetting Sleep History and Predictions')
            self.prevPercent = None
            self.sleepPeriod = None
            send_notification('Sleep History Reset', "The script's learned sleep history has been reset to accomodate for the increase in power usage")

def scriptErrNotif(errorObj, logFilePath):
    title = 'Headless Battery Monitor Failure'
    body = str(errorObj)
    logFilePath = os.path.abspath(logFilePath)
    path = "file:///{}".format(logFilePath.replace("\\", "/"))

    toast = Notification("Battery Monitor Bot", title, msg=body, icon=WIN_NOTIF_ICON)
    toast.add_actions(label="Open log file", launch=path)
    toast.show()

def get_battery_info():
    battery = psutil.sensors_battery() 
    return battery.percent, battery.power_plugged

def do_beeps():
    # use winsound to generate beeps
    for _ in range(1):
        beep(750, 1000)

def do_beeps_threaded():
    # just runs it in its own thread
    x = threading.Thread(target=do_beeps)
    x.start()

def send_notification(title, body):
    toast = Notification('Battery Monitor Bot', title, msg=body, icon=WIN_NOTIF_ICON)
    toast.show()


def get_alert_info(isLow, last):
    
    curbattery, _ = get_battery_info()
    descs = {
        'low': ( 'Low', 'below', 'minimum', 'not'),
        'high': ('High', 'above', 'maximum', 'still' )
    }

    desc = descs[ 'low' if isLow else 'high' ]

    title = '{} Battery Alert'.format(desc[0])
    if last: title = 'FINAL CALL - {}'.format(title)

    email_title = 'AJAK Auto Battery Monitor - {}'.format(title)

    body = '{}\n{}'.format(
        'Battery ({batt}%) is near or {boundarydesc} specified {limdesc} ({batterylim}%) and is {chargeverb} charging.'.format(
            batt=curbattery,
            boundarydesc=desc[1],
            limdesc=desc[2],
            batterylim= BATTERY_FLOOR if isLow else BATTERY_CEILING,
            chargeverb=desc[3],
        ),
        'Manual assistance is required.'
    )

    return email_title, title, body

def send_battery_alerts(isLow, email=False, sound=False, last=False):
    '''
    Sends alerts about battery conditions. If `isLow` is true, it will be low battery conditions,
    otherwise will be high battery conditions.

    If `email` is true, an email alert will be sent (if credentials are available).

    If `sound` is true, a buzzer sound will be made.

    `last` is used to indicate that this is the last battery alert.
    '''
    email_title, title, body = get_alert_info(isLow, last)

    if sound:
        SCOUT.printlg('Playing sound..')
        do_beeps_threaded()

    SCOUT.printlg('Showing Windows Notification...')
    send_notification(title, body)

    if email and EMAILBOT is not None:
        subject = '{} - {}'.format(email_title, mydt.now().strftime('%b %d %Y %H:%M'))
        EMAILBOT.sendEmail(subject, body, SCRIPT_CONFIG['email_alert_recipient'], important=(isLow or last))
        SCOUT.printlg('Email Alert Sent!')

def handle_battery_case(high_battery, low_battery):
    _ , charging = get_battery_info()
    attempts_made = 0

    while (low_battery and not charging) or (high_battery and charging):
        if attempts_made == MAX_ATTEMPTS:
            SCOUT.printlg('No More Attempts Remaining!')
            break

        SCOUT.printlg('Attempting Automatic Smart Plug Control')
        try:
            SMART_PLUG_CONTROLLER.set_plug(on=low_battery, off=high_battery)
            SMART_PLUG_CONTROLLER.print_logs()
        except SmartPlugControllerException as e:
            SCOUT.printlg(f'Something went wrong: {e}')

        SCOUT.print('Waiting 5 seconds for verification')
        SLEEP_CONTROLLER.trackedSleep(5)

        _ , charging = get_battery_info()
        if ( low_battery and charging ) or ( high_battery and not charging):
            SCOUT.printlg('Issue Resolved')
            break

        msg = 'Notifying User With: Windows Notification'
        if attempts_made >= 1: msg += ', Sound'
        if attempts_made >= 2: msg += ', Email'

        SCOUT.printlg('Failed to control smart plug, manual assistance required')
        SCOUT.printlg( msg )

        send_battery_alerts(
            isLow= low_battery,
            sound=(attempts_made >= 1),
            email=(attempts_made >= 2),
            last=(attempts_made == MAX_ATTEMPTS-1)
        )
        
        wait_for = 120 if attempts_made < 2 else ALERT_PERIOD
        SCOUT.printlg(f'Waiting {TimeString.make(wait_for)} for user action...')
        SLEEP_CONTROLLER.trackedSleep(wait_for)

        attempts_made += 1

        _ , charging = get_battery_info()

def monitor_battery():
    iters = 0
    SCOUT.log('Entering While Loop')
    
    while True:
        try:
            # put sleep first, doing so to eliminate if statements
            if iters > 0:
                SLEEP_CONTROLLER.sleepTillNextBatteryCheck()

            SCOUT.log('Obtaining Battery Info')
            cur_percent, charging = get_battery_info()

            SCOUT.printlg('Battery: {}%, {}'.format(cur_percent, 'Charging' if charging else 'Not Charging'))

            low_battery = (cur_percent <= BATTERY_FLOOR) and (not charging)
            high_battery = (cur_percent >= BATTERY_CEILING) and charging

            if not ( high_battery or low_battery ):
                SCOUT.printlg('No Action Required')
                iters += 1
                continue

            SCOUT.printlg('{} Battery Detected'.format('Low' if low_battery else 'High'))
            handle_battery_case(high_battery, low_battery)
            iters += 1
        except KeyboardInterrupt:
            if HEADLESS:
                SCOUT.printlg('\nScript exited due to keyboard interrupt')
                return 
            else:
                try:
                    SCOUT.print('\nPress Ctrl+C again in 10s to end script')
                    SLEEP_CONTROLLER.trackedSleep(secs=10)
                    iters = 0
                except KeyboardInterrupt:
                    SCOUT.printlg('\nScript exited due to keyboard interrupt')
                    return

def started_notif():
    send_notification('Headless Battery Monitor', 'Battery monitor started successfully and running in headless mode. Log file: {}'.format(os.path.split(SCOUT.logFileAddr)[1]))  

def testing():
    print(SCRIPT_CONFIG['tp_link_cmd_installed'])


def main():

    global SCOUT
    global BATTERY_FLOOR
    global BATTERY_CEILING
    global ALERT_PERIOD
    global MAX_ATTEMPTS
    global HEADLESS
    global SMART_PLUG_CONTROLLER
    global SLEEP_CONTROLLER
    global EMAILBOT

    SCOUT = ScriptOutputStream.getInstance(logFileAddr=LOG_FILE_ADDR, enableLogs=False, headless=False, printLogs=False)
    
    HEADLESS = (sys.stdout is None)
    
    try:
        parser = argparse.ArgumentParser()

        parser.add_argument(
            "-plug-ip",
            required= (ARGS_CONFIG.get('plug_ip') is None),
            type = str,
            metavar='<IP Address>',
            help = "The IP Address of the Kasa Smart Plug e.g. 192.168.1.1",
            default = ARGS_CONFIG.get('plug_ip')
        )

        parser.add_argument(
            "-plug-name",
            required= (ARGS_CONFIG.get('plug_name') is None),
            type = str,
            metavar='<Plug Name>',
            help = "The name of the Kasa Smart Plug as is on your Kasa Account",
            default = ARGS_CONFIG.get('plug_name')
        )

        parser.add_argument(
            "-home-wifi",
            required=(ARGS_CONFIG.get('home_wifi') is None),
            type = str,
            metavar='<Home Wifi Name>',
            help = "The name of your home wifi network, used to determine if your laptop is at home",
            default = ARGS_CONFIG.get('home_wifi')
        )

        parser.add_argument(
            "-min",
            required=False,
            type = int,
            metavar='<Minimum Battery Percentage>',
            help = "Lowest battery percentage to trigger alert, default: 25",
            default = ARGS_CONFIG['battery_min']
        )

        parser.add_argument(
            "-max",
            required=False,
            type = int,
            metavar='<Maximum Battery Percentage>',
            help = "Highest battery percentage to trigger alert, default: 85",
            default = ARGS_CONFIG['battery_max']
        )

        parser.add_argument(
            "-grain",
            required=False,
            type = str,
            metavar='<Battery Check Increment>',
            help = "The percentage increment the script should check the battery at, e.g means check every 5%%",
            default = ARGS_CONFIG['grain']
        )

        parser.add_argument(
            "-alert",
            required=False,
            type = str,
            metavar='<alert_period>',
            help = "Amount of time between sending battery alerts, default: 5m",
            default = TimeString.make(ARGS_CONFIG['alert_period_secs'])
        )

        parser.add_argument(
            "-max-attempts",
            required=False,
            type = int,
            metavar='<Alert Attempts>',
            help = "The maximum number of times an attempts made to notify you (Only done when smart plug control fails)",
            default = ARGS_CONFIG['max_alert_attempts']
        )

        parser.add_argument(
            '--nologs',
            '--nologs',
            action='store_true',
            help='Disable logs'
        )

        parser.add_argument(
            '--printlogs',
            '--printlogs',
            action='store_true',
            help='print all log messages to the console'
        )

        parser.add_argument(
            '--headless',
            '--headless',
            action='store_true',
            help='Will not have an interactive console'
        )

        parser.add_argument(
            '--testing',
            '--testing',
            action='store_true',
            help='Run code in testing function and then exit'
        )

        options = parser.parse_args()

        ALERT_PERIOD = 300
        BATTERY_FLOOR = options.min
        BATTERY_CEILING = options.max
        MAX_ATTEMPTS = options.max_attempts
        HEADLESS = options.headless

        SCOUT.setConfig(
            logFileAddr=LOG_FILE_ADDR,
            enableLogs=(not (options.testing or options.nologs)),
            headless=options.headless,
            printLogs=options.printlogs
            )

        if SCOUT.enableLogs:
            SCOUT.print('Logging To: {}\n'.format(SCOUT.logFileAddr))
            if SCOUT.printLogs:
                SCOUT.print('Printing logs is turned on!')
        else:
            SCOUT.print('No logs are being made. \n')

        if options.testing:
            testing()
            return 0
        
        if BATTERY_FLOOR >= BATTERY_CEILING:
            raise Exception(f'Minimum battery ({BATTERY_FLOOR}%) must be less than maximum battery ({BATTERY_CEILING}%)')

        SCOUT.log('Script Started')

        if HEADLESS: started_notif()

        SCOUT.log(
            'Args: ( min={}%, max={}%, grain={}%, alert={}, attempts={})'
            .format(
                BATTERY_FLOOR, BATTERY_CEILING, options.grain, 
                options.alert, MAX_ATTEMPTS
                )
            )
        
        SCOUT.print('Script Configuration:')
        SCOUT.print(f'Battery Minimum: {BATTERY_FLOOR}%')
        SCOUT.print(f'Battery Maximum: {BATTERY_CEILING}%')
        SCOUT.print(f'Check Battery Every: {options.grain}%')
        SCOUT.print(f'Alert Period: {options.alert}')
        SCOUT.print(f'Max Alert Attempts: {MAX_ATTEMPTS}')
        SCOUT.print('')
        SCOUT.flushToFile()

        SCOUT.log('Initializing Smart Plug Controller')

        SMART_PLUG_CONTROLLER = SmartPlugController( 
            options.plug_ip, 
            options.plug_name, 
            options.home_wifi, 
            tplink_creds=SCRIPT_CONFIG['tp_link_account_creds'],
            TPLinkAvail=SCRIPT_CONFIG['tp_link_cmd_installed'])
        
        SCOUT.log('Initializing Sleep Controller')

        SLEEP_CONTROLLER = ScriptSleepController(
            BATTERY_FLOOR,
            BATTERY_CEILING,
            checkIntervalPercentage=options.grain)
        
        SCOUT.log('Initializing Email Bot')

        botcreds = SCRIPT_CONFIG['email_bot_account_creds']
        EMAILBOT = None
        if botcreds is not None:
            EMAILBOT = EmailBot('smtp.gmail.com', botcreds[0], botcreds[1])

        monitor_battery()
        SCOUT.log('Script Ended')

    except Exception as e:
        SCOUT.printlg('\nScript Exception: "{}"'.format(e))

        if HEADLESS:
            # WRITE error to script
            SCOUT.log(traceback.format_exc())
            scriptErrNotif(e, LOG_FILE_ADDR)
        else:
            traceback.print_exc()

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())