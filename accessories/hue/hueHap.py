#!/usr/bin/env python3.5
""" some HAP-python  Accessories
	defines homekit accessory classes for hue type products like 
	"""
import time,sys,os
import logging

if __name__ == "__main__":
	import signal
	sys.path.append(os.getcwd()) # + '/..')
	#sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	import hueSampler
	import hueSamplerV2
	from pyhap.accessory_driver import AccessoryDriver
else:
	logger = logging.getLogger(__name__)	# get logger from main program
	import accessories.hue.hueSampler as hueSampler
	import accessories.hue.hueSamplerV2 as hueSamplerV2

from lib.fsHapper import HAP_accessory,fsBridge
from lib.devConfig import devConfig
from lib.devConst import DEVT
import secret
#from accessories.hue.hueAPIv2 import DEBUG

DEBUG=0

class HUE_accessory(HAP_accessory):
	""" adding HUE lights to HAP accessory """
	def addService(self, quantity, typ):
		''' add lamp characteristics to HUE accessory '''
		if typ==DEVT['lamp']:
			sampler = fsBridge._samplers[self.receiver]
			self.level=None
			chars=None
			if sampler is hueSampler.hueSampler:  # deCONZ or hue bridge V1
				self.gamut = sampler.devdat[quantity].gamut()
				if type(self.gamut) is list:	# color can be set
					chars=['On','Brightness','Hue','Saturation']
				elif type(self.gamut) is dict:	# ct can be set
					chars=['On','Brightness']
				elif self.gamut is not None:
					chars=['On','Brightness']
			if chars is not None:
				serv = self.add_preload_service('Lightbulb', chars=chars)
				self._chars[quantity] = {'bri': serv.configure_char('Brightness',setter_callback=self.HAPsetlev)}
				self._chars[quantity].update({'on': serv.configure_char('On',setter_callback=self.HAPonoff)})
				if 'Hue' in chars:
					self._chars[quantity].update({'hue': serv.configure_char('Hue',setter_callback=self.HAPsethue)})
				if 'Saturation' in chars:
					self._chars[quantity].update({'sat': serv.configure_char('Saturation',setter_callback=self.HAPsetsat)})
			else:
				self._chars[quantity] = {}
		else:
			super().addService(quantity, typ)
	
	def HAPsetlev(self, value):
		self.setValue(value, 'bri')
	
	def HAPsethue(self, value):
		self.setValue(value, 'hue')
	
	def HAPsetsat(self, value):
		self.setValue(value, 'sat')

class hue_happerV2(hueSamplerV2.hueSampler):
	""" HUE accessories for HAP bridge """
	def create_accessory(self, HAPdriver, quantities, aid):
		aname="-".join([self.qname(q) for q in quantities])
		return HUE_accessory(HAPdriver, aname, quantities=quantities, stateSetter=self.set_state, aid=aid, sampler=self)
		
class hue_happer(hueSampler.hueSampler):
	""" HUE accessories for HAP bridge """
	def create_accessory(self, HAPdriver, quantities, aid):
		aname="-".join([self.qname(q) for q in quantities])
		return HUE_accessory(HAPdriver, aname, quantities=quantities, stateSetter=self.set_state, aid=aid, sampler=self)

def add_HUE_to_bridge(bridge, config="hue.json"):
	conf = devConfig(config)
	if 'deCONZ' in config:
		apikey = conf['hueuser'] if conf['hueuser'] else secret.keyDECONZ  
		sampler = hue_happer(conf['huebridge'], apikey, dbFile=conf['dbFile'], quantities=conf.itstore, minNr=1, maxNr=2, minDevPerc=0)
	else:
		apikey = conf['hueuser'] if conf['hueuser'] else secret.keySIGNIFY  
		sampler = hue_happerV2(conf['huebridge'], apikey, dbFile=conf['dbFile'], quantities=conf.itstore, minNr=1, maxNr=2, minDevPerc=2, debug=DEBUG)
	#sampler.minqid=None  # do not auto create
	bridge.add_sampler(sampler, conf.itstore)	

if __name__ == "__main__":
	""" run this for testing
	"""
	from lib.tls import get_logger
	logger = get_logger(__file__)
		
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
