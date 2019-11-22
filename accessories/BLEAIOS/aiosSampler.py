#!/usr/bin/env python3.5
""" logs hue sensor values to a database """

import sys,os,time,logging,asyncio
if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	import aiosAPI #import aiosDelegate,ENV_SVR,chANA1ST
else:
	import accessories.BLEAIOS.aiosAPI as aiosAPI  #import aiosDelegate,ENV_SVR
from lib.sampleCollector import DBsampleCollector,forever
from lib.devConst import DEVT
from lib.tls import get_logger
from bluepy import btle

class aiosSampler(DBsampleCollector):
	manufacturer="AdaFruit"
	minqid=400
	def __init__(self, loop, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.aios = aiosAPI.aiosDelegate(loop=loop)
		for qid,tup in self.servmap.items():
			typ = self.qtype(qid)
			if typ < DEVT['secluded']:
				self.aios.startChIdNotifyer(qid % 100)
		#self.aios.startServiceNotifyers(self.aios.dev.getServiceByUUID(btle.UUID(aiosAPI.ENV_SVR))) # activate environamental service
		#aios.startChIdNotifyer(chDIGI, dev)
		#self.aios.startChIdNotifyer(aiosAPI.chANA1ST+3)  # activate 3rd analog channel
		task = loop.create_task(self.aios.servingNotifications())
		
	async def receive_message(self):
		''' get sensors state from BLE and check for updates and process recu when new '''
		n=0
		chId,val = await self.aios.receiveCharValue()
		if chId:
			tstamp = time.time()
			self.check_quantity(tstamp, aiosSampler.minqid+chId, val)
		await asyncio.sleep(1)
		return n
		
	def set_state(self, quantity, state, prop='bri'):
		''' stateSetter for HAP to set hue device '''
		super().set_state(quantity, state, prop=prop)


if __name__ == "__main__":
	import asyncio
	logger = get_logger(__file__)  #logging.getLogger()
	QCONF = { "%d" % (adr+aiosSampler.minqid):{
	  "source":'woon', 
	  "name"  : aiosAPI.NAMES[adr], 
	  "devadr": "%d" % adr, 
	  "typ"   : typ } 
		for adr,typ in zip(
		(aiosAPI.chTEMP,aiosAPI.chHUMI,aiosAPI.chECO2,aiosAPI.chTVOC,aiosAPI.chDIGI,aiosAPI.chANA1ST),
		(DEVT['temperature'],DEVT['humidity'],DEVT['ECO2'],DEVT['TVOC'],DEVT['DIGI'],DEVT['voltage']) ) }
	DBFILE='~/fs20store.sqlite'
	QCONF['dbFile'] = DBFILE
	loop = asyncio.get_event_loop()
	try:
		aios = aiosSampler(loop, DBFILE, quantities=QCONF)
		loop.run_until_complete(forever(aios.receive_message))
	except KeyboardInterrupt:
		logger.warning("terminated by ctrl c")
	except Exception:
		logger.exception("unknown exception!!!")
	finally:
		logger.warning(aios.jsonDump())
		aios.exit()
		time.sleep(2)
		loop.close()
	
