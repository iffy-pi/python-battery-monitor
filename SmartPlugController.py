import subprocess
import re
import time
import asyncio
from kasa import SmartDeviceException
from kasa import SmartPlug #https://python-kasa.readthedocs.io/en/latest/index.html

class SPCSubprocessException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class SmartPlugController():
    def __init__( self, 
                 plug_ip:str, 
                 plug_name:str, 
                 home_network_name:str, 
                 tplink_creds:tuple=None, 
                 logging=True, 
                 printlogs=False):
        '''
        Initialize a SmartPlug Controller, takes:

        `plug_ip` : IP Address of smart plug.

        `plug_name` : Name of the smart plug.

        `home_network_name` : Name of your home network.

        `tplink_creds`: TP Link Account credentials in the form of tuple: `(username, password)`

        `logging` : If controller will be performing logs.

        `printlogs` : Print logs as they are generated.
        '''
        
        self.plug_ip = plug_ip
        self.plug_name = plug_name
        self.home_network = home_network_name
        self.tplink_creds = tplink_creds
        self.logs = []
        self.logging = logging
        self.printlogs = printlogs

        # set the event loop policy on initialization
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    def log(self, text):
        if not self.logging: return
        # handles logging if present
        t = time.time()
        if self.printlogs:
            print('{}: {}'.format(t, text))
        
        self.logs.append('{}: {}'.format(t, text))

    # Print and log
    def printlg(self, text):
        print(text)
        self.log(text)

    def clear_logs(self):
        self.logs = []

    def dump_logs(self):
        _logs = list(self.logs)
        self.clear_logs()
        return _logs
    
    def print_logs(self):
        for l in self.dump_logs():
            print(l)

    def __get_process_output(processargs: list, error_check=True):
        child = subprocess.Popen(processargs, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = child.communicate()
        err = err.decode('utf-8')
        out = out.decode('utf-8')

        if error_check and err.strip() != '':
            raise SPCSubprocessException(f'Process Failed: "{err}"')

        return out, err

    def on_home_network(self) -> bool:
        '''
        Returns true if the calling device (laptop) is on the home network, i.e. network with name `self.home_network`.
        '''
        if self.home_network == '':
            raise Exception('No home network provided!')

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
            raise Exception('Unrecognized interface name: "{}", reconfigure parsing!'.format(info['name']))
        
        return ( connected and network == self.home_network )

    def run_tplinkcmd(self, cmdargs: list) -> None:
        '''
        Runs TPLInkCmd.exe with the arguments in `cmdargs`.

        First runs TPLinkCmd.exe log in command with `self.tplink_creds`, then runs TPLinkCmd with specified arguments.
        '''
        # cmargs is args to the tplinkcmd.exe

        # uses TPLinkCmd.exe 
        # TPLinkCmd is provided on windows store
        # https://apps.microsoft.com/store/detail/tplink-kasa-control-command-line/9ND8C9SJB8H6?hl=en-ca&gl=ca

        if self.tplink_creds is None: 
            self.log('No credentials provided')
            return

        username, password = self.tplink_creds
        if username is None or password is None:
            raise Exception('No username and password information!')
        
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

    def __plug_set(self, on: bool, off: bool) -> bool:
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
            self.log('Plug check failed!')
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
            raise Exception('No plug control was set!')
        
        self.log('Setting plug to {} state'.format('on' if on else 'off'))

        if not self.on_home_network():
            self.log('Not on home network')
            return -2

        if self.__plug_set(on, off): 
            self.log('Plug was already set')
            return 0
        
        if use_pykasa:
            # python control first
            try:
                self.log('Setting plug via python')
                asyncio.run(self.set_plug_with_pykasa(on=on, off=off))
            except SmartDeviceException as e:
                self.log(f'Python Control Failed: {e}')
        

            # check if it worked and return if it did
            if self.__plug_set(on, off): return 0

        if use_tplink:
            # otherwise try the cloud
            self.log('Setting plug via cloud')
            try:
                self.set_plug_via_tplink(on=on, off=off)
            
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except Exception as e:
                self.log(f'Cloud Control Failed: {e}')

            # check if it worked and return if it did
            # return 1 meaning it had to resort to second level
            if self.__plug_set(on, off): return 1
        
        self.log('Plug control failed')
        return -1




