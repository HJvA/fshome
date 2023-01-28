#!/usr/bin/env python3.5
""" logs hue sensor values to a database """

import sys,os,time,logging,asyncio,datetime
if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	from hueAPI import HueSensor,HueLight,HueBaseDev,getTyp,getProp
else:
	from accessories.hue.hueAPI import HueSensor,HueLight,getTyp,getProp
from lib.sampleCollector import DBsampleCollector
from lib.devConst import DEVT,qSRC
from lib.tls import get_logger

class hueSampler(DBsampleCollector):
	""" fshome interface to a Hue or deCONZ bridge """
	devdat = {}	# dict of hue devices (either lights or sensors)
	@property
	def manufacturer(self):
		return "deCONZ" if self.deCONZ else "Signify"
	#minqid= QID['HUE'] # 500 for deCONZ
	
	def __init__(self,iphue,hueuser, *args, **kwargs):
		super().__init__(*args, **kwargs)
		nDev = len(hueSampler.devdat)
		devlst = HueSensor.devTypes(iphue,hueuser) # list of sensors from hue bridge
		self.deCONZ = False
		for hueid,dev in devlst.items():
			qid = self.qCheck(None,hueid,dev['typ'],dev['name'])
			if qid:
				hueSampler.devdat[qid] = HueSensor(hueid,iphue,hueuser) # create sensor 
				if hueSampler.devdat[qid].deCONZ and not self.deCONZ:
					self.deCONZ = True
					logger.info('qid %s deConz=>on, sensor=%s' % (qid, dev))
			else:
				logger.debug('unknown sensor hueid=%s : %s' % (hueid,dev))
		logger.info("%s sensors:%s" % (self.manufacturer,len(hueSampler.devdat)-nDev))
		nDev = len(hueSampler.devdat)
		devlst = HueLight.devTypes(iphue,hueuser)
		for hueid,dev in devlst.items():
			#typ = DEVT['lamp']
			#lightTyp = HueLight.lightTyp(devlst,hueid)
			#gamut=HueLight.gamut(iphue, hueid)
			qid = self.qCheck(None,hueid,DEVT['lamp'],dev['name'])
			if qid:
				#logger.debug("having light:(%s) with %s" % (self._servmap[qid],gamut))
				hueSampler.devdat[qid] = HueLight(hueid,iphue,hueuser) # create light
				#self.deCONZ = self.deCONZ or hueSampler.devdat[qid].deCONZ
				if hueSampler.devdat[qid].deCONZ and not self.deCONZ:
					self.deCONZ = True
					logger.info('qid %s deConz=>on, light=%s' % (qid,dev))
			else:
				logger.info('unknown light hueid=%s : %s' % (hueid,dev))
		self.minqid = qSRC['deCONZ'] if self.deCONZ else qSRC['HUE']
		logger.info("%s lights:%s" % (self.manufacturer,len(hueSampler.devdat)-nDev))
		self.defSignaller()
			
	async def receive_message(self):
		''' get sensors state from hue bridge and check for updates and process recu when new '''
		n=0
		dt=datetime.datetime.now()
		for qid,dev in hueSampler.devdat.items():
			if self.deCONZ == dev.deCONZ:  # same bridge
				newval = await dev.newval()
				if newval:
					n-=1
					dtm = await dev.lastupdate()
					val = await dev.value()
					if dtm and not isinstance(val, dict):
						self.check_quantity(dtm.timestamp(), qid, val)
					else:
						logger.warning('bad hue val %s at %s' % (dtm,val))
				else:
					await asyncio.sleep(dev.refreshInterval/1000)
			else:
				logger.debug('(%d) other hue_sampler %s<>%s in %s' % (qid,self.deCONZ,dev.deCONZ,self.manufacturer))
		return n,await super().receive_message(dt)
		
	async def eventListener(self, signaller):
		''' waiting for websocket events '''
		await super().eventListener(signaller)
		
		if self.deCONZ:
			mcnt=0
			for qid,dev in hueSampler.devdat.items():
				logger.info('running eventListener for (%s) %s' % (qid,dev))
				if self.deCONZ and dev.deCONZ:  # deCONZ bridge
					#await asyncio.sleep(30)
					devName = await dev.name()
					logger.info('waiting for events on %s for %s with %s' % (qid,devName,self))
					while True:
						msg = await dev.eventListener()  # calls websocket
						if msg and 'id' in msg:
							qid = self.qCheck(quantity=None,devadr=msg['id'])
							if qid and 'state' in msg:
								rec = msg['state']
								typ = getTyp(rec)
								val = getProp(rec)
								#if typ!=dev.typ:
								#	logger.warning('uneq event types: %d != %d' % (typ,dev.typ))
								if 'buttonevent' in rec:
									logger.info('button chg:%s' % rec['buttonevent'])
								if signaller.checkEvent(qid,val):
									logger.info('%s event by %s=>%s typ(%s) cnt:%s' % (devName,qid,rec,typ,mcnt))
									signaller.signal(qid, rec)
								else:
									logger.info("no event for {} with {}".format(qid,rec))
								await asyncio.sleep(4)
								mcnt=0
							elif 'attr' in msg:  # eg for lights
								rec = msg['attr']
							else:
								mcnt +=1
								logger.debug("no event for qid:{} in evmsg:{}".format(qid,msg))
						else:
							logger.info("no id in event msg:{}".format(msg))
							await asyncio.sleep(0.01)
		logger.warning('no eventListener in %s, deCONZ:%s' % (self,self.deCONZ))
			
		
	def set_state(self, quantity, state, prop='bri', dur=None):
		''' stateSetter for HAP to set hue device '''
		if not super().set_state(quantity, state, prop=prop):
			return None
		if quantity in hueSampler.devdat:
			return hueSampler.devdat[quantity].setValue(prop, state)
		else:
			logger.warning('no such quantity:%s' % quantity)

	async def setState(self, quantity, state, prop='bri'):
		if quantity in hueSampler.devdat:
			return await hueSampler.devdat[quantity].setState(prop, state)
		else:
			logger.warning('no such quantity:%s' % quantity)
		
	def semaphore(self):
		''' to use to block concurrent http tasks '''
		return HueBaseDef.Semaphore

