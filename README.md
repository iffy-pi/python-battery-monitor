# Python PC Battery Monitor
The script battery_monitor.py is designed to periodically check a laptop's battery and turn on/off a smart plug as appropriate. This can be used to implement automatic laptop charging by having the laptop's charger always connected to the smart plug.

This allows users to have a PC-like experience with their laptop at home, no longer having to deal with checking the battery or plugging it in. It is especially ideal for those who have a static laptop set up (such as a workbench) where the laptop is docked.

This provides a better solution than always charging the laptop, as this affects the health of the laptop's battery.

The script works with Kasa Smart Plugs (https://www.kasasmart.com/us/products/smart-plugs), and has been tested using the HS103 smart plug.

# How it works
The behaviour flow chart for the script is shown in the below diagram.

**NOTE, THIS SECTION IS STILL BEING COMPLETED**

`battery_monitor.py` controls a Kasa Smart Plug (see https://www.kasasmart.com/us/products/smart-plugs) that is turned on or off when the battery reaches defined thresholds. The smart plug controls power to the PC and therefore acts as a way to turn on or turn off charging to the system.

The battery percentage of the PC is checked periodically, this checking period is automatically determined based on the script configurations

If the script fails to control the plug, a Windows Notification and an email (sent to `EMAIL_RECEIVER` defined in the script) is sent to notify the user.

hibernate_off_plug.py checks if the plug is off and turns it off if not. This was designed to run before computer hibernation/shutdown to ensure battery does not over charge.

bm.py is a command line utility to quickly check the status of the battery monitor windows scheduled task.


# Other Included Scripts
## SmartPlugController.py
Class that handles communicating with Kasa Smart Plug.

## bm.py
This script is designed to be a command line utility to monitor, stop, start and reset the Battery Monitor Windows task running on your laptop. (Make it a command line utility by adding the actual call to the python executable in a batch file e.g. bm.cd or bm.bat)

```bash
# Stop the battery monitor task
bm.py stop
# Check the status of the task
bm.py status
# Check the generated logs
bm.py logs
```

## test_smart_plug.py
Tests sending controls to the smart plug by turning it on or off. It pulls plug information from your private config.

```bash
# Turn the plug on
test_smart_plug.py on
# Turn the plug off
test_smart_plug.py off
```
## hibernate_off_plug.py
Turns the plug off if it can. Used as a method to turn the plug off when the computer goes into hibernation.

# Script Requirements
## Required Applications
1. Python (at least 3.9)
2. TP Link or Kasa Account
2. TP Link Command Line Utility (https://apps.microsoft.com/store/detail/tplink-kasa-control-command-line/9ND8C9SJB8H6?hl=en-ca&gl=ca&rtc=1)

## Required Python Packages
The required python packages are listed in requirements.txt. They can be installed using the command:

```
pip install -r requirements.txt
```

# Script Usage
## Your Private Configuration File
The private configuration file can be used to store script settings and environment variables, otherwise they would have to be specified every time the script is ran.

The configuration file is a python file that contains one dictionary variable named `CONFIG`.

Within the `CONFIG` dictionary, there are two sub-dictionaries:
- `script` 
    - Contains information used by the script across multiple executions, such as the log file directory, account credentials etc.
    - These are required for the script to run correctly.
- `args`
    - Contains information that is used as default arguments for when the script is started.
    - If not specified, script will prompt for arguments in the command line.
    - Allows for easy modification of script settings such as Plug Information without having to change task action command.

A template of the `CONFIG` dictionary is included at the beginning of battery_monitor.py. This contains the expected keys and their values.

The configuration file should be named `config.py` and stored in a folder named `private`, created in the same directory as the battery monitor script. So for example, `python-battery-monitor\private\config.py` would contain:

```python
CONFIG = {
    'script': {
        # account credentials of the email bot, set to None if you don't have any available
        'email_bot_account_creds': ('sample_email_username@gmail.com', 'sample_email_password123'),

        # email address of the alert recipient, set to None if you don't have any avaialable
        'email_alert_recipient': 'sample_email_recipient@gmail.com',
        
        # Directory where log files are created
        'log_files_dir': 'C:\\Users\\sample_user\\Documents\\sample_logs',

        # TP Link Account credentials
        'tp_link_account_creds': ('sample_tp_link_username@gmail.com', 'sample_tp_link_password456'),
    },

    'args' : {
        # IP Address of the plug
        'plug_ip': '192.168.1.100',
        'plug_name': 'Sample Smart Plug',

        # Home Wifi Network Name
        'home_wifi': 'Sample_Wifi',
        
        # Battery minimums and maximums
        'battery_min': 20,
        'battery_max': 90,
        
        # Check battery every grain %
        'grain': 10,
        
        # How many seconds to wait between each alert
        'alert_period_secs': 600,
        
        # Maximum number of alert attempts
        'max_alert_attempts': 10
    }
}
```
For account credentials, it is recommended to use Python keyring to store and retrieve them rather than putting them in the script directly. You can refer to https://www.geeksforgeeks.org/storing-passwords-with-python-keyring/ for setting and retrieving account credentials with Keyring.

## Pre-Configuration
Before the script can be used, you will need to have the following information
- Your home wifi network name
- The IP Address of your Kasa Smart Plug
- The name of your Kasa Smart plug
- Directory where script logs can be stored
- Email Bot Account Credentials (if available)
- Email to send alerts to (if available)
- Your TP Link Account Credentials

Use this information to populate the associated fields in the `CONFIG` dictionary.

## Script Arguments
You can fill in your desired arguments in the `args` field of `CONFIG`. You can also pass them to the script directly (or to override your arguments in `CONFIG`) with the scripts argument flags. Run battery_monitor.py with the argument `--help` to get information about script arguments.

## Running the Script
You can run the script through the command line:

```
python battery_monitor.py
```

Note, that the script is designed to be constantly running which might make the console window inconvenient. If you prefer instead to run it as a background process, you can use the argument `--headless`, which ensures that the script does not print to console.

```
python battery_monitor.py --headless
```

Instructions have been included below to configure the script as a background process on Windows.

# Running Script As A Process on Windows
Follow the steps below to configure battery_monitor.py as a background process on Windows which automatically runs on computer start up.

1. Open Task Scheduler program 

    ![Task Scheduler Program](/doc/task_scheduler_program_on_start.png?raw=true "Task Scheduler Program")

2. In Task Scheduler, right click `Task Scheduler Library` and click `Create Task` 

    ![Create A Task](/doc/create_task.png?raw=true "Create a Task")

3. On the `General` tab, give the task a name and check to `Run only when the user is logged on`. 

    ![General Information of Battery Task](/doc/battery_task_general.png?raw=true "General Information of Battery Task")

4. On the `Triggers` tab, set it to be triggered on log on of the relevant user. 

    ![Trigger Battery Task to be run on log on](/doc/battery_task_triggers.png?raw=true "Trigger Battery Task to be run on log on")

5. On the `Actions` tab, select `Start a program`. Use the path to the python executable as the path for the program or script. In the `Add arguments` field, place the absolute path to the battery monitor script with its command line arguments e.g. `C:\Users\omnic\local\GitRepos\CodingMisc\BatteryMonitor\battery_monitor.py -min 25 -max 85` 

    To start it as a background (windowless) process you can use `pythonw.exe` rather than `python.exe`, and add `--headless` as an argument for the battery monitor script.

    ![Put Battery Monitor Script as Action](/doc/battery_task_actions.png?raw=true "Put Battery Monitor Script as Action")

    *Note: It is recommended to use your private config to contain most of your command line arguments, as it prevents the need to change the task when they change.*

6. On the `Settings` tab, check `Allow task to be run on demand`. This will allow you to run the task immediately. Also select `Stop the existing instance` from the drop down of the rules when task is already running. This will make sure the on demand run will override any existing instance. Finally make sure to UNCHECK `Stop the task if it runs longer than:` since the script itself can be running for several days without issue.

    ![Battery Task Settings](/doc/battery_task_settings.png?raw=true "Battery Task Settings")

## Shortcut to run task on demand
You can create a Windows shortcut with the below target to run the battery monitor task on demand if clicked:
```
C:\Windows\System32\schtasks.exe /run /tn "BatteryMonitor"
```
*Note, `BatteryMonitor` is the name of the task, make sure to change based on the name given to the task when it was created*
