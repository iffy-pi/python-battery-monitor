import sys
from time import sleep

def timerSleep(secs: int, checkFnc=None) -> None:
        '''
        Puts process to sleep for the specified seconds.

        Also maintains a time remaining countdown on the console.
        '''

        # [ hours, mins, secs ]
        times = [0, 0, 0]
        timeStrs = ['', '', '']

        def formatSecs(secs):
            '''
            Returns the given number of secs in the format: <hours> : <minutes> : <seconds>
            '''
            times[0] = int(secs / 3600)
            times[1] = int((secs % 3600) / 60)
            times[2] = int((secs % 3600) % 60)
            
            for i, t in enumerate(times):
                timeStrs[i] = f'0{t}' if t < 10 else f'{t}'
            
            return ' : '.join(timeStrs)

        max_width = len(formatSecs(secs))
        msg_format = "Sleeping... " + "{:<" + str(max_width) + "s}"
        msg_len = len(msg_format.format('a'))

        # writes the time stamp on the same line every second to simulate countdown
        for remaining in range(secs, 0, -1):
            sys.stdout.write("\r" + msg_format.format(formatSecs(remaining)))
            sys.stdout.flush()
            sleep(1)
            # Run our check function if any
            if checkFnc is not None:
                checkFnc()

        # overwrite timestamp with Done when finished sleeping
        finish_msg_format = "{:<" + str(msg_len) + "s}"
        finish_msg = finish_msg_format.format('Done!')
        sys.stdout.write("\r{}\n".format(finish_msg))
