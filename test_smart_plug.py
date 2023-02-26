import sys
import os

script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
if script_loc_dir not in sys.path:  sys.path.append(script_loc_dir)
from SmartPlugController import SmartPlugController

def main():
    args = sys.argv[1:]

    if len(args) < 2:
        print('Expecting arguments: <plug ip address> <plug state>')
        return 1

    plug_ip = args[0]

    plug_state = args[1]

    if plug_state not in [ 'on', 'off' ]:
        print('Plug state must either be "on" or "off"')
        return 1
    
    plc = SmartPlugController(plug_ip, 'Ajak Smart Plug', 'JIR', None, printlogs=True)

    print("Setting Kasa SmartPlug '{}' to '{}'".format(plug_ip, plug_state))
    plc.set_plug(on=(plug_state == 'on'), off=(plug_state == 'off'), use_cloud=False)
    return 0

if __name__ == '__main__':
    sys.exit(main())