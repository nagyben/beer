# Config file handler

import ConfigParser
import mysql.connector
import GLOBALS

Config = ConfigParser.ConfigParser()

def write_new_config(path):
	if path == "":
		print 'Path cannot be empty'
	else:
		cfgfile = open(path,'w')
		
		# Setpoints. Used by main program to determine temperature constraints
		Config.add_section('SetPoint')
		Config.set('SetPoint','temperature','21.0')
		Config.set('SetPoint','deadband','1.0')
		
		# GPIO pins in use
		Config.add_section('GPIO')
		Config.set('GPIO','fridgepin','')
		Config.set('GPIO','heaterpin','')
		
		# Add temperature sensors
		Config.add_section('TempSensor')
		Config.set('TempSensor','path','/sys/devices/w1/bus/devices/28-00000XXXXXXX/w1_slave')
		
		# Controller settings
		Config.add_section('Control')
		Config.set('Control','checkintervalseconds','60')
		Config.set('Control','enabled','true')
        
        # Database settings
		Config.add_section('Database')
		Config.set('Database','EnableLogging','False')
		Config.set('Database','hostname','localhost')
		Config.set('Database','username','username')
		Config.set('Database','password','password')
		Config.set('Database','dbname','dbname')
		
		Config.write(cfgfile)
		cfgfile.close()
		
def settemperature(path, temp):
	# update in local control variable
	float(temp)	
	Config.read(path)
	
	# obtain file lock so no other thread can modify
	GLOBALS.ConfigLock.acquire()
	
	cfgfile = open(path, 'w')
	Config.set('SetPoint','temperature',temp)
	Config.write(cfgfile)
	cfgfile.close()
	
	# release file lock
	GLOBALS.ConfigLock.release()

def setdeadband(path, temp):
	float(temp)	
	Config.read(path)
	
	# obtain file lock so no other thread can modify
	GLOBALS.ConfigLock.acquire()
	
	cfgfile = open(path, 'w')
	Config.set('SetPoint','deadband',temp)
	Config.write(cfgfile)
	cfgfile.close()
	
	# release file lock
	GLOBALS.ConfigLock.release()
	
if __name__ == "__main__":
	print 'Writing new config file...'
	write_new_config("config.ini")
	print 'Write successful.'