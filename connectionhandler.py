#Function for handling connections. This will be used to create threads
import GLOBALS
import logging
import socket
import beerworker
import confighandler

def clientthread(conn):
	
    # Check if the socketlistener has been killed. If so, close the connection and do nothing.
	if GLOBALS.SocketListenerKill.isSet():
		conn.close()
	else:
		# Receive 16 bytes of data (4 characters). This is fixed-length for sending instructions
		data = conn.recv(16).rstrip()
		GLOBALS.cLogger.info('Data received from client: %s', repr(data))
		
		if len(data) != 4:
			GLOBALS.cLogger.info('Data received not correct length. Ignoring.')
			
			conn.sendall('Data not correct length. Ignoring.')
			conn.close()
		else:
			# Decide what to do based on the message
			# Python does not support switch-case...
			if data == 'derp':
				# DUMMY LEVEL
				pass
			elif data == 'kill':
				# Signalled to kill the beer process
				GLOBALS.cLogger.info('Signal received to terminate main beer process.')
				conn.sendall('Signal received to terminate main beer process.\n\nYOU MUST CONNECT AGAIN IN ORDER TO COMPLETE THIS!\n')
				GLOBALS.cLogger.info('Notifying BeerWorker...')
				GLOBALS.BeerWorker.stoprequest.set()
				
				GLOBALS.cLogger.info('Notifying main process...')
				GLOBALS.BeerProcessKill.set()
			
			elif data == 'endb':
				# Signalled to finish logging & controlling
				GLOBALS.cLogger.info('Signal received to terminate BeerWorker. Notifying BeerWorker...')
				GLOBALS.BeerWorker.stoprequest.set()
			
			elif data == 'endc':
				# Signalled to shut off all control but continue logging
				GLOBALS.BeerWorker.controlEnabled = False
				
			elif data == 'beer':
				# Signalled to start logging & controlling
				# Must wait for ID number
				GLOBALS.cLogger.info('Signal received to start beer logging. Waiting for ID...')
				conn.sendall('Received signal to start beer logging. Please send 4-digit ID number\n')

				try:
					id = int(conn.recv(16))
					
					if GLOBALS.BeerWorker.is_alive():
						GLOBALS.cLogger.info('Requested new BeerWorker but there is already one running')
						conn.sendall('A BeerWorker is already running. Please use the endb command to safely stop the BeerWorker if needed\n')
					else:
						GLOBALS.BeerWorker = beerworker.BeerWorker(id, True)
						GLOBALS.BeerWorker.start()
						GLOBALS.cLogger.info('Starting new BeerWorker with ID %d', id)
						conn.sendall('Starting new BeerWorker with ID %d\n', id)
					
				except socket.timeout, e:
					GLOBALS.cLogger.info('No data was received within timeout period. BeerWorker will not commence. Closing connection...')
					conn.sendall('No data was received within timeout period. BeerWorker will not commence. Closing connection...\n')
					
			elif data == 'been':
				# Signalled to start logging WITHOUT controlling
				# must wait for ID number
				GLOBALS.cLogger.info('Signal received to start beer logging. Waiting for ID...')
				conn.sendall('Received signal to start beer logging. Please send 4-digit ID number\n')

				try:
					id = int(conn.recv(16))
					
					if GLOBALS.BeerWorker.is_alive():
						GLOBALS.cLogger.info('Requested new BeerWorker but there is already one running')
						conn.sendall('A BeerWorker is already running. Please use the endb command to safely stop the BeerWorker if needed\n')
					else:
						GLOBALS.BeerWorker = beerworker.BeerWorker(id, False)
						GLOBALS.BeerWorker.start()
						GLOBALS.cLogger.info('Starting new BeerWorker with ID %d', id)
						conn.sendall('Starting new BeerWorker with ID %d\n', id)
					
				except socket.timeout, e:
					GLOBALS.cLogger.info('No data was received within timeout period. BeerWorker will not commence. Closing connection...')
					conn.sendall('No data was received within timeout period. BeerWorker will not commence. Closing connection...\n')
			
			elif data == 'wgon':
				# wgon = "What's Going On?"
				# Signal received asking the program state
				
				GLOBALS.cLogger.info('Signal received asking program state')
				
				# Let's return a few things:
				# BeerWorker status (including whether it is controlling temperature)
				# <list may get longer over time>
				if GLOBALS.BeerWorker.is_alive():
					if GLOBALS.BeerWorker.controlEnabled == True:
						conn.sendall('BeerWorker is monitoring and controlling temperature\n')
					else:
						conn.sendall('BeerWorker is monitoring. It is NOT controlling temperature\n')
				else:
					conn.sendall('BeerWorker is not running\n')
				
			elif data[0] == 's':
				# s is the code for setting temperature.
				# For example, 's210' would set the temperature to 21.0 degC
				# First obtain the last 3 digits
				temp = float(data[-3:])/10
				GLOBALS.cLogger.info('Received signal to set the temperature to %f', temp)
				
				# update config file
				confighandler.settemperature(GLOBALS.CONFIG_FILE, temp)
				
			elif data[0] == 'd':
				# d is the code for setting the deadband
				# For example, 'd010' would set the deadband to 1.0 degC
				
				# First obtain the last 3 digits
				temp = float(data[-3:])/10
				GLOBALS.cLogger.info('Received signal to set the deadband to %f', temp)
				
				# update config file
				confighandler.setdeadband(GLOBALS.CONFIG_FILE, temp)
				
			else:
				# Unrecognized code
				GLOBALS.cLogger.info('Unrecognized signal. Ignoring [%s]', repr(data))
			
			# close connection
			conn.close()