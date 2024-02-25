import os
import sys
import traceback
from datetime import datetime as mydt

script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
if script_loc_dir not in sys.path:
    sys.path.append(script_loc_dir)

from scripts.bm_logging import console, logger, printer
from scripts.functions import send_notification, get_battery_info, do_beeps_threaded
from scripts.ScriptSleepController import ScriptSleepController
from scripts.SmartPlugController import *
from scripts.EmailBot import EmailBot
from scripts.TimeString import TimeString



class EmailNotifier:
    def __init__(self, senderCreds: tuple[str, str], recipient):
        self.recipient = recipient
        self.bot = EmailBot('smtp.gmail.com', senderCreds[0], senderCreds[1])

    def sendEmail(self, subject, body, important=False):
        self.bot.sendEmail(subject, body, self.recipient, important=important)



class BatteryMonitor:
    def __init__(self, batteryFloor: int, batteryCeiling: int, checkGrain: int, adaptivity: float, alertPeriodSecs: int, maxAttempts: int, plug: SmartPlugController, emailer: EmailNotifier, headless:bool = False):
        self.batteryMin = batteryFloor
        self.batteryMax = batteryCeiling
        self.grain = checkGrain
        self.alertPeriod = alertPeriodSecs
        self.maxAttempts = maxAttempts
        self.headless = headless
        self.plug = plug
        self.emailer = emailer

        self.sleepController = ScriptSleepController(
            self.batteryMin,
            self.batteryMax,
            checkIntervalPercentage=self.grain,
            headless=self.headless,
            predAdaptivity=adaptivity)

    def monitorBattery(self):
        iters = 0
        while True:
            try:
                # put sleep first, doing so to eliminate if statements
                if iters > 0:
                    self.sleepController.sleepTillNextBatteryCheck()
                cur_percent, charging = get_battery_info()

                printer.info('Battery Check: {}%, {}'.format(cur_percent, 'Charging' if charging else 'Not Charging'))

                low_battery = (cur_percent <= self.batteryMin) and (not charging)
                high_battery = (cur_percent >= self.batteryMax) and charging

                if not (high_battery or low_battery):
                    printer.info('No Action Required')
                    iters += 1
                    continue

                printer.info('{} Battery Detected'.format('Low' if low_battery else 'High'))
                self.handleBatteryCase(high_battery, low_battery)
                iters += 1
            except KeyboardInterrupt:
                if self.headless:
                    printer.info('Exiting due to keyboard interrupt')
                    return
                else:
                    try:
                        console.info('Press Ctrl+C again in 10s to end script')
                        self.sleepController.trackedSleep(secs=10)
                        iters = 0
                    except KeyboardInterrupt:
                        printer.info('Exiting due to keyboard interrupt')
                        return

    def handleBatteryCase(self, high_battery, low_battery):
        _, charging = get_battery_info()
        attempts_made = 0

        while (low_battery and not charging) or (high_battery and charging):
            if attempts_made == self.maxAttempts:
                printer.warn('Max alert attempts reached')
                break

            printer.info('Attempting Automatic Smart Plug Control')
            try:
                self.plug.set_plug(on=low_battery, off=high_battery)
            except SmartPlugControllerException as e:
                printer.error(f'Plug Control Error: {e}')
                logger.error(traceback.print_exc())

            console.info('Waiting 5 seconds for verification')
            self.sleepController.trackedSleep(5)

            _, charging = get_battery_info()
            if (low_battery and charging) or (high_battery and not charging):
                printer.info('Battery case has been handled')
                break

            printer.info('Failed to control smart plug, manual assistance required')

            self.sendBatteryAlerts(
                isLow=low_battery,
                sound=(attempts_made >= 1),
                email=(attempts_made >= 2),
                last=(attempts_made == self.maxAttempts - 1)
            )

            wait_for = 120 if attempts_made < 2 else self.alertPeriod
            printer.info(f'Waiting {TimeString.make(wait_for)} for user action...')
            self.sleepController.trackedSleep(wait_for)

            attempts_made += 1

            _, charging = get_battery_info()

    def sendBatteryAlerts(self, isLow, email=False, sound=False, last=False):
        '''
        Sends alerts about battery conditions. If `isLow` is true, it will be low battery conditions,
        otherwise will be high battery conditions.

        If `email` is true, an email alert will be sent (if credentials are available).

        If `sound` is true, a buzzer sound will be made.

        `last` is used to indicate that this is the last battery alert.
        '''
        email_title, title, body = self.getAlert(isLow, last)

        if sound:
            printer.info('Playing sound..')
            do_beeps_threaded()

        printer.info('Showing Windows Notification...')
        send_notification(title, body)

        if email and self.emailer is not None:
            printer.info('Sending Email...')
            subject = '{} - {}'.format(email_title, mydt.now().strftime('%b %d %Y %H:%M'))
            self.emailer.sendEmail(subject, body, important=(isLow or last))
            printer.info('Email Alert Sent!')

    def getAlert(self, isLow, last):
        curbattery, _ = get_battery_info()
        descs = {
            'low': ('Low', 'below', 'minimum', 'not'),
            'high': ('High', 'above', 'maximum', 'still')
        }

        desc = descs['low' if isLow else 'high']

        title = '{} Battery Alert'.format(desc[0])
        if last: title = 'FINAL CALL - {}'.format(title)

        email_title = 'Laptop Auto Battery Monitor - {}'.format(title)

        body = '{}\n{}'.format(
            'Battery ({batt}%) is near or {boundarydesc} specified {limdesc} ({batterylim}%) and is {chargeverb} charging.'.format(
                batt=curbattery,
                boundarydesc=desc[1],
                limdesc=desc[2],
                batterylim=self.batteryMin if isLow else self.batteryMax,
                chargeverb=desc[3],
            ),
            'Manual assistance is required.'
        )

        return email_title, title, body