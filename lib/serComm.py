#!/usr/bin/env python3.5
""" classes for serial transceiver devices
"""
import serial
import time
import asyncio
import logging
from threading import Lock
lock = Lock()

#from lib import devConfig
if __name__ == "__main__":
	from devConfig import devConfig
else:
	from .devConfig import devConfig

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

# device / accessoiry type enumeration
DEVT ={
	"temp":0, "temp/hum":1, "rain":2, "wind":3, "temp/hum/press":4, "brightness":5,
	"pyro":6, "fs20":9,
	"doorbell":10, "motion":11, "switch":12, "light":13, "dimmer":14, "secluded":98, "unknown":99}


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
	
class serDevice(object):
	""" generic serial device 
		parses messages for a pool of devices
		keeps internal state dict of recognised devices
	"""
	config = None  #devConfig("fs20.json")
	devdat={}	# last parsed messages per device
	commPort=None

	def __init__(self, devkey=None, transceiver=None):
		''' constructor : setup serial device
			input:transceiver : serial communication port device e.g. culfw.de
		'''
		self.devkey=devkey	# key for devdat
		if transceiver is None:
			if serDevice.commPort is None:
				serDevice.commPort = serComm()	# create default
		else:
			serDevice.commPort = transceiver
	
	@staticmethod
	def getConfigItem(devkey, itmkey):
		if devkey in serDevice.config.itstore:
			if itmkey in serDevice.config.itstore[devkey]:
				return serDevice.config.itstore[devkey][itmkey]
		return None
	
	def getRecordItem(self, itkey):
		''' get item from actual device state '''
		if self.devkey is None:
			return None
		if self.devkey in serDevice.devdat:
			return serDevice.devdat[self.devkey][itkey]
		return self.getConfigItem(itkey)
	
	@staticmethod
	def setConfig(devConfigName,newItemPrompt=None):
		'''loads devices configuration/map from disk'''
		serDevice.config = devConfig(devConfigName,newItemPrompt=None)
		
	@staticmethod
	def getConfig():
		return serDevice.config.itstore.items()
	
	def exit(self):
		serDevice.commPort.exit()
		
	def parse_message(self,data):
		''' virtual : to be enhanced to convert string to dict of items'''
		return {"msg":data.strip(' \r\n'),"len":len(data)}
		
	async def receive_message(self, timeout=2, minlen=8, termin='\r\n',
		signkeys=('typ','devadr')):
		'''receive dict of items from a (any) device
			recognises device from signkeys in parsed/received items
			tries to add unknown devices to config'''
		msg = await serDevice.commPort.asyRead(timeout, minlen, bytes(termin,'ascii'))
		if msg is None or len(msg)==0:
			#logger.debug("nothing received this time %s" % time.time())
			rec={}
		else:
			rec = self.parse_message(msg)
			signature={}
			if not serDevice.config is None:
				for devk in signkeys:  # build device signature from message
					if devk in rec:
						if devk!='typ' or rec[devk]!=DEVT['fs20']: # don't have typ in signature if no sens
							signature[devk]=rec[devk]  # add this key to the signature
			if len(signature)>0:
				devkey = serDevice.config.checkItem(signature) # lookup dev by signature and store it if not there
				if devkey is None or len(devkey)==0:
					logger.error("no name in config for %s with msg:%s" % (signature,msg))
				else:
					#if devkey[0]=='_' or len(signature) < len(signkeys):
					if 'typ' in rec:
						typ =rec['typ']
					else:
						typ = None
					if typ==DEVT['fs20']:
						typ = serDevice.getConfigItem(devkey,'typ')
						if not typ is None:
							rec.update(typ=typ)
					if typ is None:
						logger.error("receiving unknown device(%s) dd:%s msg:%s having:%s %d<%d" % (devkey,time.strftime("%y%m%d %H:%M:%S"), msg,rec,len(signature),len(signkeys)))
					if typ==DEVT['secluded']:
						logger.info("%s ignored" % rec)
					else:
						rec.update({'new':1,'name':devkey})
						newdev = not devkey in serDevice.devdat
						serDevice.devdat[devkey] = rec
					if newdev:
						logger.warning("new device received:%s with:%s now having:%s" % (devkey,signature, serDevice.devdat.keys()))
			else:
				logger.error("unknown device:%s config:%s" % (msg,serDevice.config))
			logger.debug("rec:%s" % rec)
		return rec
	
	def device_status(self):
		''' retrieve last received message of this device
			keeps track how many times the value has been read since last update
		'''
		if self.devkey is None or not self.devkey in serDevice.devdat:
			#logger.error("no rec for %s" % self.devkey)
			return None
		rec = serDevice.devdat[self.devkey]
		timesseen = rec.get("new",0)
		if timesseen<=0:
			logger.info("%s not updated %d, returning act" % (self.devkey,timesseen))
		serDevice.devdat[self.devkey].update(new = timesseen-1)
		return serDevice.devdat[self.devkey]

		
	def send_message(self, msg, termin='\r\n'):
		""" sends a terminated string to the device """
		data = bytes(msg+termin, 'ascii')
		logger.debug("cmd:%s" % data)
		serDevice.commPort.write(data)
	
	def get_info(self, cmd="V"):
		''' sends a command and reads the response '''
		self.send_message(cmd)
		return self.receive_message()

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
		cul = serComm()
		logger.info("cul version %s" % cul.get_info(b'V\r\n'))
		device = serDevice(cul)
		
		loop.run_until_complete(forever(device.receive_message, signkeys=None))
				
		# how it would be synchronously 
		while True:
			time.sleep(2)
			data = device.receive_message() # does not recognise devices here
			if data is None:
				logger.warning(".")
					
	except KeyboardInterrupt:
		logger.warning("terminated by ctrl c")
	loop.close()
	device.exit()
	logger.critical('bye')
else:
	logger = logging.getLogger(__name__)	# get logger from main program
