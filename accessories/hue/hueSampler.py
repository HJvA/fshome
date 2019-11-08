#!/usr/bin/env python3.5
""" logs hue sensor values to a database """

import sys,os,time,logging,asyncio
if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	from hueAPI import HueSensor,HueLight
else:
	from accessories.hue.hueAPI import HueSensor,HueLight
from lib.sampleCollector import DBsampleCollector,forever
from lib.devConst import DEVT
from lib.tls import get_logger


class hueSampler(DBsampleCollector):
	devdat = {}	# dict of hue devices (either lights or sensors)
	manufacturer="Signify"
	minqid=200
	def __init__(self,iphue,hueuser, *args, **kwargs):
		super().__init__(*args, **kwargs)
		devlst = HueSensor.devTypes(iphue,hueuser) # list of sensors from hue bridge
		logger.info("hue sensors:\n%s\n" % devlst)
		self.minqid=hueSampler.minqid
		for hueid,dev in devlst.items():
			qid = self.qCheck(None,hueid,dev['typ'],dev['name'])
			if qid:
				hueSampler.devdat[qid] = HueSensor(hueid,iphue,hueuser) # create sensor 
		devlst = HueLight.devTypes(iphue,hueuser)
		logger.info("hue lights:\n%s\n" % devlst)
		for hueid,dev in devlst.items():
			#typ = DEVT['lamp']
			#lightTyp = HueLight.lightTyp(devlst,hueid)
			gamut=HueLight.gamut(hueid)
			qid = self.qCheck(None,hueid,DEVT['lamp'],dev['name'])
			if qid:
				logger.debug("having light:(%s) with %s" % (self.servmap[qid],gamut))
				hueSampler.devdat[qid] = HueLight(hueid,gamut,iphue,hueuser) # create light
			
	async def receive_message(self):
		''' get sensors state from hue bridge and check for updates and process recu when new '''
		n=0
		for qid,dev in hueSampler.devdat.items():
			if dev.newval():
				n-=1
				self.check_quantity(dev.lastupdate().timestamp(), qid, dev.value())
			else:
				await asyncio.sleep(dev.refreshInterval/100)
		return n
		
	def set_state(self, quantity, state, prop='bri'):
		''' stateSetter for HAP to set hue device '''
		#super().set_state(quantity, state, prop=prop)
		hueSampler.devdat[quantity].setValue(prop, state)


if __name__ == "__main__":
	import asyncio
	logger = get_logger(__file__)  #logging.getLogger()
	conf={	# to be loaded from json file
		"hueuser": "RnJforsLMZqsCbQgl5Dryk9LaFvHjEGtXqcRwsel",
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
	async def huepoll():
		#while True:	
		global bri
		await hueobj.receive_message()  # both sensors and lights
		for qid,tup in hueobj.servmap.items():
			typ = hueobj.qtype(qid)
			if typ == DEVT['lamp']:
				bri += 1
				#logger.info("set bri of %s to %s" % (qid,bri))
				hueobj.set_state(qid, bri % 100, prop='bri')
				#hueobj.devdat[qid].setValue(prop='bri', bri)
			await asyncio.sleep(0.01)
				
	loop = asyncio.get_event_loop()

	try:
		hueSampler.minqid=None
		hueobj = hueSampler(conf['huebridge'], conf['hueuser'], dbFile=conf['dbFile'], quantities=QCONF, minNr=1, maxNr=10, minDevPerc=0)
		
		hueobj.set_state(260, 'true', prop='on')
		
		#light=hueobj.jsonConfig()	
		#loop.call_soon(hueobj.receive_message)
		#asyncio.run(huepoll())
		
		loop.run_until_complete(forever(huepoll))
		#loop.run_until_complete(forever(hueobj.receive_message))									
	except KeyboardInterrupt:
		logger.warning("terminated by ctrl c")
	except Exception:
		logger.exception("unknown exception!!!")
	finally:
		loop.close()
	hueobj.set_state(260, 'false', prop='on')
	hueobj.exit()
	logger.critical("bye")
else:	# this is running as a module
	logger = get_logger()  # get logger from main program
