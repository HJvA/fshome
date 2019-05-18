#!/usr/bin/env python3.5
""" some HAP-python  Accessories
	defines homekit accessory classes for hue type products like 
	"""
import time,sys,os
import logging

if __name__ == "__main__":
	import signal
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	from pyhap.accessory import Bridge
	from hueSampler import hueSampler
else:
	logger = logging.getLogger(__name__)	# get logger from main program
	from .hueSampler import hueSampler

from lib.fsHapper import HAP_accessory,fsBridge
from lib.devConfig import devConfig
from pyhap.accessory_driver import AccessoryDriver

class hue_happer(hueSampler):
	def create_accessory(self, HAPdriver, quantities, aid, sampler):
		aname="-".join([sampler.qname(q) for q in quantities])
		return HAP_accessory(HAPdriver, aname, quantities=quantities, stateSetter=sampler.set_state, aid=aid, sampler=sampler)


def add_HUE_to_bridge(bridge, config="hue.json"):
	conf = devConfig(config)
	sampler = hue_happer(conf['huebridge'], conf['hueuser'], dbFile=conf['dbFile'], quantities=conf.itstore, minNr=1, maxNr=2, minDevPerc=0)
	bridge.add_sampler(sampler, conf.itstore)
		

if __name__ == "__main__":
	""" run this 
	"""		
	logger = logging.getLogger()
	hand=logging.StreamHandler()
	hand.setLevel(logging.INFO)
	logger.addHandler(hand)	# use console
	logger.addHandler(logging.FileHandler(filename='hueRun.log', mode='w', encoding='utf-8')) #details to log file
	logger.setLevel(logging.DEBUG)
	logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S")))
	
	try:
		driver = AccessoryDriver(port=51826)
		signal.signal(signal.SIGTERM, driver.signal_handler)

		bridge= fsBridge(driver, 'hueBridge')
		add_HUE_to_bridge(bridge, config="hue.json")
		driver.add_accessory(accessory=bridge)
	
		signal.signal(signal.SIGTERM, driver.signal_handler)

		driver.start()
	except Exception:
		logger.exception('ending hueHap')
	finally:
		logger.info('bye')
		
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
