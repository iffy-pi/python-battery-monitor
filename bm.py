import sys
import os
import subprocess
import glob
import re

BMTASKNAME= "BatteryMonitor"
LOGFILEDIR='C:\\Users\\omnic\\OneDrive\\Documents\\Misc\\battery_monitor'

TASKSTATES = {
	'ready'
}

class TaskState():
	none = 0
	running = 1
	ready = 2
	stopped = 3

	def __init__(self):
		pass

	def set_state(self, state: int):
		self.state = state

	def set_state(self, statusstr: str):
		self.state = TaskState.state_from_status_str(statusstr)

	def state_from_status_str(statusstr):
		dix = {
			'running': TaskState.running,
			'ready': TaskState.ready,
			'stopped': TaskState.stopped
		}

		
		return dix[statusstr.lower()]

	def state_to_status_str(state):
		dix = {
			str(TaskState.none): 'Non State',
			str(TaskState.running) : 'Running',
			str(TaskState.ready) : 'Ready',
			str(TaskState.stopped) : 'Stopped'
		}

		
		return dix[str(state)]


	def __str__(self):
		return TaskState.state_to_status_str(self.state)


BMTASKSTATE = TaskState()

def bm_task(args: list):
	# C:\Windows\System32\schtasks.exe /run /tn "BatteryMonitor"
	cmd = ['schtasks.exe', "/tn", BMTASKNAME]
	cmd = cmd + args
	child = subprocess.Popen(cmd)
	child.communicate()

def get_re_matched_groups(search_str, pattern):
    res = re.search(pattern, search_str)
    if res is None:
        return []
    else:
        return list(res.groups())


def get_task_status():
	child = subprocess.Popen(f'schtasks /query /tn "{BMTASKNAME}" /v /fo list | find "Status:"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = child.communicate()
	output = out.decode('utf-8')
	res = get_re_matched_groups(output, 'Status: *(.*)')[0].strip()
	BMTASKSTATE.set_state(res)


def test():
	child = subprocess.Popen(f'schtasks /query /tn "{BMTASKNAME}" /v /fo list | find "Status:"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = child.communicate()
	output = out.decode('utf-8')
	res = get_re_matched_groups(output, 'Status: *(.*)')[0].strip()
	BMTASKSTATE.set_state(res)

def start_bm():
	print('Starting Battery Monitor task')
	bm_task(["/run"])

def stop_bm():
	print('Stopping Battery Monitor task')
	bm_task(["/end"])

def reset_bm():
	stop_bm()
	start_bm()

def bm_status():
	get_task_status()
	print('Status: {}'.format(BMTASKSTATE))

	if BMTASKSTATE.state == TaskState.running:
		print('')
		show_latest_log(linecnt=5)

def latest_log():
	# get the list of files in the log directory
	list_of_files = glob.glob(f'{LOGFILEDIR}\\*.log')
	# get the c time of each file and use that as the key to order the list
	# and identify the maximum
	latest_file = max(list_of_files, key=os.path.getctime)
	
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
	args = sys.argv[1:]
	argc = len(args)

	if argc < 1:
		return 0

	uniword_commands = {
		'start': start_bm,
		'stop': stop_bm,
		'reset': reset_bm,
		'status': bm_status,
	}


	if args[0].lower() in uniword_commands.keys():
		uniword_commands[ args[0].lower() ]()


	elif args[0] == 'logs':
		# no other args we default to truncating
		# can specify a line count or use open

		get_task_status()
		if BMTASKSTATE.state != TaskState.running:
			print('Battery Monitor Task is not runnning!')
			return 1

		if argc <= 1:
			show_latest_log()
			return 0


		if args[1] == 'open':
			show_latest_log(openlog=True)

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
	
	return 0

if __name__ == '__main__':
	sys.exit(main())