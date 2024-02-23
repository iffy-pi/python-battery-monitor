import sys
from time import sleep
import os

script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
if script_loc_dir not in sys.path:  sys.path.append(script_loc_dir)
from scripts.SmartPlugController import SmartPlugController
from private.config import CONFIG

def main():


    plc = SmartPlugController(
        CONFIG['args']['plug_ip'], 
        CONFIG['args']['plug_name'], 
        CONFIG['args']['home_wifi'],
        )

    res = plc.set_plug(off=True)
    
    if res == 0:
        print('Plug was turned off')
    
    if res == -2:
        print('Not on home network')
        sleep(1)

    return 0

if __name__ == '__main__':
    sys.exit(main())