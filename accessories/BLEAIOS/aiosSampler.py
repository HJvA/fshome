#!/usr/bin/env python3.5
""" logs hue sensor values to a database """

import sys,os,time,logging,asyncio
if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))
	import aiosAPI #import aiosDelegate,ENV_SVR,chANA1ST
else:
	import accessories.BLEAIOS.aiosAPI as aiosAPI  #import aiosDelegate,ENV_SVR
from lib.sampleCollector import DBsampleCollector,forever,sm
from lib.devConst import DEVT
from lib.tls import get_logger
from bluepy import btle

class aiosSampler(DBsampleCollector):
	""" specific AIOS database sample collector """
	manufacturer="AdaFruit"
	minqid=400	# base for database quantityId for aios
	def __init__(self, loop, *args, devAddress=aiosAPI.DEVADDRESS, **kwargs):
		super().__init__(*args, **kwargs)
		masks ={}
		for qid in self.qactive():
			if qid>0 and int(self.qdevadr(qid))==aiosAPI.chDIGI:  # get assigned input bits
				name = self.qname(qid)
				masks[qid] = self.serving(qid, sm.MSK)  
		self.aios = aiosAPI.aiosDelegate(loop=loop, devAddress=devAddress, chInpBits=masks)
		if self.aios.dev is None:
			logger.warning('no BLE device for aios')
		else:
			for qid in self.qactive():
				aiosId = int(self.qdevadr(qid))
				self.aios.startChIdNotifyer(aiosId)
				anaChan = aiosId - aiosAPI.chANA1ST
				if anaChan>=0:
					Vmax = self.serving(qid, sm.MSK)
					if Vmax:
						self.aios.setAnaVoltRange(anaChan, float(Vmax))
			task = loop.create_task(self.aios.servingNotifications())
		
	async def receive_message(self):
		''' await new sensors state from BLE and process recu when new '''
		n=0
		adr,val = await self.aios.receiveCharValue()
		if adr and val is not None:
			if adr<aiosSampler.minqid:
				chId = self.qCheck(None,adr) # search devadr in servmap
				#chId += aiosSampler.minqid
			else:
				chId=adr  # from mask
			if chId:
				n+=1
			else:
				logger.warning('no aios quantity to devadr:%s' % adr)
			tstamp = time.time()
			self.check_quantity(tstamp, chId, val)
		await asyncio.sleep(0.1)
		return n
		
	def set_state(self, quantity, state, prop=None, dur=None):
		''' stateSetter to set digio bit '''
		ok = super().set_state(quantity, state, prop=prop)
		if prop:  # and prop.isnumeric():
			if dur:
				self.aios.setDigPulse(bitnr=int(prop), duration=dur)
			else:
				self.aios.setDigBit(bitnr=int(prop), val=state)
		return ok

if __name__ == "__main__":  # testing
	import asyncio
	DIGINPIN =16   # PIR detector
	logger = get_logger(__file__)  #logging.getLogger()
	# build a default config dict
	QCONF = { "%d" % (adr+aiosSampler.minqid):{
	  "source":'aios', 
	  "name"  : aiosAPI.NAMES[adr], 
	  "devadr": "%d" % adr, 
	  "typ"   : typ,
	  "mask"  : DIGINPIN if adr==aiosAPI.chDIGI else None } 
		for adr,typ in zip(
		(aiosAPI.chTEMP,aiosAPI.chHUMI,aiosAPI.chECO2,aiosAPI.chTVOC,aiosAPI.chDIGI,aiosAPI.chANA1ST),
		(DEVT['temperature'],DEVT['humidity'],DEVT['ECO2'],DEVT['TVOC'],DEVT['DIGI'],DEVT['voltage']) ) }
	DBFILE='~/fs20store.sqlite'
	QCONF['dbFile'] = DBFILE
	QCONF['devAddress']=aiosAPI.DEVADDRESS
	QCONF["%d" % (aiosAPI.chDIGI+aiosSampler.minqid,)]["mask"]=0xffff
	loop = asyncio.get_event_loop()
	try:
		aios = aiosSampler(loop, DBFILE, devAddress=QCONF['devAddress'], quantities=QCONF)
		loop.run_until_complete(forever(aios.receive_message))
	except KeyboardInterrupt:
		logger.warning("terminated by ctrl c")
	except Exception as e:
		logger.exception("unknown exception: %s" % e)
	finally:
		if aios:
			logger.warning(aios.jsonDump())
			aios.exit()
		time.sleep(2)
		loop.close()
else:
	logger = get_logger(__name__)
	
