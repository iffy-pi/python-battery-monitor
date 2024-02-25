import sys
from time import sleep
import os
import logging

script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
if script_loc_dir not in sys.path:  sys.path.append(script_loc_dir)
from scripts.SmartPlugController import SmartPlugController
from scripts.arg_parsing import get_args_from_config_in_sysargs
from scripts.functions import get_plug_password

def main():
    config = get_args_from_config_in_sysargs()
    plc = SmartPlugController(
        config.plugIP,
        config.plugName,
        config.wifi,
        tplink_creds=(config.plugAccUsername, get_plug_password(config.plugAccUsername)),
        TPLinkAvail=get_plug_password(config.plugAccUsername) is not None,
        logger=None)

    res = plc.set_plug(off=True)
    
    if res == 0:
        print('Plug was turned off')
    
    if res == -2:
        print('Not on home network')
        sleep(1)

    return 0

if __name__ == '__main__':
    sys.exit(main())