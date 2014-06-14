# main beer program
# REQUIRES wiringpi2 LIBRARY TO WORK - install this on the Pi first
# http://raspi.tv/how-to-install-wiringpi2-for-python-on-the-raspberry-pi#install
#

import GLOBALS
import time
import confighandler
import ConfigParser
import threading
import logging
import mysql.connector as mysql
import sys
import beerworker
import thread
import socketlistener
import socket

# Define loggers
GLOBALS.beerlogger = logging.getLogger(__name__)
GLOBALS.beerlogger.setLevel(logging.DEBUG)

consolelogging = logging.StreamHandler()
consolelogging.setLevel(logging.DEBUG)
formatter = logging.Formatter('(%(name)s) [%(levelname)s] %(message)s')
consolelogging.setFormatter(formatter)

filelogging = logging.FileHandler('/home/pi/bin/beer/beer.log')
filelogging.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s (%(name)s) [%(levelname)s] %(message)s', '%d-%m-%Y %H:%M:%S')
filelogging.setFormatter(formatter)

GLOBALS.beerlogger.addHandler(consolelogging)
GLOBALS.beerlogger.addHandler(filelogging)

# Define config file
GLOBALS.CONFIG_FILE = "/home/pi/bin/beer/config.ini"
Config = ConfigParser.ConfigParser()
Config.read(GLOBALS.CONFIG_FILE)
try:
	GLOBALS.CHECK_INTERVAL = int(Config.get('Control','checkintervalseconds'))
except ValueError:
	GLOBALS.beerlogger.warning('checkintervalseconds not set in config.ini. Using default of 60 seconds instead')
	GLOBALS.CHECK_INTERVAL = 60 # seconds

SocketListener = socketlistener.SocketListener()

# Thread locks
GLOBALS.ConfigLock = threading.RLock()	# Config file lock

# Events
GLOBALS.BeerWorkerFinish = threading.Event()
GLOBALS.BeerProcessKill = threading.Event()

# Connect to mysql database
try:
	GLOBALS.cnx = mysql.connect(user=Config.get('Database','username'), password=Config.get('Database','password'), host=Config.get('Database','hostname'), database=Config.get('Database','dbname'))
	GLOBALS.cnx.autocommit = True
except mysql.Error as err:
	if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
		GLOBALS.cnx = None
		GLOBALS.beerlogger.error('Access to database denied. Check username/password settings')
	elif err.errno == errorcode.ER_BAD_DB_ERROR:
		GLOBALS.cnx = None
		GLOBALS.beerlogger.error('Database does not exist!')
	else:
		GLOBALS.cnx = None
		GLOBALS.beerlogger.error(err)
finally:
	# for now, this can't work without the mysql database
	if GLOBALS.cnx == None:
		GLOBALS.beerlogger.critical('An error occured while trying to connect to the MySQL database. Beer control cannot continue without this!')
		sys.exit()
	else:
		GLOBALS.beerlogger.info('Successfully connected to %s database', GLOBALS.cnx.database)

# THE MIGHTY GLOBALS.BeerWorker
GLOBALS.BeerWorker = beerworker.BeerWorker(0, False)

# Start socketlistener thread
SocketListener.start()
GLOBALS.beerlogger.info('Starting socket listener...')

# beer.py has no more responsibility until it is requested to stop
# Therefore wait until requested to stop
while not GLOBALS.BeerProcessKill.isSet():
	try:
		GLOBALS.BeerProcessKill.wait(1)
	except KeyboardInterrupt:
		GLOBALS.BeerProcessKill.set()
	
# If code passes this point, we must exit. First, raise the flag to terminate the GLOBALS.BeerWorker
GLOBALS.beerlogger.info('Beer process requested to terminate')
GLOBALS.beerlogger.info('Notifying BeerWorker...')
GLOBALS.BeerWorker.stoprequest.set()

# Wait until the worker has finished
if GLOBALS.BeerWorker.isAlive():
	GLOBALS.BeerWorkerFinish.wait()
	
GLOBALS.beerlogger.info('BeerWorker has finished')

# Now raise the flag to terminate the socketlistener
GLOBALS.beerlogger.info('Notifying SocketListener...')
GLOBALS.SocketListenerKill.set()

# Wait until the socketlistener is terminated. The socketlistener thread obtains a lock during its execution which is released upon termination
# We can request to acquire the lock as it will block until socketlistener releases it
tempsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tempsocket.connect(('192.168.0.4', 8888))
tempsocket.close()

SocketListener.join()
GLOBALS.beerlogger.info('SocketListener has terminated')
GLOBALS.beerlogger.info('Beer process quitting. Bye bye!')
sys.exit()

