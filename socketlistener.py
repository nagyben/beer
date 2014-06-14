import GLOBALS
import socket
import sys
import thread
import logging
import time
import threading
import select

GLOBALS.SocketListenerKill = threading.Event()
GLOBALS.SocketListenerLock = threading.RLock()
GLOBALS.cLogger = logging.getLogger(__name__)


import connectionhandler

class SocketListener(threading.Thread):

	def run(self):
		# define constants 

		HOST = ''   		# Symbolic name meaning all available interfaces
		PORT = 8888 		# Arbitrary non-privileged port
		CONNECTIONS = 5		# Maximum number of simultaneous connections

		#define logging
		GLOBALS.cLogger.setLevel(logging.DEBUG)
		
		consolelogging = logging.StreamHandler()
		consolelogging.setLevel(logging.DEBUG)
		formatter = logging.Formatter('(%(name)s) [%(levelname)s] %(message)s')
		consolelogging.setFormatter(formatter)

		filelogging = logging.FileHandler('/home/pi/bin/beer/connections.log')
		filelogging.setLevel(logging.DEBUG)
		formatter = logging.Formatter('%(asctime)s (%(name)s) [%(levelname)s] %(message)s', '%d-%m-%Y %H:%M:%S')
		filelogging.setFormatter(formatter)
		
		GLOBALS.cLogger.addHandler(consolelogging)
		GLOBALS.cLogger.addHandler(filelogging)
		
		# Acquire thread lock
		GLOBALS.SocketListenerLock.acquire()

		# Create socket
		GLOBALS.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		GLOBALS.cLogger.info('Socket created')
		 
		# Bind socket to local host and port
		while True:
			try:
				GLOBALS.cLogger.info('Attempting to bind to %s:%s', str(HOST), str(PORT))
				GLOBALS.s.bind((HOST, PORT))
			except socket.error , msg:
				GLOBALS.cLogger.warning('Bind failed. Error Code : %s %s', str(msg[0]), msg[1])
				GLOBALS.cLogger.warning('Trying again in 10 seconds...')
				time.sleep(10)
				continue
			break

		GLOBALS.cLogger.info('Socket succesfully bound')

		#Start listening on socket
		GLOBALS.s.listen(CONNECTIONS)
		GLOBALS.cLogger.info('Socket listening. Maximum connections: %s', str(CONNECTIONS))
		
		inputs = [ GLOBALS.s ]
		outputs = [ ]
		message_queues = {}
		
		#now keep talking with the client
		while not GLOBALS.SocketListenerKill.isSet():
			#wait to accept a connection - blocking call
			conn, addr = GLOBALS.s.accept()
			GLOBALS.cLogger.info('Connected with %s:%s. Passing to connectionhandler...', addr[0], str(addr[1]))
	 
			#start new thread takes 1st argument as a function name to be run, second is the tuple of arguments to the function.
			thread.start_new_thread(connectionhandler.clientthread ,(conn,))
		
		GLOBALS.cLogger.info('Termination flag has been set. Closing socket...')
		GLOBALS.s.close()
		GLOBALS.cLogger.info('Socket listening terminated.')
		
		GLOBALS.SocketListenerLock.release()