#!/usr/bin/env python3.5
""" classes for serial transceiver devices
"""
import serial
import time
import asyncio
import logging
from threading import Lock
lock = Lock()

__author__ = "Henk Jan van Aalderen"
__version__ = "1.0.0"
__email__ = "hjva@notmail.nl"
__status__ = "Development"


# Serial Device
DEVICE = '/dev/ttyACM0'
BAUDRATE = 9600 #38400
PARITY = 'N'
RTSCTS = False
XONXOFF = False
TIMEOUT = 1

class serComm(object):
	""" transceiver for sending commands and receiving messages to/from serial devices
	"""
	def __init__(self, serdev=DEVICE, baud=BAUDRATE):
		''' constructor : setup elementary io functions 
		'''
		self.ser = serial.serial_for_url(serdev, do_not_open=True, timeout=TIMEOUT)
		self.ser.baudrate = baud
		self.ser.parity = PARITY
		self.ser.rtscts = RTSCTS
		self.ser.xonxoff = XONXOFF
		self.buf=b""
		try:
			self.ser.open()
		except serial.SerialException as e:
			logger.critical('Could not open serial port {} \n'.format(self.ser.name, e))
			#sys.exit(1)
		logger.debug("serial opened:%s" % self.ser.name)
		
	def exit(self):
		self.ser.close()
		
	def read(self, timeout=1, minlen=1, termin=b''):
		''' tries to read a string from self.ser till either termin is found, or timeout occurs. 
		'''
		with lock:
			cnt=0
			tres=0.01	# poll resolution
			while cnt<timeout/tres and self.ser.inWaiting()+len(self.buf)<minlen:
				time.sleep(tres)
				cnt+=1
			if self.ser.inWaiting()>0:
				self.buf += self.ser.read(self.ser.inWaiting())
			if len(self.buf)>minlen:
				if termin in self.buf:
					(data,sep,self.buf) = self.buf.partition(termin)	
					#data.strip(b' \t\n\r')
					logger.debug("interv:%.2f read:%s remains:%s" % (cnt*tres, data, self.buf))
					return data.decode('ascii')
		return None
		
	async def asyRead(self, timeout=1, minlen=1, termin=b''):
		''' tries to read a string from self.ser till either termin is found, or timeout occurs.
			asynchronously i.e. uses await to allow cpu to other tasks
		'''
		with lock:
			cnt=0
			tres=0.5	# poll resolution
			while cnt<timeout/tres and self.ser.inWaiting()+len(self.buf)<minlen:
				await asyncio.sleep(tres)
				cnt+=1
			try:
				if self.ser.inWaiting()>0:
					self.buf += self.ser.read(self.ser.inWaiting())
			except serial.SerialException:
				logger.critical('error reading serial port {} \n'.format(self.ser.name, e))
			if len(self.buf)>minlen:
				if termin in self.buf:
					(data,sep,self.buf) = self.buf.partition(termin)	
					#data.strip(b' \t\n\r')
					logger.debug("interv:%.2f read:%s remains:%s" % (cnt*tres, data, self.buf))
					return data.decode('ascii')
		return None
		
	def write(self, data):
		self.ser.write(data)
		
	def get_info(self, command):
		self.write(command)
		return self.read(timeout=5, termin=b'\n')
	

async def forever(func, *args, **kwargs):
	''' run (await) function func over and over '''
	while (True):
		await func(*args, **kwargs)

if __name__ == "__main__":		# just receives strings, basic parsing
	logger = logging.getLogger()
	logger.addHandler(logging.StreamHandler())	# use console
	logger.setLevel(logging.DEBUG)
	loop = asyncio.get_event_loop()

	try:
		cul = serComm(DEVICE,BAUDRATE)
		logger.info("cul version %s" % cul.get_info(b'V\r\n'))
		
		loop.run_until_complete(forever(cul.asyRead, termin=b'\n'))
									
	except KeyboardInterrupt:
		logger.warning("terminated by ctrl c")
	loop.close()
	cul.exit()
	logger.critical('bye')
else:
	logger = logging.getLogger(__name__)	# get logger from main program
