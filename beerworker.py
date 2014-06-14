#BeerWorker.py
import GLOBALS
import threading
import time
import wiringpi2 as wiringpi
import ConfigParser
import mysql.connector
import logging

BWLock = threading.RLock()

class BeerWorker(threading.Thread):
	id = 0
	stoprequest = threading.Event()
	controlEnabled = False
	tempSensorDir = ""
	FridgeGPIO = 0      # Cooling element GPIO pin (BCM FORMAT)
	HeaterGPIO = 0      # Heating element GPIO pin (BCM FORMAT)
	
	BWLog = 0		    # BeerWorker Log
	cnxCur = 0			# MySQL connection cursor object
	
	setPoint = 0        # setpoint
	deadband = 0        # deadband
    
    dbLogging = False   # Database logging
	
	# BeerWorker is asked to politely stop by calling 
	# BeerWorker.stoprequest.set()
	def __init__(self, id, controlenabled):
		threading.Thread.__init__(self)
		self.id = id
		self.stoprequest.clear()		
		self.controlEnabled = controlenabled
		
		# Obtain temperature sensor directory
		Config = ConfigParser.ConfigParser()
		Config.read(GLOBALS.CONFIG_FILE)
		try:
			self.FridgeGPIO = int(Config.get('GPIO','fridgepin'))
			self.HeaterGPIO = int(Config.get('GPIO','heaterpin'))
			self.tempSensorDir = Config.get('TempSensor','path')
		except ValueError:
			GLOBALS.beerlogger.error('fridgepin or heaterpin has not been set in config.ini. Please set these!')
		
		if Config.get('Database','enablelogging').lower = 'true':
			self.dbLogging = True
		
		# set up a BWLog
		self.BWLog = logging.getLogger('BeerWorker')
		self.BWLog.setLevel(logging.DEBUG)
		
		filelogging = logging.FileHandler('/home/pi/bin/beer/BeerWorker.log')
		filelogging.setLevel(logging.DEBUG)
		formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%d-%m-%Y %H:%M:%S')
		filelogging.setFormatter(formatter)
		
		consolelogging = logging.StreamHandler()
		consolelogging.setLevel(logging.DEBUG)
		formatter = logging.Formatter('(%(name)s) [%(levelname)s] %(message)s')
		consolelogging.setFormatter(formatter)
		
		# Remove any handlers already present
		self.BWLog.handlers = []
		
		# Add handlers
		self.BWLog.addHandler(filelogging)
		self.BWLog.addHandler(consolelogging)
		print self.BWLog.handlers
		
		# set up wiringpi when BeerWorker initializes
		self.BWLog.info('Initializing wiringpi...')
		wiringpi.wiringPiSetupGpio()
		
		wiringpi.pinMode(self.FridgeGPIO, 1)
		wiringpi.digitalWrite(self.FridgeGPIO, 0)		# set output to zero just in case
		self.BWLog.info('Set GPIO%d as fridge output pin', self.FridgeGPIO)
		
		wiringpi.pinMode(self.HeaterGPIO, 1)
		wiringpi.digitalWrite(self.HeaterGPIO, 0)		# set output to zero just in case
		self.BWLog.info('Set GPIO%d as heater output pin', self.HeaterGPIO)
		
		# Create database cursor object
		cnxCur = GLOBALS.cnx.cursor()
		
	def checkInit(self):
		# Check if everything has been set properly
		if self.FridgeGPIO == 0:
			self.BWLog.error('fridgepin has not been set. BeerWorker cannot start without it.')
			return False
		
		if self.HeaterGPIO == 0:
			self.BWLog.error('heaterpin has not been set. BeerWorker cannot start without it.')
			return False
		
		if self.tempSensorDir == "":
			self.BWLog.error('TempSensor path has not been set. BeerWorker cannot start without it.')
			return False
		
		if self.id < 1:
			self.BWLog.error('id has not been set correctly. id must be larger than 1.')
			return False
        
        if self.tempHigh < self.tempLow:
            self.BWLog.error('Upper temperature bound cannot be set lower than lower temperature bound! Check config.ini!')
            return False
		
		return True
		
	def GetTempInfo(self):
		Config = ConfigParser.ConfigParser()
		Config.read(GLOBALS.CONFIG_FILE)
		self.setPoint = float(Config.get('SetPoint','temperature'))
		self.deadband = float(Config.get('SetPoint','deadband'))
		
	def get_temperature(self, devicefile):
		try:
			fileobj = open(devicefile,'r')
			lines = fileobj.readlines()
			fileobj.close()
		except:
			self.BWLog.error('Could not open device file of temperature sensor')
			return None
			
		status = lines[0][-4:-1] #returns YES or NO
		
		if status=="YES":
			tempstr=lines[1]
			tempstr=tempstr[tempstr.index('=')+1:-1]
			tempvalue=float(tempstr)/1000
			return tempvalue
		else:
			self.BWLog.error('Probe read failed')
			return None
		
	def run(self):
		print(self.id)
		self.cnxCur = GLOBALS.cnx.cursor()
		if not self.checkInit():
			self.BWLog.error('This BeerWorker has been incorrectly configured and will not do anything.')
		else:
			if BWLock.acquire(blocking=0):
				if self.controlEnabled == True:
					self.BWLog.info('BeerWorker starting with control enabled!')
				else:
					self.BWLog.info('BeerWorker starting with control disabled!')
                    
				while not self.stoprequest.isSet():
					# Refresh temperatures from config file
					self.GetTempInfo()
					
					# read beer temperature
					temp_beer = self.get_temperature(self.tempSensorDir)
					
					# read fridge and heater state
					fridge_state = wiringpi.digitalRead(self.FridgeGPIO)
					heater_state = wiringpi.digitalRead(self.HeaterGPIO)
					
					# write temperature into mysql database, if database logging is enabled
                    if self.dbLogging = True:
                        if temp_beer != None:
                            try:
                                self.cnxCur.execute('INSERT INTO templog(beer_id, timestamp, temperature) VALUES(%s, %s, %s)', (self.id, time.time(), temp_beer))
                                self.cnxCur.execute('INSERT INTO fridge_power(beer_id, timestamp, power) VALUES(%s, %s, %s)', (self.id, time.time(), fridge_state))
                                self.cnxCur.execute('INSERT INTO heater_power(beer_id, timestamp, power) VALUES(%s, %s, %s)', (self.id, time.time(), heater_state))
                            except mysql.connector.Error as err:
                                self.BWLog.warning(err)
					
					if self.controlEnabled == True:
						# set upper and lower temperature limits
						upperlimit = self.setPoint + self.deadband
						lowerlimit = self.setPoint - self.deadband
						print upperlimit
						print lowerlimit
						
						# Check temperature vs. upper and lower limits
						if temp_beer > upperlimit:
							# Temperature is too HIGH, turn off heater and turn on fridge
							wiringpi.digitalWrite(self.HeaterGPIO, 0)
							wiringpi.digitalWrite(self.FridgeGPIO, 1)
						
						elif temp_beer < lowerlimit:
							# Temperature is too LOW, turn off fridge and turn on heater
							wiringpi.digitalWrite(self.FridgeGPIO, 0)
							wiringpi.digitalWrite(self.HeaterGPIO, 1)
						
						else:
							# The only other logical case is that the temperature is in the bounds, so turn off both heater and fridge
							wiringpi.digitalWrite(self.FridgeGPIO, 0)
							wiringpi.digitalWrite(self.HeaterGPIO, 0)
					
					for i in range(GLOBALS.CHECK_INTERVAL):
						time.sleep(1)
						if self.stoprequest.isSet():
							break
					
					else:
						# Control has been turned off
						wiringpi.digitalWrite(self.FridgeGPIO, 0)
						wiringpi.digitalWrite(self.HeaterGPIO, 0)
						
				# BeerWorker is ending, so clean up after ourselves
				self.BWLog.info('BeerWorker is finishing...')
				self.BWLog.info('Cleaning up GPIO pins...')
				wiringpi.digitalWrite(self.FridgeGPIO, 0)
				wiringpi.digitalWrite(self.HeaterGPIO, 0)

				wiringpi.pinMode(self.FridgeGPIO, 0)
				wiringpi.pinMode(self.HeaterGPIO, 0)
				
				self.BWLog.info('BeerWorker has finished')
				BWLock.release()
			else:
				print('Could not acquire thread lock. Maybe another worker is already running!')
			
			GLOBALS.BeerWorkerFinish.set()