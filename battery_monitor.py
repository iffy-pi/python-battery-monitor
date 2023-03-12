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
LOG_FILE = None
ENABLE_LOGS = False
PRINT_LOGS = False

def send_email_from_bot(text, subject, mainRecipient, recipients, files=[], important=False, content="text", verbose=False):
    if not isinstance(recipients, list):
        raise Exception("{0} error: {1}".format(__file__, "recipients must be a list"))

    if mainRecipient not in recipients: recipients.insert(0, mainRecipient)

    # get the bot credentials
    sender = EMAIL_SENDER
    sender_pass = EMAIL_SENDER_PASS

    server  = 'smtp.gmail.com'
    
    if verbose: script_print('Configuring Email Headers')
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = mainRecipient
    msg['Cc'] = ( ";".join(recipients) ).replace("\n\r ", "")
    if important:
        msg['X-Priority'] = "1"
        msg['X-MSMail-Priority'] = "High"


    if verbose: script_print('Configuring Email Content')
    if content == "text":
        msg.attach( MIMEText(text) )
    else:
        msg.attach( MIMEText(text, content) )
    
    for filename in files:
        if verbose: script_print("Attaching file ({0})".format(filename))
        with open(filename, "rb") as file:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload( file.read() )
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="{0}"'.format(os.path.basename(filename)))
            msg.attach(part)

    if verbose: script_print(f'Connecting to SMTP server: {server}...')
    
    # connect to gmail smpt server with this port
    session = smtplib.SMTP(server, 587)#587

    #enable security
    session.starttls()

    #log in with the credentials of the bot
    session.login(sender, sender_pass)

    if verbose: lprint('Sending Email...')

    session.sendmail(sender, recipients, msg.as_string())
    
    if verbose: script_print('Sent')
    session.quit()

def log(msg, verbose=False):
    global LOG_FILE
    if verbose or PRINT_LOGS:
        script_print(msg, islogged=True)

    if ENABLE_LOGS:
        LOG_FILE.write('{}: {}\n'.format(mydt.today().strftime('%d/%m/%Y %H:%M:%S'), msg))

def lprint(text):
    # prints information and also logs it as well
    log(text, verbose=True)

def save_logs_to_file():
    # offload logs and prints from stdout to file
    global LOG_FILE
    LOG_FILE.close()
    LOG_FILE = open(LOG_FILE_ADDR, 'a')

    if HEADLESS:
        # if headless log file is stdout
        sys.stdout = LOG_FILE


def script_print( text, islogged=False):
    # handles if we need to do a log file
    if HEADLESS:
        # if we are headless we are writing to log file
        # need proper dating 
        if not islogged:
            # if logged, it is alredy in the log file
            print('{} (headless console): {}\n'.format(mydt.today().strftime('%d/%m/%Y %H:%M:%S'), text))
    
    else:
        # just print text
        print(text)

def verbose_sleep(secs=None, mins=None, hours=None):

    if not secs:
        secs = 0

    if mins: secs += mins*60

    if hours: secs += hours*3600

    save_logs_to_file()

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


def do_beeps():
    # use winsound to generate beeps
    for _ in range(3):
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
        lprint('Playing sound..')
        do_beeps_threaded()

    # windows 10 notification
    lprint('Showing Windows Notification...')
    send_notification(title, body)

    if email:
        # send the email alert
        subject = '{} - {}'.format(email_title, mydt.now().strftime('%b %d %Y %H:%M'))
        send_email_from_bot(body, subject, EMAIL_RECEIVER, [], important=(low or last))
        lprint('Email Alert Sent!')

