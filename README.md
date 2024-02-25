# Python Laptop Battery Monitor
The script battery_monitor.py is designed to periodically check a laptop's battery and turn on/off a smart plug as appropriate. This can be used to implement automatic laptop charging by having the laptop's charger always connected to the smart plug.

This allows users to have a PC-like experience with their laptop at home, no longer having to deal with checking the battery or plugging it in. It is especially ideal for those who have a static laptop set up (such as a workbench) where the laptop is docked.

This provides a better solution than always charging the laptop, as this affects the health of the laptop's battery.

The script works with Kasa Smart Plugs (https://www.kasasmart.com/us/products/smart-plugs), and has been tested using the HS103 smart plug.

# Using the Battery Monitor
## Requirements
### Devices
- A TP Link Smart Plug (https://www.kasasmart.com/us/products/smart-plugs)
    - See supported smart plugs [here](https://github.com/python-kasa/python-kasa#supported-devices)
- A Windows laptop with a battery

### Applications/Services
- Python 3.10 or later
  - Install all the required packages with `python -m pip install -r requirements.txt`
  - You are free to configure a virtual environment if you wish
- TP link Command Line Utility (not fully required)
  - *TP Link Command Line Utility is a paid application ($1.29) but is not required to run the script ([Controlling The Smart Plug](#controlling-the-smart-plug)). If you do not want to get it skip this step and do NOT specify `-plug-creds` for the monitor.

### Information
The following information is required by the monitor
- The name of your home wifi/ethernet network
  - This is the network your laptop and smart plug are on
- The IP address of your smart plug
  - It is recommended to assign your smart plug a static IP address.
- A directory where the monitor can create log files
- If you have TP Link Command Line Utility:
  - Your TP Link Account credentials (see `-plug-creds` argument below)
  - The name of your Kasa Smart Plug (as seen in your account)
- If you wish to receive email alerts:
  - The email credentials to use for sending the alerts (See `-email-creds` argument below)
  - The email which receives the alerts

## Running The Monitor
You can run the battery monitor by running the script `python battery_monitor.py`, and passing it's required arguments (see below).
It is recommended to run the script as background task using Windows Task Scheduler, see [Running Monitor as a background task on windows](#running-monitor-as-a-background-task-on-windows).

## Monitor Script Arguments
The full list of arguments can be found by running `python battery_monitor.py -help` but the important ones (referenced later in this README) are mentioned below:

| Flag            | Description                                                                                                              |
|-----------------|--------------------------------------------------------------------------------------------------------------------------|
| `-config`       | A JSON config file which contains arguments to be used by the script. See the config file below.                         |
| `--headless`    | If flag is passed to script, script will run without any output (as if stdout is missing). Ideal for running windowless. |
| `-home-wifi`    | The name of the user's home network                                                                                      |
| `-plug-ip`      | The IP address of the smart plug for the laptop in the user's home network                                               |
| `-plug-name`    | The name of the smart plug for the laptop in th user's home network                                                      |
| `-min`          | The minimum battery threshold the laptop should reach                                                                    |
| `-max`          | The maximum battery threshold the laptop should reach                                                                    |
| `-grain`        | How often (in battery percentage) should the script check the battery e.g. 5 for every 5%                                |
| `-adaptivity`   | How adaptive the script is when predicting sleep periods for battery checks                                              |
| `-alert`        | The amount of time the script should wait after sending an alert                                                         |
| `-max-attempts` | The maximum number of times the script should attempt plug control (when previous attempts are not working)              |
| `-email-to`     | The email recipient for email notifications                                                                              |
| `-logdir`       | The directory where the script will store its logs in.                                                                   |
| `-email-creds`  | The username of the email used to send email notifications. Read more below.                                             |
| `-plug-creds`   | The username of the TP Link Account used to control the smart plug. Read more below.                                     |

### `-email-creds`
If you want to configure email alerts for the script, a sender account will be required. For this, the script expects the sender's account credentials to be stored as a Generic Windows Credential with the site/service name being `Battery_Monitor_Email_Credentials` (Credential Manager > Windows Credentials > Add a generic credential).

The argument provided with `-email-creds` will be the username for the credentials stored as `Battery_Monitor_Email_Credentials`.

`-email-creds` is required for email alerts (i.e. if `-email-to` is included as an argument).

_Note: Most email accounts will require an application specific password rather than your actual email account password._

### `-plug-creds`
A python library is used to control the smart plug but users have the option to use the TP Link Command Line Utility as a backup(see [Controlling The Smart Plug](#controlling-the-smart-plug)).

To use this functionality, the script must access your TP Link Account credentials (email and password). Similar to `-email-creds`, the script expects these to be stored as a generic Windows credential with the site/service name being `Battery_Monitor_TP_Link_Credentials`. The argument provided with `-plug-creds` will be the username for the generic credentials.

TP Link Command Line Utility is a paid application. If you wish to not use it, do not specify the `-plug-creds` argument.

### The config file (`-config`)
The script requires several command line arguments, which can become tedious to specify. To remediate this, the script provides the `-config` argument, which takes a path to a JSON file that contains all the command line flags the user wants for the script. This allows users to specify only the config argument for the script.

The JSON file is formatted such that:
- Each command line flag is a key which maps to its expected value
- Inclusion flags such as `--headless` are specified by just setting their value to true.
  - If the value specified for the flag is false, then the flag will be considered as unset

An exmaple JSON file is shown below:
```json
{
    "-plug-ip": "192.168.0.0",
    "-plug-name": "Smart Plug",
    "-home-wifi": "My Wifi",
    "-min": 60,
    "-max": 95,
    "-grain": 5,
    "-adaptivity": 0.90,
    "-alert": "5m",
    "-max-attempts": 20,
    "-logdir": "C:\\Users\\logs",
    "-email-to": "email@gmail.com",
    "-email-creds": "emailme@gmail.com",
    "-plug-creds": "myacc@gmail.com"
}
```

## Other Utility Scripts Provided
### bm.py
This script is designed to be a command line utility to monitor, stop, start and reset the Battery Monitor Windows task running on your laptop. (Make it a command line utility by adding the actual call to the python executable in a batch file e.g. bm.cd or bm.bat)

```bash
# Stop the battery monitor task
bm.py -task "BatteryMonitor" stop
# Check the status of the task
bm.py -task "BatteryMonitor" status
# Check the generated logs
bm.py  -task "BatteryMonitor" logs
```

### test_smart_plug.py
Tests sending controls to the smart plug by turning it on or off. Specify your config file as an argument

```bash
# Turn the plug on
test_smart_plug.py -config "..." on
# Turn the plug off
test_smart_plug.py -config "..." off
```
### hibernate_off_plug.py
Turns the plug off if it can. Used as a method to turn the plug off when the computer goes into hibernation.


# How Battery Monitor Works
The high level function of the monitor script is described in the flow chart below.

![Script Control Flow Chart](/doc/images/script_control_flow_chart.png?raw=true "Script Control Flow Chart")

The script begins by reading the battery percentage and charging status of the computer. If the battery is between the minimum and maximum thresholds, then the script sleeps till the next battery check is required. The amount of time the script sleeps is calculated from the desired battery check interval and measured battery change rate, see [Sleep Prediction for Battery Checks](#sleep-prediction-for-battery-checks).

The battery check will result in one of three conditions:
- No Action: The battery percentage is within your minimum and maximum thresholds. The script will then sleep till the next battery check is required.
- Low Battery Condition: Battery is less than or equal to the minimum threshold (`-min`) and computer is not charging.
- High Battery Condition: Battery is greater than or equal to the maximum threshold (`-max`) and computer is charging.

For low and high battery conditions, the script runs the function `handle_battery_case` to resolve the battery condition.

In `handle_battery_case`, the script attempts to control the smart plug based on the battery condition:
- If low battery, then script attempts to turn smart plug on.
- If high battery, then script attempts to turn smart plug off.

The script's attempt to control the smart plug may not be successful for a variety of reasons (see [Controlling The Smart Plug](#controlling-the-smart-plug)), therefore the battery and charging status are checked after the smart plug is controlled. If the low/high battery condition is resolved, the script exits the function and sleeps till the next battery check.

If the battery condition is not resolved at this point, manual intervention from the user is required. The script alerts the user with:
- A windows notification and 
- A sound notification after 1 attempt and
- An email notification (sent to your configured email recipient (`-email-to`)) after 2 attempts.

The script then waits for the user action. For the first two attempts, the script waits 2 minutes as the assumption is that the user could be using the laptop or could be nearby. After first two attempts, the user may not be close to the computer so the script instead waits the user configured alert period (`-alert`).

After the wait period, the script checks if the battery condition is resolved and sleeps till the next battery check if it is. Otherwise, it repeats the process of attempting plug control and then alerting the user. Each repeat of this is an attempt, and the script will continue until it reaches the configured number of maximum attempts (`-max-attempts`). After this, the script just sleeps till the next battery check.

When the script wakes up for the next battery check, it repeats the entire process again.

## Sleep Prediction for Battery Checks
Users can configure how much percent the battery should change before the next battery check is done by the script.

To ensure that the sleep period matches the desired check interval, the script uses exponential averaging to predict the sleep period for the desired battery change. The formula is shown below:

$\text{Next sleep period} = \alpha(\text{actual time for desired battery change}) + (1-\alpha)(\text{previous sleep period})$

The script calculates the actual time to get the desired battery change using linear extrapolation on the battery change between the current sleep call and the previous sleep call.

$\alpha$ ($0 < \alpha < 1$) is the adaptivity weight of the prediction. As $\alpha$ increases, the prediction becomes more responsive to recent behaviour as opposed to long term trends. The default adaptivity value is 0.90 but is also configurable by the user (`-adaptivity`).

## Controlling The Smart Plug
Smart plug control is managed by the SmartPlugController class in SmartPlugController.py. The class utilizes the [python Kasa module](https://pypi.org/project/python-kasa/0.5.1/), along with the [TP Link Command Line Utility](https://apps.microsoft.com/store/detail/tplink-kasa-control-command-line/9ND8C9SJB8H6?hl=en-ca&gl=ca&rtc=1) to turn the smart plug on/off.

When a request is made to the class to control the smart plug, it first checks if the laptop is on the user's home network. If the laptop is not on the home network, then the smart plug is unreachable and cannot be controlled, therefore the request is ended.

Otherwise, the class attempts to control the smart plug using the APIs of the python Kasa module. This is usually successful but occassionally there can be a module [system set relay state error](https://forum.universal-devices.com/topic/34492-error-when-changing-device-state/) which prevents the plug from receiving the command.

The TP Link Command Line Utility is used as a backup in the cases where the module fails. The class uses the utility to log onto the user's TP Link account and send the request to the plug through the cloud.

TP Link Command Line Utility is a paid application ($1.29). It is not required by the script to run but does make it more stable as it reduces the need for user intervention when the python module fails.

**Note: Python Kasa [v0.5.1](https://github.com/python-kasa/python-kasa/releases/tag/0.5.1) may have resolved the relay state error eliminating the need for the Utility.**

## Extra Note: Unlock Signal
When the script sleeps till the next battery checks, it reads the UNLOCK_SIGNAL file for a 1 value. If a 1 value is read, the script clears its accumulated sleep history and begins making predictions from scratch.

This allows the script to be notified of system unlocks while running. This can be achieved by creating a Windows Task in Task Scheduler to run the script `battery_monitor_unlock_signal.py`, triggered by a workstation unlock.

This was introduced to accomo,date the large increase in power usage when a user logs on after an extended period of time away. Due to the extended period of time away, the sleep periods to read the same drop in battery percentage can get long. In some instances, the increased power usage from the user returning drains the laptop battery before the monitor wakes up again, causing the laptop to die unexpectedly.

The unlock signal is configured with an "open" period of 2 hours, meaning that the unlock signal will not be triggered if another unlock happens within 2 hours of the last unlock signal received by the monitor.

# Running Monitor As A Background Task on Windows
Follow the steps below to configure battery_monitor.py as a background process on Windows which automatically runs on computer start up.

1. Open Task Scheduler program 

    ![Task Scheduler Program](/doc/images/task_scheduler_program_on_start.png?raw=true "Task Scheduler Program")

2. In Task Scheduler, right click `Task Scheduler Library` and click `Create Task` 

    ![Create A Task](/doc/images/create_task.png?raw=true "Create a Task")

3. On the `General` tab, give the task a name and check to `Run only when the user is logged on`. 

    ![General Information of Battery Task](/doc/images/battery_task_general.png?raw=true "General Information of Battery Task")

4. On the `Triggers` tab, set it to be triggered on log on of the relevant user. 

    ![Trigger Battery Task to be run on log on](/doc/images/battery_task_triggers.png?raw=true "Trigger Battery Task to be run on log on")

5. On the `Actions` tab, select `Start a program`. Use the path to the python executable as the path for the program or script. In the `Add arguments` field, place the absolute path to the battery monitor script with its command line arguments e.g. `C:\Users\user\python-battery-monitor\battery_monitor.py -min 25 -max 85` 

    To start it as a background (windowless) process you can use `pythonw.exe` rather than `python.exe`, and add `--headless` as an argument for the battery monitor script.

    ![Put Battery Monitor Script as Action](/doc/images/battery_task_actions.png?raw=true "Put Battery Monitor Script as Action")

    *Note: It is recommended to use your private config to contain most of your command line arguments, as it prevents the need to change the task when they change.*

6. On the `Settings` tab, check `Allow task to be run on demand`. This will allow you to run the task immediately. Also select `Stop the existing instance` from the drop down of the rules when task is already running. This will make sure the on demand run will override any existing instance. Finally make sure to UNCHECK `Stop the task if it runs longer than:` since the script itself can be running for several days without issue.

    ![Battery Task Settings](/doc/images/battery_task_settings.png?raw=true "Battery Task Settings")

## Shortcut to run task on demand
You can create a Windows shortcut with the below target to run the battery monitor task on demand if clicked:
```
C:\Windows\System32\schtasks.exe /run /tn "BatteryMonitor"
```
*Note, `BatteryMonitor` is the name of the task, make sure to change based on the name given to the task when it was created*
