"""
	base interface to Bluetooth Low Energy device
	using bluepy from http://ianharvey.github.io/bluepy-doc/index.html
"""
import time
import asyncio
from bluepy import btle

if __name__ == "__main__":
	import logging
	logger = logging.getLogger()
else:
	import lib.tls as tls
	logger = tls.get_logger()

DEVINF_SVR="0000180a-0000-1000-8000-00805f9b34fb"  # device info
BAS_SVR   ="0000180f-0000-1000-8000-00805f9b34fb"		# battery level

SCALES={} # chId:factor kvp's

def showChars(svr):
	''' lists all characteristics from a service '''
	logger.info('svr %s uuid %s' % (svr,svr.uuid))
	for ch in svr.getCharacteristics():
		logger.info("ch %s %s %s" % (str(ch),ch.propertiesToString(),ch.uuid))
		if ch.supportsRead():
			byts = ch.read()
			num = int.from_bytes(byts, byteorder='little', signed=False)
			logger.info("read %d:%s %s" % (ch.getHandle(),tls.bytes_to_hex(byts),num))

class bluepyDelegate(btle.DefaultDelegate):
	def __init__(self, scales={}):
		super().__init__()
		self.queue = asyncio.Queue()
		self.notifying = {}
		self.scales=scales
		
	def handleNotification(self, cHandle, data):
		""" callback getting notified by bluepy """
		self.queue.put_nowait((cHandle,data))

	def startServiceNotifyers(self, service):
		for chT in service.getCharacteristics(): 
			self.startNotification(chT)
			
	def CharId(self, charist):
		return charist.getHandle()
		if uuid in CHARS.values():
			return next(chID for chID,chUUID in CharDef.items() if chUUID==uuid)
		return None

	def startNotification(self, charist):
		''' sets charist on ble device to notification mode '''
		hand = charist.getHandle()
		if charist.properties & btle.Characteristic.props["NOTIFY"]:
			if hand not in self.notifying:
				chId = self.CharId(charist)
				self.notifying[hand] = chId
			charist.peripheral.writeCharacteristic(hand+1, b"\x01\x00", withResponse=True)
			logger.info('starting notificatio on %s' % charist)
		else:
			logger.warning('NOTIFY not supported by:%s' % charist)
		if charist.supportsRead():
			val = charist.read()
			self.queue.put_nowait((hand,val))

	async def receiveCharValue(self):
		""" consume received notification data """
		tup = await self.queue.get()
		chId = None
		if tup:
			if tup[0] in self.notifying:
				chId = self.notifying[tup[0]]
			val = tls.bytes_to_int(tup[1], '<')
		else:
			val = float('NaN')
		if chId in self.scales:
			val = float(val) / self.scales[chId]
		logger.info('chId:%s = %s' % (chId,val))
		self.queue.task_done()
		return chId,val

	async def awaitingNotifications(self):
		""" keep consuming received notifications """
		while True:
			dat = await self.receiveCharValue()

	async def servingNotifications(self, dev):
		""" keep polling bluepy for received notifications """
		while True:
			if dev.waitForNotifications(0.1):
				#await self.receiveCharValue()
				pass
			await asyncio.sleep(0.1)
		
	def tasks(self, dev):
		''' background tasks receiving notifications from BLE device '''
		return [ asyncio.create_task(self.awaitingNotifications()),
					asyncio.create_task(self.servingNotifications(dev)) ]
	
async def main(dev, servNotifying):
	delg = bluepyDelegate()
	if servNotifying:
		for srv in servNotifying:
			delg.startServiceNotifyers(dev.getServiceByUUID(btle.UUID(srv)))
	dev.withDelegate( delg )
	await asyncio.gather( * delg.tasks(dev) )
	

if __name__ == "__main__":	# testing 
	DEVADDRESS = "d8:59:5b:cd:11:0c"

	logger.info("Connecting...")
	dev = btle.Peripheral(DEVADDRESS, btle.ADDR_TYPE_RANDOM) #  btle.ADDR_TYPE_PUBLIC)
	
	logger.info('dev %s iface:%s' % (dev,dev.iface))
	
	descr = dev.getDescriptors()
	for des in descr:
		try:
			logger.debug('descr:%d:%s: %s' % (des.handle, des, tls.bytes_to_hex(des.read())))
		except btle.BTLEGattError as e:
			logger.warning('%s:%s:' % (des,e ))
	
	logger.info("Services...")
	for svc in dev.services:
		logger.info(str(svc))
		time.sleep(0.1)
		showChars(svc)

	logger.info("getting notified")
	try:
		asyncio.run(main(dev, [BAS_SVR,DEVINF_SVR]))
	except KeyboardInterrupt:
		logger.warning('leaving')
		
	dev.disconnect()
	logger.warning('bye')