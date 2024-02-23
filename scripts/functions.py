import os
import threading
from datetime import datetime
from time import time

from winsound import Beep as beep

import psutil
from winotify import Notification

script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
WIN_NOTIF_ICON = os.path.realpath(os.path.join(script_loc_dir, '..', 'roboticon.png'))

def send_notification(title, body):
    toast = Notification('Battery Monitor Bot', title, msg=body, icon=WIN_NOTIF_ICON)
    toast.show()

def error_notification(errorObj, logFilePath):
    title = 'Headless Battery Monitor Failure'
    body = str(errorObj)
    logFilePath = os.path.abspath(logFilePath)
    path = "file:///{}".format(logFilePath.replace("\\", "/"))

    toast = Notification("Battery Monitor Bot", title, msg=body, icon=WIN_NOTIF_ICON)
    toast.add_actions(label="Open log file", launch=path)
    toast.show()

def new_log_file(logdir):
    return os.path.join(logdir,
                 'status_{}_{}.log'.format(
                     datetime.today().strftime('%H%M_%d_%m_%Y'),
                     int(time())
                 ))

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
