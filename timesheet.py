#!/usr/bin/env python2.7
from datetime import datetime, timedelta, time, date
from fdfgen import forge_fdf
from commands import getoutput
from tempfile import TemporaryFile
import argparse, os, sys, yaml

def format_date(date):
	return date.strftime('%m/%d/%y')

def format_time(time):
	return '%s:%.2d' % (time.hour, time.minute)

def parse_time(string):
	hour, minute = string.split(':')
	return time(hour=int(hour), minute=int(minute))

def hours_elapsed(start, end):
	start_dec = start.hour + start.minute / 60.0
	end_dec = end.hour + end.minute / 60.0
	return end_dec - start_dec

def generate_pdf(fields, output):
	fdf = forge_fdf('', fields.items(), [], [], [])
	with TemporaryFile() as fdf_file:
		fdf_file.write(fdf)
	message = getoutput('pdftk timesheet.pdf fill_form data.fdf output %s.pdf flatten' % (output))
	fdf_file.close()

def set_fields(start_date, end_date, first_name, last_name, employee_id, payrate, week):
	curr_date = end_date
	while(curr_date >= start_date):
		start = curr_date - timedelta(days=curr_date.weekday(), weeks=1)
		curr_date -= timedelta(weeks=2)

		fields = {
			'First Name': first_name,
			'Last Name': last_name,
			'SS': employee_id,
		}

		# populate them dates.
		for i in range(0, 14):
			num = str(i + 1)
			fields['D'+ num] = format_date(start + timedelta(days=i))

		friday = start + timedelta(days=4)
		next_friday = friday + timedelta(weeks=1)

		fields['Week Ending 1'] = format_date(friday)
		fields['Week Ending 2'] = format_date(next_friday)

		all_hours = 0

		# populate weeks
		for week_num in range(1, 3):
			total_hours = 0
			for i in range(0, 7):
				if week_num == 1:
					num = str(i + 1)
				else:
					num = str(7 + i + 1)

				if week[i]:
					start_time = parse_time(week[i][0])
					end_time = parse_time(week[i][1])

					fields['F' + num] = format_time(start_time)
					fields['T' + num] = format_time(end_time)
					
					total_hours += hours_elapsed(start_time, end_time)

			fields['Week %d Total' % (week_num)] = str(total_hours)
			fields['Sum%d' % (week_num)] = str(total_hours)
			if week_num == 1:
				fields['Hours 1'] = str(total_hours)
			else:
				fields['Hours 4'] = str(total_hours)

			all_hours += total_hours

		fields['Comments'] = 'Peer Leader work with Andrew Tjang \n%.02f/hrs X $12/hr = $%.02f' % (all_hours, all_hours * 12.0)

	return fields

def parse_yaml(config_file):
	stream = open(config_file, 'r')
	config = yaml.load(stream)
	stream.close()
	return config

def get_work_week(config):
	weekdays = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
	week = [(), (), (), (), (), (), ()]
	for event in config['schedule']:
		week[weekdays[event['day']]] = (event['start'], event['end'])
	return week

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Generate timesheets for CS111 payroll')
	parser.add_argument("date", type=str, nargs='?', help="end of pay period")
	parser.add_argument("--config", default=os.getenv("HOME") + '/payroll.yaml', help="employee config file")
	parser.add_argument("--output", help="output file")
	args = parser.parse_args()
	
	if args.date: 
		due = args.date.rsplit('/')
		end_date = datetime(day=int(due[1]), month=int(due[0]), year=int(due[2]))
	else:
		end_date = date.today()
		end_date = end_date + timedelta(days=4-end_date.weekday())
	start_date = end_date - timedelta(days=4, weeks=1)
	
	config = parse_yaml(args.config)
	week = get_work_week(config)

	fields = set_fields(start_date, end_date, config['first_name'], config['last_name'], config['employee_id'], config['payrate'], week)
	
	if args.output:
		output = args.output
	else:
		output = os.getenv("HOME") + "/" + config['last_name'] + '-' + end_date.strftime('%m-%d-%y')
	generate_pdf(fields, output)
	print "Generated %s.pdf!" % (output)