import sys
import os
import subprocess
import glob
import re
from enum import Enum
import argparse

BMTASKNAME= "BatteryMonitor"
LOGFILEDIR= r'C:\Users\omnic\OneDrive\Computer Collection\Battery Monitor\bm_logs'

TASKSTATES = {
	'ready'
}

class TaskStates(Enum):
	none = 0
	stopped = 1
	running = 2

	def stateToStr(state):
		# Takes a task state enum and returns a string for it=

		enumstr = {
			str(TaskStates.none) : 'Uknown',
			str(TaskStates.running) : 'Running',
			str(TaskStates.stopped) : 'Stopped'
		}

		s = enumstr.get(str(state))

		if s is not None: return s
		return enumstr.get(str(TaskStates.none))

	def strToState(statusstr):
		# takes status string returned from an schtasks query and turns it into a state
		enumstates = {
			'running': TaskStates.running,
			'ready': TaskStates.stopped
		}
		
		state = enumstates.get(statusstr.lower())
		
		if state is not None: return state
		return TaskStates.none

def bm_task(args: list, getoutput=False):
	# C:\Windows\System32\schtasks.exe /run /tn "BatteryMonitor"
	cmd = ['schtasks.exe', "/tn", BMTASKNAME]
	cmd = cmd + args

	if getoutput:
		child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out, err = child.communicate()
		return out, err
	else:
		child = subprocess.Popen(cmd)
		child.communicate()

def get_re_matched_groups(search_str, pattern):
    res = re.search(pattern, search_str)
    if res is None:
        return []
    else:
        return list(res.groups())

def get_task_state():
	child = subprocess.Popen(f'schtasks /query /tn "{BMTASKNAME}" /v /fo list | find "Status:"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = child.communicate()
	output = out.decode('utf-8')
	res = get_re_matched_groups(output, 'Status: *(.*)')[0].strip()
	return TaskStates.strToState(res)

def start_bm(getoutput=False):
	if get_task_state() == TaskStates.running:
		print('Battery Monitor Task is already running')
		return
	
	print('Starting Battery Monitor task')
	return bm_task(["/run"], getoutput=getoutput)

def stop_bm():
	if get_task_state() == TaskStates.stopped:
		print('Battery Monitor Task is already stopped')
		return
	
	print('Stopping Battery Monitor task')
	bm_task(["/end"])

def restart_bm():
	stop_bm()
	start_bm()

def bm_status():
	st = get_task_state()
	print('Status: {}'.format(TaskStates.stateToStr(st)))

	if st == TaskStates.running:
		print('')
		show_latest_log(linecnt=5)

def pause_bm():
	child = subprocess.Popen(['C:\\Python310\\pythonw.exe', r'C:\\Users\\omnic\\local\\GitRepos\\python-battery-monitor\\bmsched.py', '3'], stdout=None, stderr = None)
	print('Started!')

def latest_log():
	# get the list of files in the log directory
	list_of_files = glob.glob(f'{LOGFILEDIR}\\*.log')
	# get the c time of each file and use that as the key to order the list
	# and identify the maximum
	latest_file = max(list_of_files, key=os.path.getmtime)
	
	return os.path.join(LOGFILEDIR, latest_file)

def show_latest_log(openlog=False, linecnt=13):
	logfile = latest_log()

	if openlog:
		subprocess.Popen(['notepad.exe', logfile])
		return

	with open( logfile, 'r') as file:
		lines = file.readlines()

	filelinescnt=len(lines)
	print('Showing last {} lines of {}:\n'.format(min(linecnt, filelinescnt), os.path.split(logfile)[1]))
	for line in lines[ max(0, filelinescnt-linecnt) :]:
		print(line, end='')



def main():
	args = [a.lower() for a in sys.argv[1:]]
	argc = len(args)

	if argc < 1:
		return 0

	uniword_commands = {
		'start': start_bm,
		'stop': stop_bm,
		'restart': restart_bm,
		'status': bm_status,
	}


	if args[0] in uniword_commands.keys():
		uniword_commands[ args[0] ]()


	elif args[0] == 'logs':
		# no other args we default to truncating
		# can specify a line count or use open

		if get_task_state() != TaskStates.running:
			print('Battery Monitor Task is not runnning!')
			return 1

		if argc <= 1:
			show_latest_log()
			return 0


		if args[1] == 'open':
			show_latest_log(openlog=True)

		elif args[1] == 'name':
			print(latest_log())

		else:
			try:
				linecnt = int(args[1])
			except ValueError:
				print('Invalid value for line count!')
				return 1

			if linecnt < 0:
				print('Negative value for line count!')
				return 1

			show_latest_log(linecnt=linecnt)
	
	else:
		print(f'Unrecognized argument: "{args[0]}"')
	
	return 0

if __name__ == '__main__':
	sys.exit(main())