#!/usr/bin/env python3.5
""" some HAP-python  Accessories
	defines homekit accessory classes for the aios client
	"""
import time,sys,os
import logging

if __name__ == "__main__":
	import signal
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	#from pyhap.accessory import Bridge
	from aiosSampler import aiosSampler
	from pyhap.accessory_driver import AccessoryDriver
else:
	logger = logging.getLogger(__name__)	# get logger from main program
	from accessories.BLEAIOS.aiosSampler import aiosSampler

from lib.fsHapper import HAP_accessory,fsBridge
from lib.devConfig import devConfig
from lib.devConst import DEVT
import submod.pyCommon.tls as tls

class AIOS_accessory(HAP_accessory):
	""" adding  to HAP accessory """
	def addService(self, quantity, typ):
		''' add  characteristics to  accessory '''
		if typ==DEVT['DIGI']:
			sampler = fsBridge._samplers[self.receiver]
		else:
			super().addService(quantity, typ)
	
	def HAPsetlev(self, value):
		self.setValue(value, 'bri')

class aios_happer(aiosSampler):
	""" accessories for HAP bridge """
	def create_accessory(self, HAPdriver, quantities, aid):
		aname="-".join([self.qname(q) for q in quantities])
		return AIOS_accessory(HAPdriver, aname, quantities=quantities, stateSetter=self.set_state, aid=aid, sampler=self)

def add_AIOS_to_bridge(bridge, config="aios.json"):
	conf = devConfig(config)
	#logger.info('aios config %s ' % conf)
	sampler = aios_happer(bridge.driver.loop, dbFile=conf['dbFile'], devAddress=conf['devAddress'], quantities=conf.itstore, minNr=2, maxNr=8, minDevPerc=0.2)
	#sampler.minqid=None  # do not auto create
	bridge.add_sampler(sampler, conf.itstore)	

if __name__ == "__main__":
	""" run this 
	"""
	logger = tls.get_logger(__file__)
	
	try:
		driver = AccessoryDriver(port=51826)
		signal.signal(signal.SIGTERM, driver.signal_handler)

		bridge= fsBridge(driver, 'aiosBridge')
		add_AIOS_to_bridge(bridge, config="aios.json")
		driver.add_accessory(accessory=bridge)

		signal.signal(signal.SIGTERM, driver.signal_handler)

		driver.start()
	except Exception:
		logger.exception('ending aiosHap')
	finally:
		logger.info('bye')
		
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
