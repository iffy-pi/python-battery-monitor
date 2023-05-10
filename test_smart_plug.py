import sys
import os

script_loc_dir = os.path.split(os.path.realpath(__file__))[0]
if script_loc_dir not in sys.path:  sys.path.append(script_loc_dir)
from SmartPlugController import SmartPlugController
from private.config import CONFIG

def main():
    args = sys.argv[1:]

    plug_ip = CONFIG['args']['plug_ip']
    plug_state = args[0]

    if plug_state not in [ 'on', 'off' ]:
        print('Plug state must either be "on" or "off"')
        return 1

    plug_on = (plug_state == 'on')
    use_tplinkcmd = not ( '--no-tplink' in args )
    use_pykasa = not ( '--no-pykasa' in args)

    plc= SmartPlugController(
        plug_ip, 
        CONFIG['args']['plug_name'], 
        CONFIG['args']['home_wifi'],
        tplink_creds=CONFIG['script']['tp_link_account_creds'],
        printlogs=True)

    print("Setting Kasa SmartPlug '{}' to '{}'".format(plug_ip, plug_state))

    s = None
    if use_pykasa: s = '{}, {}'.format(s, 'Python') if s is not None else 'Python'
    if use_tplinkcmd: s = '{}, {}'.format(s, 'TPLinkCmd.exe') if s is not None else 'TPLinkCmd.exe'

    print('Can use: {}'.format(s))

    plc.set_plug(on=plug_on, off=(not plug_on), use_tplink=use_tplinkcmd, use_pykasa=use_pykasa)


    return 0

if __name__ == '__main__':
    sys.exit(main())