def handle_battery_case(high_battery, low_battery):
    local_notif_sent = False
    _ , charging = get_battery_info()
    attempts_left = MAX_ATTEMPTS
    attempts_made = 0

    while (low_battery and not charging) or (high_battery and charging):

        if attempts_made == MAX_ATTEMPTS:
            lprint('No More Attempts Remaining!')
            break

        # attempt to turn on the smart plug first ourselves
        lprint('Attempting Automatic Smart Plug Control')
        try:
            SMART_PLUG_CONTROLLER.set_plug(on=low_battery, off=high_battery)
            for l in SMART_PLUG_CONTROLLER.dump_logs():
                log(l)

        except KeyboardInterrupt:
            raise KeyboardInterrupt

        except Exception as e:
            lprint(f'Something went wrong: {e}')

        script_print('Waiting 5 seconds for verification')
        verbose_sleep(5)
        _ , charging = get_battery_info()

        if ( low_battery and charging ) or ( high_battery and not charging):
            # we have resolved the issue so we can break
            lprint('Issue Resolved')
            break

        
        lprint('Failed to control smart plug, manual assistance required')

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

        lprint( msg )

        send_battery_alerts(
            low=low_battery,
            high=high_battery,
            sound=(attempts_made >= 1),
            email=(attempts_made >= 2),
            last=(attempts_made == MAX_ATTEMPTS -1 )
        )

        attempts_made += 1
        
        lprint(f'Waiting {timestr(wait_for)} for user action...')
        verbose_sleep(secs=wait_for)

        # get the charging info again and reloop
        _ , charging = get_battery_info()

def predict_sleep_period(current, prev, window, delta=5, init_prediction=10):
    # based on process burst prediction: q_(n+1) = a*t_n + (1-a)q_n 
    # init_prediction (q_0) is first prediction for amount of seconds to change delta%
    # window is the measured amount of time in seconds between current and prev battery measurements
    # a is weighting parameter, a=1 means only base on current behaviour, a=0 means based on previous behaviour
    # cur_ct (t_n) is the amount of time it took to change delta%
    # pred_ct (q_n) is the predicted time it took to change delta% ( corresponds to q_(n-1))
    # next_pred_ct (q_(n+1)) is the predicted time to change delta% for next iteration

    a = 0.89

    if prev is None or window is None:
        log(f'Initial Prediction Used, Prediction: {timestr(init_prediction)}')
        return init_prediction

    # how much percent changed per second, assuming linear
    change_rate = abs(current-prev)/float(window)

    if change_rate == 0.0:
        # if no change in battery
        # just add like 5 mins to predicted time
        log(f'No Battery Change, Prediction: {timestr(window*2)}')
        return window*2

    # calculate how much time it takes to change by percent
    cur_ct = delta / change_rate

    # window will be what we predicted before
    pred_ct = float(window)

    next_pred_ct = a*cur_ct + (1-a)*pred_ct

    log(f'Applied Estimation, Prediction: {timestr(int(next_pred_ct))}')

    return int(next_pred_ct)

def get_battery_cases(cur_percent, charging, pred_sleep_period):
    # returns if we are in a low battery case and or high battery case

    # handle standard cases
    below_thresh = cur_percent <= BATTERY_FLOOR
    above_thresh = cur_percent >= BATTERY_CEILING

    if below_thresh or above_thresh:
        return (below_thresh and not charging), (above_thresh and charging)


    # if we go out of threshold bounds during sleep, want to handle it preemptively
    # that would happen if thresh_drop_period < sleep_period
    period_per_percent = pred_sleep_period / GRAIN

    # amount of time it would take to reach threshold
    below_thresh_time = int(period_per_percent * ( cur_percent - BATTERY_FLOOR))
    above_thresh_time = int(period_per_percent * (BATTERY_CEILING - cur_percent))


    below_thresh = below_thresh_time < pred_sleep_period
    above_thresh = above_thresh_time < pred_sleep_period

    if below_thresh or above_thresh:
        lprint('Pre-emptive threshold prediction: time to reach {} ({}) is less than next predicted sleep period ({})'.format(
            'battery floor' if below_thresh else 'battery ceiling',
            timestr(below_thresh_time) if below_thresh else timestr(above_thresh_time),
            timestr(pred_sleep_period)
            ))

    return ( below_thresh and not charging), (above_thresh and charging)


