"""
	GATT client for Elgato eve devices (preliminary)
	using bluepy from http://ianharvey.github.io/bluepy-doc/index.html
"""
import time
import asyncio
from bluepy import btle

if __name__ == "__main__":  # testing this module
	import sys,os,logging
	sys.path.append(os.getcwd()) # bring lib in path: to be called from cwd=fshome
	#sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..')) # bring lib in path
	import lib.tls as tls
	logger = tls.get_logger(__file__, logging.DEBUG, logging.DEBUG)
else:
	import lib.tls as tls
	logger = tls.get_logger()
from accessories.BLEAIOS.bluepyBase import bluepyDelegate,BAS_SVR,showChars

#sudo hcitool lescan
DEVADDRESS = "FB:E3:89:87:00:BF" # Eve Energy DFF5
DEVADDRESS = "F1:B0:B8:80:03:F8" # Eve Energy 1B30
#F1:B0:B8:80:03:F8 Eve


chPOW=1
chENRG=2
chVOLT=3
chAMP =4

chDIGI    = 10		# func id for digitals
chANA1ST  = 11		# func id for first analog channel
chBAT =5
dscVALRNG = 6
dscPRESFORM = 7

CHARS={}
CHARS[chENRG]   = "E863F10C-079E-48FF-8F27-9C2605A29F52"
CHARS[chPOW]    = "E863F10D-079E-48FF-8F27-9C2605A29F52"
CHARS[chVOLT]   = "E863F10A-079E-48FF-8F27-9C2605A29F52"
CHARS[chAMP]    = "E863F126-079E-48FF-8F27-9C2605A29F52"
CHARS[chBAT]    = 0x2a19   #"00002a19-0000-1000-8000-00805f9b34fb"

class eveDelegate(bluepyDelegate):
	''' specialization of bluepy to have aios interface '''
	def __init__(self, devAddress=DEVADDRESS):
		''' devAddress : address of device as found by e.g. bluetoothctl
		'''
		super().__init__(devAddress)

	def __repr__(self):
		"""Return the representation of the ble client."""
		return 'ble aios client: dev@{} ' \
			.format(self.dev.addr )
	
	def _CharId(self, charist, CharDef=CHARS):
		''' return unique id for a chracteristic '''
		chId = None
		uuid = charist.uuid
		self._getAnaMap()
		for chi,uid in CharDef.items():
			if btle.UUID(uid) == uuid:
				chId = chi
				break
		return chId

	def startChIdNotifyer(self, chId):
		''' start GATT notification mode on server for denoted characteristic '''
		if self.dev is None:
			logger.error('no ble device for notifying on %d' % chId)
			return
		elif self.dev.getState():
			logger.info('starting notification on %s dev=%s' % (chId,self.dev.getState()))
			if chId>=chANA1ST:  # finding which chan
				return
			elif chId == chDIGI:
				service = self.dev.getServiceByUUID(btle.UUID(AIOS_SVR))
			elif chId in [chTEMP,chHUMI,chECO2,chTVOC]:
				service = self.dev.getServiceByUUID(btle.UUID(ENV_SVR))
			elif chId == chBAT:
				service = self.dev.getServiceByUUID(btle.UUID(BAS_SVR))
			if chId in CHARS:
				logger.info('getCharacteristics:%s on %s' % (CHARS[chId],service))
				charist = service.getCharacteristics(CHARS[chId])
				if charist:
					self.startNotification(charist[0])
				else:
					logger.error("no BLE characteristic for %s with uuid:%s in %s" % (chId,btle.UUID(CHARS[chId]),service))

		
	async def receiveCharValue(self):
		""" consume received notification data """
		chId,val = await super().receiveCharValue()
		if chId == chDIGI:
			#self._digiParse(val)  # get bitvals
			bits=[]
			for chB,bitn in self.chInpBits.items():
				if self.bitvals[bitn]:
					bits.extend([chB,1])
				logger.debug('digi:%d mask:%0x => %s' % (chB, 1 << self.chInpBits[chB], bits))
			if bits:
				return tuple(bits)
			return chId,None
		else:
			return chId,val

			

async def main():
	""" for testing """
	logger.info("Connecting...")
	delg = eveDelegate(DEVADDRESS)
	
	logger.info('dev %s iface:%s' % (delg.dev,delg.dev.iface if delg.dev else None) )
	
	if delg.dev:
		logger.info("Services...")
		for svc in delg.dev.services:
			logger.info(str(svc))
			time.sleep(0.1)
			showChars(svc)
		time.sleep(5)
		
		descr = delg.dev.getDescriptors()
		for des in descr:
			try:
				logger.debug('descr:%d:%s: %s' % (des.handle, des, des.read()))
			except btle.BTLEGattError as e:
				logger.warning('%s:%s:' % (des,e ))
				

	try:
		tasks = delg.tasks()
		#tasks.append(asyncio.create_task( blinkTask(aios, DIGOUTBIT) ))
		logger.info("running tasks %s \nin aios %s" % (tasks,delg))
		await asyncio.gather( * tasks )
	except KeyboardInterrupt:
		logger.warning('leaving')
	finally:
		delg.dev = None

if __name__ == "__main__":	# testing 
	asyncio.run(main()) #, debug=True)
	time.sleep(1)
	logger.warning('bye')