if __name__ == "__main__":
	import asyncio
	import secret
	logger = get_logger(__file__,logging.INFO,logging.DEBUG) 
	conf={	# to be loaded from json file
		"hueuser":secret.keyDECONZ,
		"huebridge": "192.168.1.20",	
		#"dbFile": "/mnt/extssd/storage/fs20store.sqlite"
		"dbFile": '~/fs20store.sqlite'
	}
	QCONF = {  # example default configuration
  "570": {
    "source": "gang",
    "name": "gangSwitch",
    "devadr": "2",
    "typ": 12,
    "signal" :"116=17,4cfa"
  },
  "580":{
    "source" :"gang",
    "typ": 13,
    "name": "deurLmp",
    "devadr": "2"
	 },
	 
  "207": {
    "source": "entree",
    "name": "DeurMotion",
    "devadr": "7",
    "typ": 11
  },
  "243": {
    "source": "tuin",
    "name": "tempMaroc",
    "devadr": "12",
    "typ": 0
  },
  "208": {
    "source": "entree",
    "name": "DeurLux",
    "devadr": "8",
    "typ": 5
  },
  "256": {
    "source": "zeSlaap",
    "name": "zSwitch",
    "devadr": "3",
    "typ": 12
  },
  "245": {
    "source": "tuin",
    "name": "luxMaroc",
    "devadr": "11",
    "typ": 5
  },
  "206": {
    "source": "entree",
    "name": "DeurTemp",
    "devadr": "9",
    "typ": 0
  },
  "231": {
    "source": "keuken",
    "name": "keukTemp",
    "devadr": "19",
    "typ": 0
  },
  "244": {
    "source": "tuin",
    "name": "motMaroc",
    "devadr": "10",
    "typ": 11
  },
  "230": {
    "source": "woon",
    "name": "tapKnops",
    "devadr": "2",
    "typ": 12
  },
  "232": {
    "source": "keuken",
    "name": "keukMot",
    "devadr": "17",
    "typ": 11
  },
  "235": {
    "source": "kamerEet",
    "name": "eetKnops",
    "devadr": "5",
    "typ": 12
  },
  "233": {
    "source": "keuken",
    "name": "keukLux",
    "devadr": "18",
    "typ": 5
  },
  "260":{    
    "typ": 13,
    "name": "eetStrip",
    "devadr":"4",
    "aid":20
  }
}
	
	bri=1
	async def huepoll(hueobj):
		#while True:	
		#loop = asyncio.get_running_loop()
		global bri
		n = await hueobj.receive_message()  # both sensors and lights
		qa = hueobj.qactive()
		if n:
			logger.debug('receive_message:%s qactive=:%s' % (n,[q for q in qa]))
		for qid in qa:
			upd = hueobj.isUpdated(qid)
			if upd:
				last = hueobj.get_last(qid)
				logger.debug('qid %s updated to %s' % (qid,last))
			typ = hueobj.qtype(qid)
			if typ == DEVT['lamp']:
				bri += 1
				#logger.info("set bri of %s to %s" % (qid,bri))
				await hueobj.setState(qid, bri % 100, prop='bri')
				#hueobj.set_state(qid, bri % 100, prop='bri', loop=loop)
				#hueobj.devdat[qid].setValue(prop='bri', bri)
				#await asyncio.sleep(0.1)
		await asyncio.sleep(1)
	
	async def main(hueobj):
		try:		
			#hueobj.set_state(260, 'true', prop='on')		
			while True:
				await huepoll(hueobj)
		
		except KeyboardInterrupt:
			logger.warning("terminated by ctrl c")
		except Exception:
			logger.exception("unknown exception!!!")
		finally:
			#hueobj.set_state(260, 'false', prop='on')
			time.sleep(1)
			hueobj.exit()
			
	HueBaseDev.Semaphore = asyncio.Semaphore()
	#hueSampler.minqid=None
	hueobj = hueSampler(conf['huebridge'], conf['hueuser'], dbFile=conf['dbFile'], quantities=QCONF, minNr=1, maxNr=3, minDevPerc=0)

	loop = asyncio.get_event_loop()
	loop.run_until_complete(main(hueobj))
	logger.critical("bye")
else:	# this is running as a module
	logger = get_logger()  # get logger from main program