def monitor_battery():
    cur_percent = None
    prev_percent = None
    sleep_period = None
    itr = 0

    log('Initializing Smart Plug Controller')
    global SMART_PLUG_CONTROLLER
    SMART_PLUG_CONTROLLER = SmartPlugController( SMART_PLUG_IP_ADDRESS, 'Ajak Smart Plug', HOME_WIFI_NAME, tplink_creds=TPLINK_CLOUD_CREDS)

    if HEADLESS: started_notif()

    log('Entering While Loop')
    
    while True:

        try:
            # loop runs forever

            # put sleep first, doing so to eliminate if statements
            if itr > 0:
                # predict the next sleep period
                # window of checking is always the sleep period
                # initial prediction is initial sleep cycle set by user
                sleep_period = predict_sleep_period(cur_percent, prev_percent, sleep_period, delta=GRAIN)
                #sleeping the sleep period
                lprint(f'Sleeping {timestr(sleep_period)}...')
                verbose_sleep( secs=sleep_period )

            # get the battery percentage
            log('Obtaining Battery Info')
            percent, charging = get_battery_info()

            # update our previous and current values
            prev_percent = cur_percent
            cur_percent = percent

            lprint('Battery: {}%, Charging: {}'.format(percent, 'Yes' if charging else 'No'))

            low_battery , high_battery = get_battery_cases(cur_percent, charging, predict_sleep_period(cur_percent, prev_percent, sleep_period, delta=GRAIN))

            if not ( high_battery or low_battery ):
                # no need to alert, continue to sleep
                lprint('No Action Required')
                itr += 1
                continue

            lprint('{} Battery Detected'.format('Low' if low_battery else '', 'High' if high_battery else ''))
            handle_battery_case(high_battery, low_battery)
            itr += 1

        except KeyboardInterrupt:
            if HEADLESS:
                lprint('While loop exited from keyboard interrupt')
                return
            
            else:
                try:

                    print('\nPress Ctrl+C again in 10s to end script')
                    verbose_sleep(secs=10)
                    itr = 0
                except KeyboardInterrupt:
                    lprint('While loop exited from keyboard interrupt')
                    return

def started_notif():
    send_notification('Headless Battery Monitor', 'Battery monitor started successfully and running in headless mode.')  

def testing():
    print('Running!')
    x = threading.Thread(target=do_beeps)
    x.start()
    print('Done!')


def main():

    try:

        global BATTERY_FLOOR
        global BATTERY_CEILING
        global ALERT_PERIOD
        global GRAIN
        global SMART_PLUG_IP_ADDRESS
        global HOME_WIFI_NAME
        global MAX_ATTEMPTS
        global ENABLE_LOGS 
        global PRINT_LOGS
        global LOG_FILE
        global HEADLESS

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
            '--no-logs',
            '--no-logs',
            action='store_true',
            help='Disable logs'
        )

        parser.add_argument(
            '--log-verbose',
            '--log-verbose',
            action='store_true',
            help='script_print all log messages to the console'
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
        GRAIN = options.grain
        HOME_WIFI_NAME = options.home_wifi
        SMART_PLUG_IP_ADDRESS = options.plug_ip
        MAX_ATTEMPTS = options.max_attempts
        ENABLE_LOGS = not (options.testing or options.no_logs)
        PRINT_LOGS = options.log_verbose
        HEADLESS = options.headless

        if ENABLE_LOGS:
            script_print('Logging To: {}\n'.format(LOG_FILE_ADDR))
            LOG_FILE = open(LOG_FILE_ADDR, 'a')

        if options.testing:
            testing()
            return 0

        if options.headless:
            sys.stdout = LOG_FILE

        log('Script Started')
        log('Args: ( min={}%, max={}%, grain={}%, alert={}, attempts={})'.format(BATTERY_FLOOR, BATTERY_CEILING, GRAIN, options.alert, MAX_ATTEMPTS))
        script_print('Script Configuration:')
        script_print(f'Battery Minimum: {BATTERY_FLOOR}%')
        script_print(f'Battery Maximum: {BATTERY_CEILING}%')
        script_print(f'Check Battery Every: {GRAIN}%')
        script_print(f'Alert Period: {options.alert}')
        script_print(f'Max Alert Attempts: {MAX_ATTEMPTS}')
        script_print('')
        monitor_battery()
        log('Script Ended')

    except KeyboardInterrupt:
        script_print('\nSystem Interrupt')
        return 1
    except Exception as e:
        lprint('Script Exception: "{}"'.format(e))

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