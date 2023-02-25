# Python PC Battery Monitor
The scripts in this folder are designed to monitor the battery of the computer and handle it if it reaches a certain threshold.

`battery_monitor.py` controls the Kasa smart plug when the battery reaches the floor and ceiling thresholds.

`battery_monitor.py` is what is in use at the moment and will be the focus of this README.

# Main function
`battery_monitor.py` controls a Kasa Smart Plug (see https://www.kasasmart.com/us/products/smart-plugs) that is turned on or off when the battery reaches defined thresholds. The smart plug controls power to the PC and therefore acts as a way to turn on or turn off charging to the system.

The battery percentage of the PC is checked periodically, this checking period is automatically determined based on the script configurations

If the script fails to control the plug, a Windows Notification and an email (sent to `EMAIL_RECEIVER` defined in the script) is sent to notify the user.


# Script Usage
## Pre-Configuration
Before the script can be used, you will need to have the following information
1. Your home wifi network name
2. The IP Address of your Kasa Smart Plug
3. Directory where script logs can be stored
4. Email Bot Account
5. Email to receive alerts

Use your email bot account credentials to set `EMAIL_SENDER` and `EMAIL_SENDER_PASS` in the script. Set `EMAIL_RECEIVER` to the email you want to receive the alerts to

## More Information on the Arguments
Use `--help` to get the basic information on the script arguments, this serves as an extension to that.

`alert` take time strings as arguments. For example:

| Time String Argument	| Represented Amount of Time 			|
| :---      			|    :---     							|
| `30s` 				| 30 seconds 							|
| `1m` 					| 1 minute 								|
| `3h` 					| 3 hours 								|
| `1m25s` 				| 1 minute and 25 seconds 				|
| `3h30s` 				| 3 hours and 30 seconds 				|
| `3h3m` 				| 3 hours and 3 minutes 				|
| `2h30m16s` 			| 2 hours, 30 minutes and 16 seconds 	|

## Running Script As A Process on Windows
This script is designed to be constantly running, and should be automatically run on startup of the system. To do this, in Windows follow the below steps.

1. Open Task Scheduler program 

![Task Scheduler Program](/Python-PC-Battery-Monitor/doc/task_scheduler_program_on_start.png?raw=true "Task Scheduler Program")

2. In Task Scheduler, right click `Task Scheduler Library` and click `Create Task` 

![Create A Task](/Python-PC-Battery-Monitor/doc/create_task.png?raw=true "Create a Task")

3. On the `General` tab, give the task a name and check to `Run only when the user is logged on`. 

![General Information of Battery Task](/Python-PC-Battery-Monitor/doc/battery_task_general.png?raw=true "General Information of Battery Task")

4. On the `Triggers` tab, set it to be triggered on log on of the relevant user. 

![Trigger Battery Task to be run on log on](/Python-PC-Battery-Monitor/doc/battery_task_triggers.png?raw=true "Trigger Battery Task to be run on log on")

5. On the `Actions` tab, select `Start a program`. Use the path to the python executable as the path for the program or script. In the `Add arguments` field, place the absolute path to the battery monitor script with its command line arguments e.g. `C:\Users\omnic\local\GitRepos\CodingMisc\BatteryMonitor\battery_monitor.py -min 25 -max 85` 

![Put Battery Monitor Script as Action](/Python-PC-Battery-Monitor/doc/battery_task_actions.png?raw=true "Put Battery Monitor Script as Action")

To start it as a background process you can use `pythonw.exe` rather than `python.exe`, and add the addition of the `--headless` argument.

6. On the `Settings` tab, check `Allow task to be run on demand`. This will allow you to run the task immediately. Also select `Stop the existing instance` from the drop down of the rules when task is already running. This will make sure the on demand run will override any existing instance. Finally make sure to UNCHECK `Stop the task if it runs longer than:` since the script itself can be running for several days without issue.

![Battery Task Settings](/Python-PC-Battery-Monitor/doc/battery_task_settings.png?raw=true "Battery Task Settings")

### Shortcut to run task on demand
You can create a Windows shortcut with the below target to run the battery monitor task on demand if clicked:
```
C:\Windows\System32\schtasks.exe /run /tn "BatteryMonitor"
```
*Note, `BatteryMonitor` is the name of the task, make sure to change based on the name given to the task when it was created*
