import os
import sys
import traceback

import psutil # get battery information
import argparse # command line arguments
import re

#dateitme
from datetime import datetime as mydt
import time       # importing for getting time

# email packages
import keyring
import smtplib
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import COMMASPACE
from email import encoders

# Windows notifications
from winotify import Notification
from winsound import Beep as beep
import threading

script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
if script_loc_dir not in sys.path:  sys.path.append(script_loc_dir)
from SmartPlugController import SmartPlugController

privlocdir = os.path.join(script_loc_dir, 'private')
if privlocdir not in sys.path:  sys.path.append(privlocdir)
from privateconfig import *

# Icon used for windows10 notification
WIN_NOTIF_ICON = os.path.join(script_loc_dir, 'roboticon.png')



LOG_FILE_ADDR = os.path.join( LOG_FILES_DIR, 'status_{}_{}.log'.format(mydt.today().strftime('%H%M_%d_%m_%Y'), int(time.time())))

def send_email_from_bot(text, subject, mainRecipient, recipients, files=[], important=False, content="text", verbose=False):
    if not isinstance(recipients, list):
        raise Exception("{0} error: {1}".format(__file__, "recipients must be a list"))

    if mainRecipient not in recipients: recipients.insert(0, mainRecipient)

    # get the bot credentials
    sender = EMAIL_SENDER
    sender_pass = EMAIL_SENDER_PASS

    server  = 'smtp.gmail.com'
    
    if verbose: OUTSTREAM.print('Configuring Email Headers')
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = mainRecipient
    msg['Cc'] = ( ";".join(recipients) ).replace("\n\r ", "")
    if important:
        msg['X-Priority'] = "1"
        msg['X-MSMail-Priority'] = "High"


    if verbose: OUTSTREAM.print('Configuring Email Content')
    if content == "text":
        msg.attach( MIMEText(text) )
    else:
        msg.attach( MIMEText(text, content) )
    
    for filename in files:
        if verbose: OUTSTREAM.print("Attaching file ({0})".format(filename))
        with open(filename, "rb") as file:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload( file.read() )
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="{0}"'.format(os.path.basename(filename)))
            msg.attach(part)

    if verbose: OUTSTREAM.print(f'Connecting to SMTP server: {server}...')
    
    # connect to gmail smpt server with this port
    session = smtplib.SMTP(server, 587)#587

    #enable security
    session.starttls()

    #log in with the credentials of the bot
    session.login(sender, sender_pass)

    if verbose: OUTSTREAM.printlg('Sending Email...')

    session.sendmail(sender, recipients, msg.as_string())
    
    if verbose: OUTSTREAM.print('Sent')
    session.quit()

def verbose_sleep(secs=None, mins=None, hours=None):

    if not secs:
        secs = 0

    if mins: secs += mins*60

    if hours: secs += hours*3600

    OUTSTREAM.flushToFile()

    if HEADLESS:
        time.sleep(secs)
        return

    prev_str_len = -1
    for remaining in range(secs, 0, -1):
        sys.stdout.write("\r")

        info_str = "{:d} seconds remaining...".format(remaining)
        cur_str_len = len(info_str)

        while len(info_str) < prev_str_len:
            info_str += ' '

        prev_str_len = len(info_str)

        sys.stdout.write(info_str)
        sys.stdout.flush()
        time.sleep(1)

    finish_msg = 'Done!'

    while len(finish_msg) < prev_str_len:
        finish_msg += ' '
    sys.stdout.write("\r{}\n".format(finish_msg))

def get_re_matched_groups(search_str, pattern):
    res = re.search(pattern, search_str)
    if res is None:
        return []
    else:
        return list(res.groups())

def parse_time_str_to_seconds(time_str):
    groups = get_re_matched_groups(time_str, "([0-9]*[hH])* *([0-9]*[mM])* *([0-9]*[sS])*")
    if len(groups) != 3:
        raise Exception('Could not parse time string: {}'.format(time_str))

    for i in range(0, 3):
        if groups[i]:
            groups[i] = int( groups[i].lower().replace('h','').replace('m', '').replace('s', '') )
        else:
            groups[i] = 0

    #calculate seconds
    seconds = (groups[0]*3600) + (groups[1]*60) + groups[2]
    return seconds

