""" some HAP-python  Accessories
	defines homekit accessory classes for fsREST type products like openweather
	"""
import time,datetime
import logging
import asyncio

READINTERVAL = 3600

if __name__ == "__main__":
	import sys,os,signal
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))
	import lib.tls as tls 
	logger = tls.get_logger(__file__,logging.INFO,logging.DEBUG)
	#from aiowndr import get_traffic
else:
	logger = logging.getLogger(__name__)	# get logger from main program
	#from .aiowndr import get_traffic

from lib.sampleCollector import DBsampleCollector,qVAL,qSTMP
from lib.fsHapper import HAP_accessory,fsBridge 
from lib.devConst import DEVT,qSRC,SIsymb
from lib.devConfig import devConfig
from pyhap.accessory_driver import AccessoryDriver
from accessories.openweather.openweather import openweather,CONFFILE
#from accessories.hue.hueAPI import HueBaseDev

class WeaMap_sampler(DBsampleCollector):
	""" add specific WNDR methods to sampler class """
	manufacturer="openweather"
	def __init__(self, city, pwd, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.tstamp = None
		self.minqid = qSRC['WeaMap']
		#self.host = host
		#self.pwd = pwd
		self.semaphore=None 
		self.defSignaller()
		self.weather = openweather(APIkey=pwd,cityId=city)
		self.lastdt=0
		#stuff = self.weather.getCurrent()
	
	def defServices(self,quantities):
		''' compute dict of recognised services from quantities config '''
		qtts=quantities.copy()
		logger.info('WeaMap quantities:{}'.format(quantities))
		for qid,rec in quantities.items():
			if isinstance(rec,dict): 
				if 'name' in rec and not 'devadr' in rec:
					qtts[qid]['devadr']= secret.owCITY   #next(adr for adr,tp in wndr.rxdct.items() if tp[0]==rec['name'])
				if 'devadr' in rec and not 'typ' in rec:
					qtts[qid]['typ']=DEVT['AirQualityIdx']
				#wndr.rxdct[rec['devadr']][2]  # get typ from const
		return super().defServices(qtts)

	async def receive_message(self):
		n=0
		since = self.sinceStamp()
		if not since or (since > READINTERVAL):
			rec = await self.weather.getAirQuality()
			if rec and isinstance(rec,dict) and 'old' not in rec:
				if rec['dt']<=self.lastdt:
					logger.debug('same WeaMap rec:{}'.format(rec))
				else:
					self.lastdt = rec['dt']
					diff = self.lastdt - time.time()
					if abs(diff)>100:
						logger.warning("WeaMap large tdiff:{}".format(diff))
					logger.info('Openweather since:%s rec:%s' % (self.sinceStamp(),rec))
					for itm,rx in rec.items():
						try:
							typ = next(typ for typ,tp in SIsymb.items() if tp[0].lower()==itm.lower())
						except StopIteration as ex:
							typ =  DEVT['unknown']
							logger.warning('no known WeaMap type:{}'.format(itm))
						qid = self.qCheck(None, devadr=itm, typ=typ)
						logger.debug('WeaMap qid:%s devadr:%s=%s' % (qid,itm,rx))
						self.check_quantity(self.lastdt, quantity=qid, val=rx)
			else:
				logger.debug('bad WeaMap rec:{}'.format(rec))
				await asyncio.sleep(0.2)
				n+=1
		else:
			await asyncio.sleep(0.1)
			logger.debug('WeaMap waiting %.4g' % self.sinceStamp())
		dt = datetime.datetime.now()
		return n,await super().receive_message(dt)  # remaining

	def create_accessory(self, HAPdriver, quantities, aid):
		aname="-".join([self.qname(q) for q in quantities])
		return HAP_accessory(HAPdriver, aname, quantities=quantities, stateSetter=self.set_state, aid=aid, sampler=self)		

def add_WeaMap_to_bridge(bridge, config=CONFFILE):
	""" create WeaMap_happer and add it to the application bridge """
	conf = devConfig(config)
	dbFile=conf['dbFile']
	sampler = WeaMap_sampler(dbFile=dbFile, city=conf['ville'], pwd=conf['apikey'], quantities=conf.itstore, maxNr=1,minNr=1,minDevPerc=0.02)
	bridge.add_sampler(sampler, conf.itstore)

if __name__ == "__main__":
	import secret
	
	QCONF = {  # example default configuration
	"801":{
		"source" :"dehors",
		"typ": 70,
		"name": "aqi",
		"devadr": secret.owCITY,
		"signal":""
 		},
	"dbFile": "",   #"/mnt/extssd/storage/fs20store.sqlite",
	"ville": secret.owCITY,
	"apikey": secret.keyOPENWEATHER  
	}
	conf = devConfig(CONFFILE)
	conf.itstore = QCONF
	#conf.save()
	
	driver = AccessoryDriver(port=51826)
	bridge = fsBridge(driver, 'fsBridge')

	add_WeaMap_to_bridge(bridge, config=CONFFILE)

	driver.add_accessory(accessory=bridge)

	signal.signal(signal.SIGTERM, driver.signal_handler)

	driver.start()

	logger.info('bye')
	