#!/usr/bin/env python3.5
""" logs hue sensor values to a database """

import sys,os,time,logging,asyncio,datetime
if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	from hueAPI import HueSensor,HueLight,HueBaseDev
else:
	from accessories.hue.hueAPI import HueSensor,HueLight
from lib.sampleCollector import DBsampleCollector
from lib.devConst import DEVT
from lib.tls import get_logger

class hueSampler(DBsampleCollector):
	devdat = {}	# dict of hue devices (either lights or sensors)
	#objCount=0
	@property
	def manufacturer(self):
		return "deCONZ" if self.deCONZ else "Signify"
	minqid=200
	def __init__(self,iphue,hueuser, *args, **kwargs):
		super().__init__(*args, **kwargs)
		devlst = HueSensor.devTypes(iphue,hueuser) # list of sensors from hue bridge
		self.minqid=hueSampler.minqid
		self.deCONZ = False
		#hueSampler.objCount+=1
		for hueid,dev in devlst.items():
			qid = self.qCheck(None,hueid,dev['typ'],dev['name'])
			if qid:
				hueSampler.devdat[qid] = HueSensor(hueid,iphue,hueuser) # create sensor 
				if hueSampler.devdat[qid].deCONZ and not self.deCONZ:
					self.deCONZ = True
					logger.info('qid %s deConz=>on, sensor=%s' % (qid, dev))
		logger.info("%s sensors:\n%s\n" % (self.manufacturer,devlst))
		
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
		logger.info("%s lights:\n%s\n" % (self.manufacturer,devlst))
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
		
	def set_state(self, quantity, state, prop='bri', dur=None):
		''' stateSetter for HAP to set hue device '''
		if not super().set_state(quantity, state, prop=prop):
			return None
		return hueSampler.devdat[quantity].setValue(prop, state)
		
	async def setState(self, quantity, state, prop='bri'):
		return await hueSampler.devdat[quantity].setState(prop, state)
		
	def semaphore(self):
		''' to use to block concurrent http tasks '''
		return HueBaseDef.Semaphore

if __name__ == "__main__":
	import asyncio
	logger = get_logger(__file__,logging.INFO,logging.DEBUG) 
	conf={	# to be loaded from json file
		"hueuser": "RnJforsLMZqsCbQgl5Dryk9LaFvHjEGtXqc Rwsel",
		"huebridge": "192.168.1.21",	 
		#"dbFile": "/mnt/extssd/storage/fs20store.sqlite"
		"dbFile": '~/fs20store.sqlite'
	}
	QCONF = {  # example default configuration
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
			logger.debug('receive_message:%d qactive=:%s' % (n,[q for q in qa]))
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
			hueobj.set_state(260, 'true', prop='on')		
			while True:
				await huepoll(hueobj)
		
		except KeyboardInterrupt:
			logger.warning("terminated by ctrl c")
		except Exception:
			logger.exception("unknown exception!!!")
		finally:
			hueobj.set_state(260, 'false', prop='on')
			time.sleep(1)
			hueobj.exit()
			
	HueBaseDev.Semaphore = asyncio.Semaphore()
	hueSampler.minqid=None
	hueobj = hueSampler(conf['huebridge'], conf['hueuser'], dbFile=conf['dbFile'], quantities=QCONF, minNr=1, maxNr=3, minDevPerc=0)

	loop = asyncio.get_event_loop()
	loop.run_until_complete(main(hueobj))
	logger.critical("bye")
else:	# this is running as a module
	logger = get_logger()  # get logger from main program