def timestr(seconds_in):
    #takes in string of execution time and turns it into a string
    exec_hrs = int(seconds_in / 3600) #how many hours did it take
    exec_mins = int((seconds_in % 3600) / 60) # the amount of seconds left outside the hours, divided by 60 to get minutes
    exec_secs = int((seconds_in % 3600) % 60) # the amount of seconds left outside the minutes

    time_str = ''
    if exec_secs > 0:
        time_str = str(exec_secs)+' secs'
    if exec_mins > 0:
        time_str = str(exec_mins)+' mins '+time_str
    if exec_hrs > 0:
        time_str = str(exec_hrs)+' hrs '+time_str

    return time_str

def get_battery_info():
    battery = psutil.sensors_battery() 
    return battery.percent, battery.power_plugged


class ScriptSleepController():
    # controller used to manage script sleeping
    # accounts for things like predictive sleep, accurate sleep near thresholds and script sleep drift
    # designed to be a Singleton Class

    def __init__(self, battery_floor, battery_ceiling, des_percent_drop=5, init_pred=10):
        self.cur_percent = None
        self.charging = None
        self.prev_percent = None
        self.sleep_period = None
        self.battery_floor = battery_floor
        self.battery_ceiling = battery_ceiling
        self.des_percent_drop = des_percent_drop
        self.init_pred = init_pred
        self.pred_drift = 0

    # To make predicted sleep time more accurate, need to account for time script spends handling battery cases
    # time.time() cannot be used since it is unix timestamp, so PC hibernation will mess up prediction
    # Instead keep track of seconds slept in script with the below functions (drift)
    # drift is added to predict sleep period to account for time since last check and is reset in percent check
    # Assumption is that other parts of script that are not sleeping take negligible time

    def log(txt):
        OUTSTREAM.log('SLEEPCONTROLLER: {}'.format(txt))

    def printlg(txt):
        OUTSTREAM.printlg('SLEEPCONTROLLER: {}'.format(txt))

    def print(txt):
        OUTSTREAM.print('SLEEPCONTROLLER: {}'.format(txt))

    def track_drift(self, secs):
        self.pred_drift += secs

    def reset_drift(self):
        self.pred_drift = 0

    def track_sleep(self, secs:int):
        # increments time sincle last slepts and calls verbose sleep
        self.track_drift(secs)
        verbose_sleep(secs=secs)

    def predict_sleep_period(self):
        # predicts the amount of time to sleep so that we check the battery every (des_percent_drop)%

        # based on process burst prediction: q_(n+1) = a*t_n + (1-a)q_n 
        # init_prediction (q_0) is first prediction for amount of seconds to change delta%
        # window is the measured amount of time in seconds between current and prev battery measurements
        # a is weighting parameter, a=1 means only base on current behaviour, a=0 means based on previous behaviour
        # cur_ct (t_n) is the amount of time it took to change delta%
        # pred_ct (q_n) is the predicted time it took to change delta% ( corresponds to q_(n-1))
        # next_pred_ct (q_(n+1)) is the predicted time to change delta% for next iteration

        a = 0.89

        cur_percent = self.cur_percent
        prev_percent = self.prev_percent
        prev_pred = self.sleep_period
        init_pred = self.init_pred
        des_percent_drop = self.des_percent_drop

        if prev_percent is None or prev_pred is None:
            ScriptSleepController.log('Initial Prediction Used, Prediction')
            return init_pred

        percent_drop_per_sec = abs(cur_percent - prev_percent) / float(prev_pred)

        if percent_drop_per_sec == 0.0:
            # no change in battery
            # double the prediction
            ScriptSleepController.log('No Change, doubled the prediction.')
            return prev_pred*2

        # calculate the actual time it would take to drop by our desired percent
        actual_drop_period = des_percent_drop / percent_drop_per_sec

        # use the round robin formulat to calculate our next prediction
        next_pred = int( a*actual_drop_period + (1-a)*prev_pred )

        return next_pred

    def get_sleep_period(self):
        cur_percent = self.cur_percent
        pred_sleep_period = self.predict_sleep_period()

        # gets the sleep period we want the program to sleep for
        # can either be the predicted period, or shorter 

        # Will be shorter if (time for battery % to go out of bounds ) < predicted period

        # First calculate the time for the battery to go out of bounds
        percent_drop_per_sec = pred_sleep_period / self.des_percent_drop

        fall_below_thresh_time = max(60, int(percent_drop_per_sec * abs( cur_percent - self.battery_floor)))
        go_above_thresh_time = max(60, int(percent_drop_per_sec * abs(self.battery_ceiling - cur_percent)))

        use_below_thresh = (fall_below_thresh_time < pred_sleep_period) and not self.charging
        use_above_thresh = (go_above_thresh_time < pred_sleep_period) and self.charging

        # ScriptSleepController.print('Above ({}) vs Predicted ({})'.format(timestr(go_above_thresh_time), timestr(pred_sleep_period)))
        # ScriptSleepController.print('Below ({}) vs Predicted ({})'.format(timestr(fall_below_thresh_time), timestr(pred_sleep_period)))

        if use_below_thresh or use_above_thresh:
            # one of these cases is true, use that as the sleep period
            ScriptSleepController.printlg('Using Pre-emptive threshold prediction')
            return fall_below_thresh_time if use_below_thresh else go_above_thresh_time


        # none of them match, just use same sleep period
        ScriptSleepController.printlg('Using standard prediction')
        return pred_sleep_period

    def sleep_till_next_check(self):
        self.prev_percent = self.cur_percent
        self.cur_percent, self.charging = get_battery_info()
        
        # does the required sleep
        if self.sleep_period is not None:
            if self.pred_drift > 0:
                ScriptSleepController.printlg(f'Added {timestr(self.pred_drift)} of drift to previous prediction')
                self.sleep_period += self.pred_drift

        self.reset_drift()

        ScriptSleepController.log(f'Previous Percent: {self.prev_percent}')
        ScriptSleepController.log(f'Curent Percent: {self.cur_percent}')
        ScriptSleepController.log(f'Charging: {self.charging}')
        ScriptSleepController.log(f'Previous Sleep Period: {0 if self.sleep_period is None else self.sleep_period}s or {timestr(self.sleep_period) if self.sleep_period is not None else 0}')

        self.sleep_period = self.get_sleep_period()

        #sleeping the sleep period
        ScriptSleepController.log(f'New Prediction: {self.sleep_period}s or {timestr(self.sleep_period)}')
        ScriptSleepController.printlg(f'Sleeping {timestr(self.sleep_period)}...')
        verbose_sleep( secs=self.sleep_period )


