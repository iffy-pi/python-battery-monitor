import logging
import os
import threading
import typing

import keyring
from winsound import Beep as beep

import psutil
from winotify import Notification

script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
WIN_NOTIF_ICON = os.path.realpath(os.path.join(script_loc_dir, '..', 'roboticon.png'))
PLUG_CREDENTIAL_STORE = 'Battery_Monitor_TP_Link_Credentials'
EMAIL_CREDENTIAL_STORE = 'Battery_Monitor_Email_Credentials'


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

def get_plug_password(plug_username) -> typing.Union[str, None]:
    return keyring.get_password(PLUG_CREDENTIAL_STORE, plug_username)

def get_emailer_password(email_username) -> typing.Union[str, None]:
    return keyring.get_password(EMAIL_CREDENTIAL_STORE, email_username)


def get_log_format_str() -> str:
    return '%(filename)-25s [%(lineno)4d] %(asctime)s  %(levelname)-9s %(message)s'

def get_console_log_format_str() -> str:
    st = get_log_format_str()
    return st.replace('%(levelname)-9s', 'CONSOLE  ')

def get_log_format():
    return logging.Formatter(get_log_format_str(),
                      datefmt='%Y-%m-%d %H:%M:%S')

def get_console_log_format():
    return logging.Formatter(get_console_log_format_str(),
                             datefmt='%Y-%m-%d %H:%M:%S')

def get_log_stdout_format():
    # Formats logs so that they show up as yellow when printed to stdout
    set_console_yellow = "\033[0;33m"
    set_console_default = "\033[0m"
    return logging.Formatter(set_console_yellow + get_log_format_str() + set_console_default,
                             datefmt='%Y-%m-%d %H:%M:%S')

