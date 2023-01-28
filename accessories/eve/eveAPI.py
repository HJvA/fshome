"""
	GATT client for Elgato eve devices (preliminary)
	using bluepy from http://ianharvey.github.io/bluepy-doc/index.html
bluetoothctl scan on
Device D8:59:5B:CD:11:0C AIOS fshome
Device FB:E3:89:87:00:BF Eve Energy DFF5
Device F1:B0:B8:80:03:F8 Eve Energy 1B30
Device 48:70:DE:6C:C6:4F 48-70-DE-6C-C6-4F
Device CC:CC:CC:5A:85:25 Hue Lamp
Device 48:94:F9:EA:96:46 48-94-F9-EA-96-46
Device E7:E7:E0:CA:88:2A 5852A719784E30A3E9
Device C6:F2:F9:C8:64:B2 Hue Lamp
Device CD:52:18:3D:2A:95 Hue Lamp
Device F6:FB:49:21:24:23 Hue Lamp
Device F8:E4:E3:6E:8B:96 ZMED
Device 75:E7:2B:31:C3:17 75-E7-2B-31-C3-17

Device D8:59:5B:CD:11:0C AIOS fshome
Device FB:E3:89:87:00:BF Eve Energy DFF5
Device 56:F0:C4:E2:68:85 56-F0-C4-E2-68-85
Device F1:B0:B8:80:03:F8 Eve Energy 1B30
Device 63:18:AC:E2:1B:A6 63-18-AC-E2-1B-A6
Device CC:CC:CC:5A:85:25 Hue Lamp
Device D8:E0:E1:11:7F:B1 [TV] Samsung 7 Series (55)
Device F8:E4:E3:6E:8B:96 ZMED
Device C6:F2:F9:C8:64:B2 Hue Lamp
Device CE:82:6F:67:FA:26 Eve Degree B5C3
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
DEVADDRESS = "EB:0A:6C:63:0F:BB" # MYCO2
DEVADDRESS = "C8:7F:3C:A7:91:3A"  # Eve room
DEVADDRESS = "FB:E3:89:87:00:BF" # Eve Energy DFF5
DEVADDRESS = "F1:B0:B8:80:03:F8" # Eve Energy 1B30
DEVADDRESS = "CE:82:6F:67:FA:26" # Eve Degree
#


ENERGY_SVR = "0000003E-0000-1000-8000-0026BB765291"
ROOM_SVR   = "0000003E-0000-1000-8000-0026BB765291"
TEMP_SVR   = "0000008A-0000-1000-8000-0026BB765291"
HUM_SVR    = "00000082-0000-1000-8000-0026BB765291"
PRESS_SVR  = "E863F00A-079E-48FF-8F27-9C2605A29F52"

chPOW=1
chENRG=2
chVOLT=3
chAMP =4
chAIRQ=5
chTEMP=6

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
CHARS[chTEMP]   = "00000011-0000-1000-8000-0026BB765291"
CHARS[chAIRQ]   = "E863F10B-079E-48FF-8F27-9C2605A29F52"
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
		service = delg.dev.getServiceByUUID(btle.UUID(TEMP_SVR))
		charist = service.getCharacteristics(CHARS[chTEMP])
		logger.info('Tsrv:%s char:%s ' % (service,charist))
		logger.info(' temp:%s' % delg.read(charist[0]))
		
		logger.info("Services...")
		for svc in delg.dev.services:
			logger.info('stat:%s service:%s' % (delg.dev.getState(),str(svc)))
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