class ScriptStdOut():
    instance = None

    def __init__(self, logfileaddr, enablelogs, headless, printlogs):
        self.logfile = None
        self.logfileaddr = None
        self.enablelogs = None
        self.printlogs = None
        self.headless = None
        self.setConfig(logfileaddr=logfileaddr, enablelogs=enablelogs, headless=headless, printlogs=printlogs)
    
    def setConfig(self, logfileaddr=None, enablelogs=None, headless=None, printlogs=None):
        # set config after instance initialization

        # close the old file if there was any
        if self.logfile is not None:
            self.logfile.close()
            self.logfile = None

        # receive the new parameters
        # only replace if it changes the parameters
        if logfileaddr is not None: self.logfileaddr = logfileaddr
        if enablelogs is not None: self.enablelogs = enablelogs
        if printlogs is not None: self.printlogs = printlogs
        if headless is not None: self.headless = headless


        if self.enablelogs and self.logfileaddr is not None:
            self.logfile = open(self.logfileaddr, 'a')

        if self.headless:
            if self.logfile is None:
                raise Exception('Cannot be headless without log file!')
            
    def getInstance(logfileaddr=None, enablelogs=False, headless=False, printlogs=False):
        if ScriptStdOut.instance is None:
            ScriptStdOut.instance = ScriptStdOut(logfileaddr, enablelogs, headless, printlogs)

        return ScriptStdOut.instance

    def flushToFile(self):
        # flushes logfile object to file
        if self.logfile is None:
            return

        self.logfile.close()
        self.logfile = open(self.logfileaddr, 'a')


    def log(self, text, headlessprint=False, printlogs=None):

        if printlogs is None:
            printlogs = self.printlogs

        # logs it to the log file
        if not self.enablelogs:
            return

        if self.logfile is None:
            raise Exception('No log file!')

        if headlessprint:
            text = '(headless stdout): {}'.format(text)

        self.logfile.write('{}: {}\n'.format(mydt.today().strftime('%d/%m/%Y %H:%M:%S'), text.strip()))

        if (not self.headless) and printlogs:
            self.print(text)

    def print(self, text):
        # prints to the stdout
        if self.headless:
            # if headless script goes to logfile so we just handle it by calling log
            self.log(text, headlessprint=True)
        
        else:
            print(text)

    def printlg(self, text):
        # prints the text and also logs it

        # if headless, a print writes to log file, so remove duplicate call
        if (not self.headless): self.print(text)

        # if print logs is turned on, then the above print satisfies call
        # so send printlogs = false to log
        self.log(text, printlogs=(False if self.printlogs else None))




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


