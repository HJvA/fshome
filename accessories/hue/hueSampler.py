#!/usr/bin/env python3.5
""" logs hue sensor values to a database """

import sys,os,time,logging,asyncio
if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	from hueAPI import HueSensor
else:
	from accessories.hue.hueAPI import HueSensor,HueLight
from lib.sampleCollector import DBsampleCollector,forever

QCONF = {  # example default configuration
  "208": {
    "typ": 5,
    "source": "entree",
    "name": "DeurLux"
  },
  "235": {
    "typ": 12,
    "source": "kamerEet",
    "name": "eet knop"
  },
  "230": {
    "typ": 12,
    "source": "woon",
    "name": "kamer knoppen"
  },
  "232": {
    "typ": 11,
    "name": "keukMotion",
    "source": "keuken"
  },
  "244": {
    "typ": 11,
    "name": "MotMaroc",
    "source": "tuin"
  },
  "243": {
    "typ": 0,
    "source": "tuin",
    "name": "tempMaroc"
  },
  "256": {
    "typ": 12,
    "source": "zeSlaap",
    "name": "zSlaap switch"
  },
  "231": {
    "typ": 0,
    "source": "keuken",
    "name": "KeukTemp"
  },
  "206": {
    "typ": 0,
    "source": "entree",
    "name": "DeurTemp"
  },
  "207": {
    "typ": 11,
    "source": "entree",
    "name": "DeurMotion"
  },
  "245": {
    "typ": 5,
    "name": "luxMaroc",
    "source": "tuin"
  },
  "233": {
    "typ": 5,
    "name": "KeukLux",
    "source": "keuken"
  }
 }

class hueSampler(DBsampleCollector):
	devdat = {}
	manufacturer="Signify"
	def __init__(self,iphue,hueuser, *args, **kwargs):
		super().__init__(*args, **kwargs)
		devlst = HueSensor.devTypes(iphue,hueuser) # list of sensors from hue bridge
		logger.info("hue devices:%s" % devlst)
		self.minqid=200
		for hueid,dev in devlst.items():
			qid = self.qCheck(None,hueid,dev['typ'],dev['name'])
			hueSampler.devdat[qid] = HueSensor(hueid,iphue,hueuser) # create sensor 
		#devlst = HueLight.devTypes()
		#for hueid,dev in devlst.items():
		#	ikey = self.qid(hueid)
		#	light = HueLight(hueid,iphue,hueuser) # create light
		# TODO expose lights to Hap
			
	async def receive_message(self):
		''' get sensors state from hue bridge and check for updates and process recu when new '''
		n=0
		for qid,dev in hueSampler.devdat.items():
			if dev.newval():
				n-=1
				self.check_quantity(dev.lastupdate().timestamp(), qid, dev.value())
			else:
				await asyncio.sleep(0.1)
		return n

if __name__ == "__main__":
	import asyncio
	logger = logging.getLogger()
	hand=logging.StreamHandler()
	hand.setLevel(logging.INFO)
	logger.addHandler(hand)	# use console
	logger.addHandler(logging.FileHandler(filename='huelog.log', mode='w', encoding='utf-8'))
	logger.setLevel(logging.DEBUG)
	logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S")))
	conf={	# to be loaded from json file
		"hueuser": "iDBZ985sgFNMJruzFjCQzK-zYZnwcUCpd7wRoCVM",
		"huebridge": "192.168.1.21",	 
		#"dbFile": "/mnt/extssd/storage/fs20store.sqlite"
		"dbFile": '~/fs20store.sqlite'
	}

	loop = asyncio.get_event_loop()

	try:
		hueobj = hueSampler(conf['huebridge'], conf['hueuser'], dbFile=conf['dbFile'], quantities=QCONF, minNr=1, maxNr=2, minDevPerc=0)

		loop.run_until_complete(forever(hueobj.receive_message))									
	except KeyboardInterrupt:
		logger.warning("terminated by ctrl c")
	hueobj.exit()
	logger.critical("bye")
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
