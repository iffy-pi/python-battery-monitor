from scripts.bm_logging import logger, printer, flush_logs
from scripts.functions import send_notification
from scripts.TimeString import TimeString
from scripts.TimerSleep import timerSleep
from time import time_ns, sleep
import psutil

class UnlockSignalException(Exception):
    def __init__(self):
        self.message = 'Unlock signal was set to high'
        super().__init__(self.message)

UNLOCK_FILE = ''

class ScriptSleepController:
    '''
    This class is used to manage putting the script to sleep until the next battery check is required

    Accounts for sleep predictions, modifying predictions when battery is near thresholds.

    Designed to be a  Singleton Class, so is used as a gloval variable in the script.
    '''

    def __init__(self, batteryFloor: int, batteryCeiling: int, checkIntervalPercentage: int = 5, initPred: int = 10,
                 predAdaptivity: float = 0.93, headless:bool = False):
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
        self.headless = headless

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
            curTime = time_ns()
            diffSecs = (curTime - self.lastUnlockTime) / float(1E9)
            if diffSecs < 120 * 60:
                return False

        self.lastUnlockTime = time_ns()
        logger.info('Unlock Signal Was Read To Be High')
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
        # TODO: Doing override for testing purposes, remove when done
        checkUnlockSignal = False
        if checkUnlockSignal:
            logger.info(f'Script will be checking unlock signal  in UNLOCK_FILE: {UNLOCK_FILE}')
        secs = secs + (mins * 60) + (hours * 3600)

        if secs == 0:
            return

        # if we are in headless there is no console
        verbose = False if self.headless else verbose

        # flush logs before going to sleep
        flush_logs()

        if verbose:
            try:
                timerSleep(secs, checkFnc=self.checkUnlockSignal if checkUnlockSignal else None)
            except KeyboardInterrupt:
                # Timer sleep writes on the same line, so if interrupt occurs we want to push to next line
                # Do so by printing new line character to next line then raising interrupt
                if not self.headless:
                    print('')
                raise KeyboardInterrupt

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

    def trackedSleep(self, secs: int):
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
            logger.info(f'Calculated Prediction: {self.initSleepPred}s (Initial Prediction used)')
            return self.initSleepPred

        # Include tracked drift as time between calls
        prev_period = self.sleepPeriod + self.drift
        logger.info(f'Previously Predicted Sleep Period: {prev_period}s ({self.sleepPeriod}s sleep period + {self.drift}s drift)')
        self.drift = 0

        percent_drop_per_sec = abs(self.curPercent - self.prevPercent) / float(prev_period)

        if percent_drop_per_sec == 0.0:
            # double predictions until we get some percentage drop
            logger.info(f'Calculated Prediction: {prev_period*2}s (Doubled prediction since no change was detected)')
            return prev_period * 2

        # calculate the actual time it would take to drop by our desired percent
        actual_drop_period = self.checkIntervalPercentage / percent_drop_per_sec

        # use the round robin formulat to calculate our next prediction
        next_pred = int(self.predAdaptivity * actual_drop_period + (1 - self.predAdaptivity) * prev_period)

        logger.info('Calculated Prediction: %.2fs (Exponential Averaging with alpha=%.2f)' % (next_pred, self.predAdaptivity))
        logger.info(f'Exponential Averaging - Previous Prediction To Change By {self.checkIntervalPercentage}% = {TimeString.make(prev_period)}')
        logger.info(f'Exponential Averaging - Actual Percentage Change = {abs(self.curPercent - self.prevPercent)}%')
        logger.info(f'Exponential Averaging - Actual Time Required To Change By {self.checkIntervalPercentage}% = {TimeString.make(actual_drop_period)} ')

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
            logger.info('Next Sleep Period: Pre-emptive Threshold Prediction')
            return fall_below_thresh_time if use_below_thresh else go_above_thresh_time

        logger.info('Next Sleep Period: Calculated Prediction')
        return pred_sleep_period

    def sleepTillNextBatteryCheck(self):
        self.prevPercent = self.curPercent
        battery = psutil.sensors_battery()
        self.curPercent, self.charging = battery.percent, battery.power_plugged

        self.sleepPeriod = self.getNextSleepPeriod()

        printer.info(f'Sleeping {TimeString.make(self.sleepPeriod)}...')
        try:
            self.sleep(secs=self.sleepPeriod, checkUnlockSignal=True)
        except UnlockSignalException as e:
            logger.info('Recieved UnlockSignalException. Resetting Sleep History and Predictions')
            self.prevPercent = None
            self.sleepPeriod = None
            send_notification('Sleep History Reset',
                              "The script's learned sleep history has been reset to accomodate for the increase in power usage")