def get_alert_info(low=False, high=False, last=False):
    
    curbattery, _ = get_battery_info()
    descs = {
        'low': ( 'Low', 'below', 'minimum', 'not'),
        'high': ('High', 'above', 'maximum', 'still' )
    }

    desc = descs[ 'low' if low else 'high' ]

    title = '{} Battery Alert'.format(desc[0])
    if last: title = 'FINAL CALL - {}'.format(title)

    email_title = 'AJAK Auto Battery Monitor - {}'.format(title)

    body = '{}\n{}'.format(
        'Battery ({batt}%) is near or {boundarydesc} specified {limdesc} ({batterylim}%) and is {chargeverb} charging.'.format(
            batt=curbattery,
            boundarydesc=desc[1],
            limdesc=desc[2],
            batterylim= BATTERY_FLOOR if low else BATTERY_CEILING,
            chargeverb=desc[3],
        ),
        'Manual assistance is required.'
    )

    return email_title, title, body

def send_battery_alerts(low=False, high=False, email=False, sound=False, last=False):
    email_title, title, body = get_alert_info(low=low, high=high, last=last)

    # make sound
    if sound:
        OUTSTREAM.printlg('Playing sound..')
        do_beeps_threaded()

    # windows 10 notification
    OUTSTREAM.printlg('Showing Windows Notification...')
    send_notification(title, body)

    if email:
        # send the email alert
        subject = '{} - {}'.format(email_title, mydt.now().strftime('%b %d %Y %H:%M'))
        send_email_from_bot(body, subject, EMAIL_RECEIVER, [], important=(low or last))
        OUTSTREAM.printlg('Email Alert Sent!')

