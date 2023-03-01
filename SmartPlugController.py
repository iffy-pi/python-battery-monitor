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
    LATENCY = 1.3
    def __init__( self, plug_ip:str, plug_name:str, home_network_name:str, tplink_creds:tuple=None, logging=True, printlogs=False):
        self.plug_ip = plug_ip
        self.plug_name = plug_name
        self.home_network = home_network_name
        self.cloud_creds = tplink_creds
        self.logs = []
        self.logging = logging
        self.printlogs = printlogs
        # set the event loop policy on initialization
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    def log(self, text):
        # handles logging if present
        t = time.time()
        if self.printlogs:
            print('{}: {}'.format(t, text))
        if self.logging:
            self.logs.append('{}: {}'.format(t, text))

    # Print and log
    def printlg(self, text):
        print(text)
        self.log(text)

    def clear_logs(self):
        self.logs = []

    def dump_logs(self):
        llogs = list(self.logs)
        self.clear_logs()
        return llogs
    
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

    def on_home_network(self):
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

    def run_tplinkcmd(self, cmdargs: list):
        # cmargs is args to the tplinkcmd.exe

        # uses TPLinkCmd.exe 
        # TPLinkCmd is provided on windows store
        # https://apps.microsoft.com/store/detail/tplink-kasa-control-command-line/9ND8C9SJB8H6?hl=en-ca&gl=ca

        if self.cloud_creds is None: 
            self.log('No credentials provided')
            return

        username, password = self.cloud_creds
        if username is None or password is None:
            raise Exception('No username and password information!')
        
        output, _ = SmartPlugController.__get_process_output(['tplinkcmd.exe', '-login', '-username', username, '-password', password])

        for line in output.split('\n'):
            self.log(line.strip())

        # send the command to the plug
        output, _ = SmartPlugController.__get_process_output(['tplinkcmd.exe'] + cmdargs)

        for line in output.split('\n'):
            self.log(line.strip())
    
    def set_plug_via_cloud(self, on=False, off=False):
        self.run_tplinkcmd(['-device', self.plug_name, '-on' if on else '-off'])
        time.sleep(2)

    def start_plug_timer(self, secs, on=False, off=False):
        hours = int(secs / 3600)
        mins = int((secs % 3600) / 60)

        self.run_tplinkcmd(['-device', self.plug_name, '-timer', 'start', '-h', hours, '-m', mins, '-action', '1' if on else '0'])
        self.log('Started Timer for  {} hours and {} mins'.format(hours, mins))

    async def set_plug_via_python(self, on=False, off=False):
        plug = SmartPlug(self.plug_ip)
        if on: await plug.turn_on()
        else: await plug.turn_off()

    async def __is_plug_on_p(self):
        plug = SmartPlug(self.plug_ip)
        await plug.update()  # Request the update
        return plug.is_on
    
    def is_plug_on(self):
        return asyncio.run(self.__is_plug_on_p())

    def __plug_set(self, on, off):
        try:
            plug_on = self.is_plug_on()
            return (on and plug_on) or ( off and not plug_on)
        except SmartDeviceException:
            self.log('Plug check failed!')
            return None

    def set_plug(self, on=False, off=False, use_python=True, use_cloud=True):
        if not (on or off):
            raise Exception('No plug control was set!')
        
        self.log('Setting plug to {} state'.format('on' if on else 'off'))

        if not self.on_home_network():
            self.log('Not on home network')
            return -2

        if self.__plug_set(on, off): 
            self.log('Plug was already set')
            return 0
        
        if use_python:
            # python control first
            try:
                self.log('Setting plug via python')
                asyncio.run(self.set_plug_via_python(on=on, off=off))
                time.sleep(self.LATENCY)
            
            except SmartDeviceException as e:
                self.log(f'Python Control Failed: {e}')
        

            # check if it worked and return if it did
            if self.__plug_set(on, off): return 0

        if use_cloud:
            # otherwise try the cloud
            self.log('Setting plug via cloud')
            try:
                self.set_plug_via_cloud(on=on, off=off)
            
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except Exception as e:
                self.log(f'Cloud Control Failed: {e}')

            # check if it worked and return if it did
            # return 1 meaning it had to resort to second level
            if self.__plug_set(on, off): return 1
        
        self.log('Plug control failed')
        return -1




