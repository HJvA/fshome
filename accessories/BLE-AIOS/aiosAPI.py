"""
	GATT client for Automation IO server
	using bluepy from http://ianharvey.github.io/bluepy-doc/index.html
"""
import time
import asyncio
from bluepy import btle
from bluepyBase import bluepyDelegate,BAS_SVR,showChars


if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))
	import logging
	logger = logging.getLogger()
else:
	import lib.tls as tls
	logger = tls.get_logger()

DEVADDRESS = "d8:59:5b:cd:11:0c"
AIOS_SVR = "00001815-0000-1000-8000-00805f9b34fb"  # automation-IO
ENV_SVR  = "6c2fe8e1-2498-420e-bab4-81823e7b0c03"  # environmental quantities

chTEMP=1
chHUMI=2
chECO2=3
chTVOC=4
chDIGI    = 10		# func id for digitals
chANA1ST  = 11		# func id for first analog channel
chBAT =5

CHARS={}
CHARS[chANA1ST] = "00002a58-0000-1000-8000-00805f9b34fb"
CHARS[chDIGI] = "00002a56-0000-1000-8000-00805f9b34fb"
CHARS[chTEMP] = "00002a6e-0000-1000-8000-00805f9b34fb"
CHARS[chHUMI] = "00002a6f-0000-1000-8000-00805f9b34fb"
CHARS[chECO2] = "6c2fe8e1-2498-420e-bab4-81823e7b7397"
CHARS[chTVOC] = "6c2fe8e1-2498-420e-bab4-81823e7b7398"
CHARS[chBAT]  = "00002a19-0000-1000-8000-00805f9b34fb"


SCALES={chTEMP:100.0, chHUMI:100.0, chANA1ST:10000 }
NAMES ={chTEMP:'temperature', chHUMI:'humidity'}

	
class aiosDelegate(bluepyDelegate):
	def __init__(self, scales=SCALES):
		super().__init__(scales, devAddress=DEVADDRESS)
		self.dev = btle.Peripheral(devAddress, btle.ADDR_TYPE_RANDOM)
		logger.info('dev %s iface:%s' % (self.dev,self.dev.iface))
		self.dev.withDelegate( self )
	
	def CharId(self, charist, CharDef=CHARS):
		uuid = charist.uuid
		if uuid in CHARS.values():
			return next(chID for chID,chUUID in CharDef.items() if chUUID==uuid)
		return None

	def startChIdNotifyer(self, chId):
		if chId == chDIGI or chId>=chANA1ST:
			service = self.dev.getServiceByUUID(btle.UUID(AIOS_SVR))
			if chId>=chANA1ST:
				descr = self.dev.getDescriptors()
				hand=-99
				for des in descr:
					if des.uuid == CHARS[chANA1ST]:
						hand = des.handle
						chT=dev.getCharacteristics(hand-1,hand)[0]
					if des.handle == hand+2:
						chPresForm = des.read()
						chan=chPresForm[5]
						logger.debug('analog chan:%d hand:%d chPresForm:%s' % (chan,hand,tls.bytes_to_hex(chPresForm)))
						self.notifying[hand] = chANA1ST+chan
						if chId == chANA1ST+chan:
							self.startNotification(chT)
		elif chId in [chTEMP,chHUMI,chECO2,chTVOC]:
			service = self.dev.getServiceByUUID(btle.UUID(ENV_SVR))
		elif chId == chBAT:
			service = self.dev.getServiceByUUID(btle.UUID(BAS_SVR))
		if chId in CHARS:
			chT = service.getCharacteristics(btle.UUID(CHARS[chId]))
			self.startNotification(chT[0])
	
async def main():
	logger.info("Connecting...")
	aios = aiosDelegate()
	logger.info("getting notified")
	aios.startServiceNotifyers(aios.dev.getServiceByUUID(btle.UUID(ENV_SVR))) # activate environamental service
	#aios.startChIdNotifyer(chDIGI, dev)
	aios.startChIdNotifyer(chANA1ST+3)  # activate 3rd analog channel
	
	await asyncio.gather( * aios.tasks(aios.dev) )


if __name__ == "__main__":	# testing 
	#aiosID = btle.UUID(AIOS_SVR)
	#aios = dev.getServiceByUUID(aiosID)
	#showChars(aios)

	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		logger.warning('leaving')

	#dev.disconnect()
	logger.warning('bye')