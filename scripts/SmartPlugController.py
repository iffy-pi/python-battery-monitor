import subprocess
import re
import time
import asyncio
import logging
from kasa import SmartDeviceException
from kasa import SmartPlug #https://python-kasa.readthedocs.io/en/latest/index.html


class SmartPlugControllerException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class SmartPlugController:
    def __init__( self, 
                 plug_ip:str, 
                 plug_name:str, 
                 home_network_name:str, 
                 tplink_creds:tuple=None, 
                 TPLinkAvail:bool = False,
                 logger: logging.Logger = None):
        '''
        Initialize a SmartPlug Controller, takes:

        - `plug_ip` : IP Address of smart plug.
        - `plug_name` : Name of the smart plug.
        - `home_network_name` : Name of your home network.
        - `tplink_creds`: TP Link Account credentials in the form of tuple: `(username, password)`
        - `TPLinkAvail` : True if the TP Link Command Line Utility (https://apps.microsoft.com/store/detail/tplink-kasa-control-command-line/9ND8C9SJB8H6?hl=en-ca&gl=ca) is installed on the computer
        '''
        
        self.plug_ip = plug_ip
        self.plug_name = plug_name
        self.home_network = home_network_name
        self.tplink_creds = tplink_creds
        self.TPLinkAvail = TPLinkAvail
        self.logger = logger

        # set the event loop policy on initialization
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    def log(self, text: str, level: int=logging.INFO):
        if self.logger is None:
            return

        self.logger.log(level, text)
    @staticmethod
    def __get_process_output(processargs: list, error_check=True):
        child = subprocess.Popen(processargs, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = child.communicate()
        err = err.decode('utf-8')
        out = out.decode('utf-8')

        if error_check and err.strip() != '':
            raise SmartPlugControllerException(f'Process Failed: "{err}"')

        return out, err

    def on_home_network(self) -> bool:
        '''
        Returns true if the calling device (laptop) is on the home network, i.e. network with name `self.home_network`.
        '''
        if self.home_network == '':
            raise SmartPlugControllerException('No home network provided!')

        data, _ = SmartPlugController.__get_process_output(['netsh', 'WLAN', 'show', 'interfaces'])
        data_lines = data.split('\n')

        info = {
            'name':'',
            'ssid' : '',
            'state': '',
        }

        for line in data_lines:
            # regex matching for the field name and the value
            # first brackets get the field name
            # name and value separated by colon
            # second bracktes get the value
            res = re.search('(.*) : *(.*)', line.strip())

            if res is None: continue

            parsed_strs = list(res.groups())

            field_name = parsed_strs[0].strip().lower().replace(' ', '_')
            field_value = parsed_strs[1].strip()

            # populate info dictionary
            if info.get(field_name) is not None:
                info[field_name] = field_value
                if all( info[k] != '' for k in info.keys()): break

        adapter = info['name'].lower()
        network = info['ssid']
        connected = ( info['state'].lower() == 'connected')

        if adapter != 'wi-fi':
            raise SmartPlugControllerException('Unrecognized interface name: "{}", reconfigure parsing!'.format(info['name']))
        
        return ( connected and network == self.home_network )

    def run_tplinkcmd(self, cmdargs: list) -> None:
        '''
        Runs TPLInkCmd.exe with the arguments in `cmdargs`.

        First runs TPLinkCmd.exe log in command with `self.tplink_creds`, then runs TPLinkCmd with specified arguments.
        '''
        if not self.TPLinkAvail:
            self.log('TP Link Command Line Utility is not available', level=logging.WARNING)
            return

        # cmargs is args to the tplinkcmd.exe

        # uses TPLinkCmd.exe 
        # TPLinkCmd is provided on windows store
        # https://apps.microsoft.com/store/detail/tplink-kasa-control-command-line/9ND8C9SJB8H6?hl=en-ca&gl=ca

        if self.tplink_creds is None: 
            self.log('No credentials provided', level=logging.ERROR)
            return

        username, password = self.tplink_creds
        if username is None or password is None:
            raise SmartPlugControllerException('No username and password information!')
        
        output, _ = SmartPlugController.__get_process_output(['tplinkcmd.exe', '-login', '-username', username, '-password', password])

        for line in output.split('\n'):
            self.log(line.strip())

        # send the command to the plug
        output, _ = SmartPlugController.__get_process_output(['tplinkcmd.exe'] + cmdargs)

        for line in output.split('\n'):
            self.log(line.strip())
    
    def set_plug_via_tplink(self, on=False, off=False) -> None:
        '''
        Sets plug on or off using TPLinkCmd.exe
        '''
        self.run_tplinkcmd(['-device', self.plug_name, '-on' if on else '-off'])
        time.sleep(2)

    def start_plug_timer(self, secs, on=False, off=False):
        hours = int(secs / 3600)
        mins = int((secs % 3600) / 60)

        self.run_tplinkcmd([
            '-device', self.plug_name,
            '-timer', 'start', 
            '-h', hours, '-m', mins,
            '-action', '1' if on else '0'])
        self.log('Started Timer for  {} hours and {} mins'.format(hours, mins))

    async def set_plug_with_pykasa(self, on=False, off=False) -> None:
        '''
        Sets the plug to the desired on or off using the python Kasa module.
        '''
        plug = SmartPlug(self.plug_ip)
        if on: await plug.turn_on()
        else: await plug.turn_off()

    async def __is_plug_on(self) -> bool:
        plug = SmartPlug(self.plug_ip)
        await plug.update()  # Request the update
        return plug.is_on
        
    def is_plug_on(self) -> bool:
        '''
        Checks if the plug is on.
        '''
        return asyncio.run(self.__is_plug_on())
    
    def isPlugSetTo(self, on: bool = False, off: bool = False) -> bool:
        '''
        Checks if the plug was already set to the desired value i.e. if the plug is already on or off.
        Returns true if:
            
        plug is on, and `on` is true, 
        
        or plug is off and `off` is true.
        '''
        try:
            plug_on = self.is_plug_on()
            return (on and plug_on) or ( off and not plug_on)
        except SmartDeviceException:
            self.log('Plug check failed!', level=logging.ERROR)
            return None
        
    def set_plug(self, on=False, off=False, use_pykasa=True, use_tplink=True) -> int:
        '''
        Sets the smart plug on or off.

        `use_pykasa` : Allowed to use the python Kasa module

        `use_tplink` : Allowed to use TPLinkCmd.exe

        Attempts to set the plug first using the Kasa module (if allowed), if not successful, TPLinkCmd.exe is used (if allowed).

        Returns 0 if the request was successful or plug was already set, -1 if the plug could not be set, and -2 if not on the home network.
        '''
        if not (on or off):
            raise SmartPlugControllerException('No plug control was set!')
        
        self.log('Setting plug to {} state'.format('on' if on else 'off'))

        if not self.on_home_network():
            self.log('Not on home network', level=logging.ERROR)
            return -2

        if self.isPlugSetTo(on=on, off=off): 
            self.log('Plug was already set')
            return 0
        
        # only use tp link if it is available
        use_tplink = False if not self.TPLinkAvail else use_tplink
        
        if use_pykasa:
            try:
                self.log('Setting plug with Python Kasa')
                asyncio.run(self.set_plug_with_pykasa(on=on, off=off))
            except SmartDeviceException as e:
                self.log(f'Python Control Failed: {e}', level=logging.WARNING)
        
        if self.isPlugSetTo(on=on, off=off): return 0

        if use_tplink:
            self.log('Setting plug with TP Link CL Utility')
            try:
                self.set_plug_via_tplink(on=on, off=off)
            except SmartPlugControllerException as e:
                self.log(f'CL Utility Failed: {e}', level=logging.WARNING)

        if self.isPlugSetTo(on=on, off=off): return 1
        
        self.log('Plug control failed', level=logging.ERROR)
        return -1




