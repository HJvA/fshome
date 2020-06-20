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
		self.reading=False
		try:
			self.ser.open()
		except serial.SerialException as e:
			logger.critical('Could not open serial port {} \n'.format(self.ser.name, e))
			#sys.exit(1)
		logger.debug("serial opened:%s version=%s" % (self.ser.name, serial.VERSION))
		
	def exit(self):
		if self.ser.is_open:
			self.ser.close()
		
	def read(self, timeout=1, minlen=1, termin=b''):
		''' tries to read a string from self.ser till either termin is found, or timeout occurs. 
		'''
		with lock:
			cnt=0
			tres=0.01	# poll resolution
			while cnt<timeout/tres and self.ser.in_waiting+len(self.buf)<minlen:
				time.sleep(tres)
				cnt+=1
			if self.ser.in_waiting>0:
				self.buf += self.ser.read(self.ser.in_waiting)  # get bytes
			if len(self.buf)>minlen:
				if termin in self.buf:
					(data,sep,self.buf) = self.buf.partition(termin)	
					#data.strip(b' \t\n\r')
					logger.debug("interv:%.2f read:%s remains:%s" % (cnt*tres, data, self.buf))
					return data.decode('ascii')
		return None
		
	async def asyRead(self, timeout=1.0, minlen=1, termin=b''):
		''' tries to read a string from self.ser till either termin is found, or timeout occurs.
			asynchronously i.e. uses await to allow cpu to other tasks
		'''
		tres=timeout*0.1	# poll resolution
		if self.ser.is_open:  #not self.reading:
			#with self.ser:      # will open close
			self.reading=True
			cnt=0
			try:			
				while cnt<timeout/tres and self.ser.in_waiting+len(self.buf)<minlen:
					await asyncio.sleep(tres)
					cnt+=1
				if self.ser.in_waiting>0:
					self.buf += self.ser.read(self.ser.in_waiting)
			except KeyboardInterrupt:
				raise
			except serial.SerialException:
				logger.critical('error reading serial port {} \n'.format(self.ser.name, e))
			except TypeError:
				logger.error('serial interrupt while awaiting')
			except Exception as e:
				logger.exception("unknown serial!!! :%s" % e)
			if len(self.buf)>minlen:
				if termin in self.buf:
					(data,sep,rema) = self.buf.partition(termin)  # split bytearray
					#idx = self.buf.find(termin)
					#data= self.buf[:idx]
					#rema= self.buf[idx:]
					self.buf = rema
					#logger.debug("interv:%.2f read:%s remains:%d" % (cnt*tres, len(data), len(self.buf)))
					return data.decode('ascii')
				elif cnt>0:
					logger.debug('serdata without termin :%s' % self.buf)
			self.reading=False
		#else:
		#	await asyncio.sleep(tres)
		return None
	
	def remaining(self):
		#if self.reading:
		#	return -1
		return len(self.buf)
		return self.ser.in_waiting
		
	def flush(self):
		self.ser.reset_input_buffer()  #flushInput()
		self.ser.reset_output_buffer() #flushOutput()
		self.ser.flush()
		n = self.ser.in_waiting
		if n>0:
			logger.warning('still reading %d after flush' % n)
			self.ser.read(n)
		
	def write(self, data):
		#with self.ser:
		if self.ser.is_open:
			#self.ser.open()
			self.ser.write(data)
	
	def send_message(self, msg, termin='\r\n'):
		""" sends a terminated string to the device """
		data = bytes(msg+termin, 'ascii')
		logger.debug("cmd:%s" % data)
		self.write(data)
	
	def get_info(self, command):
		""" queries device with command """
		self.write(command)
		return self.read(timeout=5, termin=b'\n')

if __name__ == "__main__":		# just receives strings, basic parsing
	logger = logging.getLogger()
	logger.addHandler(logging.StreamHandler())	# use console
	logger.setLevel(logging.DEBUG)
	loop = asyncio.get_event_loop()

	devices = [port.device for port in serial.list_ports.comports()]
	ports = [port for port in devices if port in ['/dev/ttyACM0','/dev/ttyUSB0']]
	logger.info('devices:%s: ports:%s:' % (devices,ports))
	ser = serial.Serial(ports[0], BAUDRATE)
	
	try:
		cul = serComm(DEVICE, BAUDRATE)
		logger.info("cul version %s" % cul.get_info(b'V\r\n'))
		
		loop.run_until_complete(forever(cul.asyRead, termin=b'\n'))
	except KeyboardInterrupt:
		logger.warning("terminated by ctrl c")
	loop.close()
	cul.exit()
	logger.critical('bye')
else:
	logger = logging.getLogger(__name__)	# get logger from main program
