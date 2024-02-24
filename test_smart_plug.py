import sys
import os
import logging


script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
if script_loc_dir not in sys.path:  sys.path.append(script_loc_dir)

from scripts.SmartPlugController import SmartPlugController
from scripts.arg_parsing import get_args_from_config_cli
from scripts.functions import get_plug_password, get_log_format

logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(get_log_format())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def main():
    config = get_args_from_config_cli()

    args = sys.argv[1:]

    if len(args) == 0 or args[0] in ('-h', '--help'):
        print("<'on' or 'off'> [--no-tplink] [--no-pykasa]")
        return 1

    plug_ip = config.plugIP
    plug_state = args[0]

    if plug_state not in [ 'on', 'off' ]:
        print('Plug state must either be "on" or "off"')
        return 1

    plug_on = (plug_state == 'on')
    use_tplinkcmd = not ( '--no-tplink' in args )
    use_pykasa = not ( '--no-pykasa' in args)

    plc= SmartPlugController(
        config.plugIP,
        config.plugName,
        config.wifi,
        tplink_creds=(config.plugAccUsername, get_plug_password(config.plugAccUsername)),
        TPLinkAvail=get_plug_password(config.plugAccUsername) is not None,
        logger=logger)

    print("Setting Kasa SmartPlug '{}' to '{}'".format(plug_ip, plug_state))

    s = None
    if use_pykasa: s = '{}, {}'.format(s, 'Python') if s is not None else 'Python'
    if use_tplinkcmd: s = '{}, {}'.format(s, 'TPLinkCmd.exe') if s is not None else 'TPLinkCmd.exe'

    print('Can use: {}'.format(s))

    plc.set_plug(on=plug_on, off=(not plug_on), use_tplink=use_tplinkcmd, use_pykasa=use_pykasa)


    return 0

if __name__ == '__main__':
    sys.exit(main())