def handle_battery_case(high_battery, low_battery):
    _ , charging = get_battery_info()
    attempts_made = 0

    while (low_battery and not charging) or (high_battery and charging):

        if attempts_made == MAX_ATTEMPTS:
            OUTSTREAM.printlg('No More Attempts Remaining!')
            break

        # attempt to turn on the smart plug first ourselves
        OUTSTREAM.printlg('Attempting Automatic Smart Plug Control')
        try:
            SMART_PLUG_CONTROLLER.set_plug(on=low_battery, off=high_battery)
            for l in SMART_PLUG_CONTROLLER.dump_logs():
                OUTSTREAM.log(l)

        except KeyboardInterrupt:
            raise KeyboardInterrupt

        except Exception as e:
            OUTSTREAM.printlg(f'Something went wrong: {e}')

        OUTSTREAM.print('Waiting 5 seconds for verification')

        SLEEP_CONTROLLER.track_sleep(5)

        _ , charging = get_battery_info()

        if ( low_battery and charging ) or ( high_battery and not charging):
            # we have resolved the issue so we can break
            OUTSTREAM.printlg('Issue Resolved')
            break

        
        OUTSTREAM.printlg('Failed to control smart plug, manual assistance required')

        # first attempt do only windows notif (if theyre on thier computer)
        # second attempt is windows notif and sound (looking away)
        # other attempts after use windows notif, sound and email
        # before email, wait time is 120s

        msg = 'Notifying With: Windows Notification'
        wait_for = 120 if attempts_made < 2 else ALERT_PERIOD

        if attempts_made >= 1: # after first attempt use sound
            msg += ', Sound'

        if attempts_made >= 2: # after second attempt use email
            msg += ', Email'

        OUTSTREAM.printlg( msg )

        send_battery_alerts(
            low=low_battery,
            high=high_battery,
            sound=(attempts_made >= 1),
            email=(attempts_made >= 2),
            last=(attempts_made == MAX_ATTEMPTS -1 )
        )

        attempts_made += 1
        
        OUTSTREAM.printlg(f'Waiting {timestr(wait_for)} for user action...')
        SLEEP_CONTROLLER.track_sleep(wait_for)

        # get the charging info again and reloop
        _ , charging = get_battery_info()



def monitor_battery():
    itr = 0
    OUTSTREAM.log('Entering While Loop')
    
    while True:

        try:
            # loop runs forever

            # put sleep first, doing so to eliminate if statements
            if itr > 0:
                SLEEP_CONTROLLER.sleep_till_next_check()


            # get the battery percentage
            OUTSTREAM.log('Obtaining Battery Info')
            cur_percent, charging = get_battery_info()

            OUTSTREAM.printlg('Battery: {}%, Charging: {}'.format(cur_percent, 'Yes' if charging else 'No'))

            low_battery = (cur_percent <= BATTERY_FLOOR) and (not charging)
            high_battery = (cur_percent >= BATTERY_CEILING) and charging

            if not ( high_battery or low_battery ):
                # no need to alert, continue to sleep
                OUTSTREAM.printlg('No Action Required')
                itr += 1
                continue

            OUTSTREAM.printlg('{} Battery Detected'.format('Low' if low_battery else '', 'High' if high_battery else ''))
            handle_battery_case(high_battery, low_battery)
            itr += 1

        except KeyboardInterrupt:
            if HEADLESS:
                OUTSTREAM.printlg('While loop exited from keyboard interrupt')
                return
            
            else:
                try:

                    OUTSTREAM.print('\nPress Ctrl+C again in 10s to end script')
                    SLEEP_CONTROLLER.track_sleep(secs=10)
                    itr = 0
                except KeyboardInterrupt:
                    OUTSTREAM.printlg('While loop exited from keyboard interrupt')
                    return

def started_notif():
    send_notification('Headless Battery Monitor', 'Battery monitor started successfully and running in headless mode. Log file: {}'.format(os.path.split(LOG_FILE_ADDR)[1]))  

def testing():
    print('Running!')
    x = threading.Thread(target=do_beeps)
    x.start()
    print('Done!')


