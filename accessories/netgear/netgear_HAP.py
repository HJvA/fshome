""" some HAP-python  Accessories
	defines homekit accessory classes for netgear type products like WNDR4300
	"""
import time
import logging
import asyncio

cnfFile = "WNDR.json"
READINTERVAL = 120

if __name__ == "__main__":
	import sys,os,signal
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	from aiowndr import get_traffic
else:
	logger = logging.getLogger(__name__)	# get logger from main program
	from .aiowndr import get_traffic
from lib.sampleCollector import DBsampleCollector
from lib.fsHapper import HAP_accessory,fsBridge 
from lib.devConst import DEVT
from lib.devConfig import devConfig
from pyhap.accessory_driver import AccessoryDriver
from accessories.hue.hueAPI import HueBaseDev

class WNDR_sampler(DBsampleCollector):
	""" add specific WNDR methods to sampler class """
	manufacturer="netgear"
	def __init__(self, host, pwd, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.tstamp = None
		self.minqid = 700
		self.host = host
		self.pwd = pwd
		self.semaphore=HueBaseDev.Semaphore
		
	
	def defServices(self,quantities):
		''' compute dict of recognised services from quantities config '''
		qtts=quantities.copy()
		for qid,rec in quantities.items():
			if 'name' in rec and not 'devadr' in rec:
				qtts[qid]['devadr']=next(adr for adr,tp in wndr.rxdct.items() if tp[0]==rec['name'])
			if 'devadr' in rec and not 'typ' in rec:
				qtts[qid]['typ']=DEVT['Mbytes']
				#wndr.rxdct[rec['devadr']][2]  # get typ from const
		return super().defServices(qtts)

	async def receive_message(self):
		if self.sinceAccept()>=READINTERVAL:
			rec = await get_traffic(host=self.host, pwd=self.pwd, semaphore=self.semaphore)
			if rec:
				logger.debug('wndr since:%.6g rec:%s' % (self.sinceAccept(),rec))
				for itm,rx in rec.items():
					tstamp = time.time()
					qid = self.qCheck(None, devadr=itm, typ=DEVT['Mbytes'])
					#logger.debug('wndr qid:%s devadr:%s=%s' % (qid,itm,rx))
					self.check_quantity(tstamp, quantity=qid, val=rx)
			else:
				logger.warning('nothing received from wndr :%s' % rec)
				await asyncio.sleep(0.2)
		else:
			await asyncio.sleep(0.01)
			logger.debug('wndr waiting %.6g' % self.sinceAccept())
		return 0  # remaining

class WNDR_happer(WNDR_sampler):
	""" apple HAP sampler on WNDR router """
	def create_accessory(self, HAPdriver, quantities, aid):
		aname="-".join([self.qname(q) for q in quantities])
		return HAP_accessory(HAPdriver, aname, quantities=quantities, stateSetter=self.set_state, aid=aid, sampler=self)		

def add_WNDR_to_bridge(bridge, config=cnfFile):
	""" create WNDR_happer and add it to the application bridge """
	conf = devConfig(config)
	dbFile=conf['dbFile']
	sampler = WNDR_happer(dbFile=dbFile, host=conf['host'], pwd=conf['pwd'],  quantities=conf.itstore, maxNr=30,minNr=4,minDevPerc=0.02)
	bridge.add_sampler(sampler, conf.itstore)

if __name__ == "__main__":
	logger = logging.getLogger()
	hand=logging.StreamHandler()
	hand.setLevel(logging.DEBUG)
	logger.addHandler(hand)	# use console
	logger.addHandler(logging.FileHandler(filename='WNDR_Hap.log', mode='w', encoding='utf-8'))
	logger.setLevel(logging.DEBUG)
	logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S")))
	
	QCONF = {  # example default configuration
	"700": {
     "devadr":"rxToday",
     "name": "MbToday",
     "source": "gang" },
	"701": {
     "devadr":"rxYestday",
     "name": "MbYesterday",
     "source": "gang" },
   "702": {
     "devadr":"txToday",
     "name": "tMbToday",
     "source": "gang" },
	"703": {
     "devadr":"txYestday",
     "name": "tMbYesterday",
     "source":"gang"},
   #"dbFile": "/mnt/extssd/storage/fs20store.sqlite"
	"dbFile": '~/fs20store.sqlite',
	"host": '192.168.1.1',
	"pwd": 'har'
   }
	conf = devConfig(cnfFile)
	conf.itstore = QCONF
	conf.save()
	
	driver = AccessoryDriver(port=51826)
	bridge = fsBridge(driver, 'fsBridge')

	add_WNDR_to_bridge(bridge, config=cnfFile)

	driver.add_accessory(accessory=bridge)

	signal.signal(signal.SIGTERM, driver.signal_handler)

	driver.start()

	logger.info('bye')
