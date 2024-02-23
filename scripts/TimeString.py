import re

class TimeStringException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class TimeString():
    '''
    Used to make or parse "TimeStrings", which are simple strings that represent a given amount of time.
    Class provides functionality to parse and create such time strings

    Example TimeStrings are shown below:
    | Time String Argument     | Represented Amount of Time           |
    | :---                     |    :---                              |
    | `30s`                    | 30 seconds                           |
    | `1m`                     | 1 minute                             |
    | `3h`                     | 3 hours                              |
    | `1m 25s`                 | 1 minute and 25 seconds              |
    | `3h30s`                  | 3 hours and 30 seconds               |
    | `3h 3m`                  | 3 hours and 3 minutes                |
    | `2h30m16s`               | 2 hours, 30 minutes and 16 seconds   |

    Can also use full names, like mins, secs, and hours e.g. "2hrs 3mins 2secs" or "2hours 3mins 2secs"
    '''

    def parse(timestr: str) -> int:
        '''
        Parse a time string into seconds
        '''
        possible_formats = [
            "([0-9][0-9]* *hour[s]*)* *([0-9][0-9]* *min[s]*)* *([0-9][0-9]* *sec[s]*)*",
            "([0-9][0-9]* *hr[s]*)* *([0-9][0-9]* *min[s]*)* *([0-9][0-9]* *sec[s]*)*",
            "([0-9][0-9]* *h)* *([0-9][0-9]* *m)* *([0-9][0-9]* *s)*",
        ]

        timestr = timestr.lower()

        groups = None
        for frmt in possible_formats:
            res = re.search(frmt, timestr)
            if (res is not None) and (len(res.groups()) == 3) and (any(g is not None for g in res.groups())):
                groups = list(res.groups())
                break

        if groups is None:
            raise TimeStringException('Could not parse time string: {}'.format(timestr))


        for i in range(0, 3):
            if groups[i]:
                digit_str = ''
                # remove the letters from each time string
                for j in range(len(groups)):
                    if not groups[i][j].isdigit():
                        break
                    digit_str += groups[i][j]
                groups[i] = int(digit_str)
            else:
                groups[i] = 0

        #calculate seconds
        seconds = (groups[0]*3600) + (groups[1]*60) + groups[2]
        return seconds

    
    def make(seconds: int) -> str:
        '''
        Make time string from seconds input
        '''
        _hrs = int(seconds / 3600)
        _mins = int((seconds % 3600) / 60)
        _secs = int((seconds % 3600) % 60)

        timestr = ''

        info = ( (_secs, 'sec'), (_mins, 'min'), (_hrs, 'hr') )

        for pair in info:
            val, unit = pair
            if val > 0:
                timestr = '{} {}'.format('{} {}{}'.format(val, unit, 's' if val > 1 else ''), timestr)
        
        return timestr.strip()
