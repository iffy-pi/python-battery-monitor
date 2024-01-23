import os
import sys
script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
if script_loc_dir not in sys.path:
    sys.path.append(script_loc_dir)

from battery_monitor import UNLOCK_FILE

def main():
    """
    This script simply sets a value in the file LOG/DIRunlock_signal.txt , which is read every second by the battery monitor script while it sleeps
    If the unlock_signal is 1, then the battery monitor wakes up from its sleep and recalibrates itself to the current OS power usage
    This was introduced because I continued to have unexpected shutdowns because my usage drastically increased before the sleep was over
    """
    # Just write 1 to the file
    with open(UNLOCK_FILE, 'w') as file:
        file.write('1')

if __name__ == '__main__':
    sys.exit(main())
