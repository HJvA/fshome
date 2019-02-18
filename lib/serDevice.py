#!/usr/bin/env python3.5
""" class for serial transceiver devices
	maintaining state per dev internally
"""
# device / accessoiry type enumeration, codes to be used in fs20.json

import logging

if __name__ == "__main__":
	import asyncio,time
	from devConfig import devConfig
	from serComm import serComm,forever,DEVICE
else:
	from lib.devConfig import devConfig
	from lib.serComm import serComm

__author__ = "Henk Jan van Aalderen"
__version__ = "1.0.0"
__email__ = "hjva@notmail.nl"
__status__ = "Development"

# known device types enumeration
DEVT ={
	"temp":0,      # temperature sensor
	"temp/hum":1,  # temperature + humidity sensor
	"rain":2,      # precipitation meter
	"wind":3,      # wind speed meter
	"temp/hum/press":4, # incl air pressure
	"brightness":5,# brightness actuator
	"pyro":6,      # pyro detector
	"fs20":9,      # unknown fs20 device
	"doorbell":10, # doorbell button
	"motion":11,   # motion detector
	"switch":12,   # mains switch 
	"light":13, 
	"dimmer":14,   # mains (light) dimmer
	"secluded":98, # known device but to be ignored
	"unknown":99 } # unknown device

class serDevice(object):
	""" generic serial device 
		parses messages for a pool of devices
		keeps internal state dict of recognised devices
	"""
	# static data i.e. common for all devices
	config = None  #devConfig("fs20.json")
	devdat={}	   # last parsed messages per device
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
		if self.devkey in serDevice.devdat:  # known device
			return serDevice.devdat[self.devkey][itkey]
		return serDevice.getConfigItem(self.devkey, itkey)  # look in config
	
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
		
	async def receive_message(self, timeout=2, minlen=8, termin='\r\n', signkeys=('typ','devadr')):
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


if __name__ == "__main__":		# just receives strings, basic parsing
	logger = logging.getLogger()
	logger.addHandler(logging.StreamHandler())	# use console
	logger.setLevel(logging.DEBUG)
	loop = asyncio.get_event_loop()

	try:
		#ComPort = serDevice.config.getItem('ComPort',DEVICE)

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