def main():

    global OUTSTREAM
    global BATTERY_FLOOR
    global BATTERY_CEILING
    global ALERT_PERIOD
    global MAX_ATTEMPTS
    global HEADLESS
    global SMART_PLUG_CONTROLLER
    global SLEEP_CONTROLLER

    OUTSTREAM = ScriptStdOut.getInstance(logfileaddr=LOG_FILE_ADDR, enablelogs=False, headless=False, printlogs=False)

    try:
        parser = argparse.ArgumentParser()

        parser.add_argument(
            "-plug-ip",
            required=True,
            type = str,
            metavar='<IP Address>',
            help = "The IP Address of the Kasa Smart Plug e.g. 192.168.1.1",
            default = None
        )

        parser.add_argument(
            "-home-wifi",
            required=True,
            type = str,
            metavar='<Home Wifi Name>',
            help = "The name of your home wifi network, used to determine if your laptop is at home",
            default = None
        )

        parser.add_argument(
            "-min",
            required=False,
            type = int,
            metavar='<Minimum Battery Percentage>',
            help = "Lowest battery percentage to trigger alert, default: 25",
            default = 25
        )

        parser.add_argument(
            "-max",
            required=False,
            type = int,
            metavar='<Maximum Battery Percentage>',
            help = "Highest battery percentage to trigger alert, default: 85",
            default = 85
        )

        parser.add_argument(
            "-grain",
            required=False,
            type = str,
            metavar='<Battery Check Increment>',
            help = "The percentage increment the script should check the battery at, e.g means check every 5%%",
            default = 5
        )

        parser.add_argument(
            "-alert",
            required=False,
            type = str,
            metavar='<alert_period>',
            help = "Amount of time between sending battery alerts, default: 5m",
            default = '5m'
        )

        parser.add_argument(
            "-max-attempts",
            required=False,
            type = int,
            metavar='<Alert Attempts>',
            help = "The maximum number of times an attempts made to notify you (Only done when smart plug control fails)",
            default = 20
        )

        # parser.add_argument(
        #     "-logfile",
        #     required=False,
        #     type = int,
        #     metavar='<Alert Attempts>',
        #     help = "The maximum number of times an attempts made to notify you (Only done when smart plug control fails)",
        #     default = 20
        # )


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

        ALERT_PERIOD = parse_time_str_to_seconds( options.alert )
        BATTERY_FLOOR = options.min
        BATTERY_CEILING = options.max
        MAX_ATTEMPTS = options.max_attempts
        HEADLESS = options.headless

        OUTSTREAM.setConfig(logfileaddr=LOG_FILE_ADDR, enablelogs=(not (options.testing or options.nologs)), headless=options.headless, printlogs=options.printlogs)

        if OUTSTREAM.enablelogs:
            OUTSTREAM.print('Logging To: {}\n'.format(LOG_FILE_ADDR))
            # LOG_FILE = open(LOG_FILE_ADDR, 'a')
            if OUTSTREAM.printlogs:
                OUTSTREAM.print('Printing logs is turned on!')
        else:
            OUTSTREAM.print('No logs are being made. \n')

        if options.testing:
            testing()
            return 0

        OUTSTREAM.log('Script Started')
        OUTSTREAM.log('Args: ( min={}%, max={}%, grain={}%, alert={}, attempts={})'.format(BATTERY_FLOOR, BATTERY_CEILING, options.grain, options.alert, MAX_ATTEMPTS))
        OUTSTREAM.print('Script Configuration:')
        OUTSTREAM.print(f'Battery Minimum: {BATTERY_FLOOR}%')
        OUTSTREAM.print(f'Battery Maximum: {BATTERY_CEILING}%')
        OUTSTREAM.print(f'Check Battery Every: {options.grain}%')
        OUTSTREAM.print(f'Alert Period: {options.alert}')
        OUTSTREAM.print(f'Max Alert Attempts: {MAX_ATTEMPTS}')
        OUTSTREAM.print('')

        if HEADLESS: started_notif()

        OUTSTREAM.log('Initializing Smart Plug Controller')
        SMART_PLUG_CONTROLLER = SmartPlugController( options.plug_ip, 'Ajak Smart Plug', options.home_wifi, tplink_creds=TPLINK_CLOUD_CREDS)
        OUTSTREAM.log('Initializing Sleep Controller')
        SLEEP_CONTROLLER = ScriptSleepController(BATTERY_FLOOR, BATTERY_CEILING, des_percent_drop=options.grain)

        monitor_battery()
        OUTSTREAM.log('Script Ended')

    except KeyboardInterrupt:
        OUTSTREAM.print('\nSystem Interrupt')
        return 1
    except Exception as e:
        OUTSTREAM.printlg('Script Exception: "{}"'.format(e))

        if HEADLESS:
            send_notification(
                'Headless Battery Monitor Failure',
                'Error: "{}"'.format(e)
            )
        else:
            traceback.print_exc()

    return 0


if __name__ == "__main__":
    sys.exit(main())