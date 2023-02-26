import sys
from time import sleep
import os

script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
if script_loc_dir not in sys.path:  sys.path.append(script_loc_dir)
from SmartPlugController import SmartPlugController


def main():
    args = sys.argv[1:]

    if len(args) < 2:
        print('Expecting arguments: <home wifi> <plug ip>')
        return 1

    home_wifi = args[0]
    plug_ip = args[1]
    
    plc = SmartPlugController(plug_ip, 'Ajak Smart Plug', home_wifi, None)

    res = plc.set_plug(off=True)
    
    if res == 0:
        print('Plug was turned off')
    
    if res == -2:
        print('Not on home network')
        sleep(1)

    return 0

if __name__ == '__main__':
    sys.exit(main())