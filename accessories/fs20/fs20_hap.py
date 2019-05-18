""" some HAP-python  Accessories
	defines homekit accessory classes for hue type products like 
	"""
import time
import logging

if __name__ == "__main__":
	import sys,os,signal
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	from pyhap.accessory import Bridge
	from accessories.fs20.fs20Sampler import fs20Sampler
	from pyhap.accessory_driver import AccessoryDriver
else:
	logger = logging.getLogger(__name__)	# get logger from main program
	from .fs20Sampler import fs20Sampler
	
from lib.fsHapper import HAP_accessory, fsBridge #,sampler_accessory
from lib.devConfig import devConfig

class fs20_happer(fs20Sampler):
	def create_accessory(self, HAPdriver, quantities, aid, sampler):
		aname="-".join([sampler.qname(q) for q in quantities])
		return HAP_accessory(HAPdriver, aname, quantities=quantities, stateSetter=sampler.set_state, aid=aid, sampler=sampler)

class fs20_dimmer(HAP_accessory):
	''' possible implementation '''
	def addService(self, quantity, typ):
		#self._services.update({quantity:typ})
		serv=None
		if typ==DEVT['dimmer']:
			serv = self.add_preload_service('Lightbulb', chars=['On','Brightness'])
			self.char_on = serv.configure_char('On', setter_callback=self.HAPonoff)
			self._chars[quantity] = serv.configure_char('Brightness', setter_callback=self.HAPsetting)
		else:
			super().addService(quantity, typ)

	def check_status(self):
		""" checks last received state of a device and notify HAP when something has changed """
		val=None
		sampler = sampler = fsBridge._samplers[self.receiver]
		for qtt in self._chars:  #,rec in sampler.servmap.items():
			if sampler.isUpdated(qtt):
				#typ = sampler.qtype(qtt)
				cde = sampler.get_last(qtt)  # get val from device
				cmd = fstls.fs20commands.index(val)
				self.send_value(val,qtt)

	def send_value(self, value, quantity=None):
		''' send myvalue to HAP '''
		if quantity in self._chars:
			self._chars[quantity].set_value(value)
			logger.info("send HAP val %s to %s quantity:%d" % (value,self.display_name,quantity))
		else:
			logger.warning("no hap quantity like:%s for:%s in %s" % (quantity,value,self._chars))

	def HAPsetting(self, value):
		''' HAP issues to set level for dimmer or lamp '''
		logger.warning("setting %s from %d to %d " % (self.display_name,self.level,value))
		for qtt in self._chars:  #self._services.items():
			self.stateSetter(qtt, value)

def add_fs20_to_bridge(bridge, config='fs20.json'):
	conf = devConfig(config)
	dbFile=conf['dbFile']
	sampler = fs20_happer( dbFile=dbFile, quantities=conf.itstore,maxNr=4,minNr=1,minDevPerc=0.1)
	bridge.add_sampler(sampler, conf.itstore)
	
if __name__ == "__main__":
	""" run this 
	"""		
	logger = logging.getLogger()
	hand=logging.StreamHandler()
	hand.setLevel(logging.INFO)
	logger.addHandler(hand)	# use console
	logger.addHandler(logging.FileHandler(filename='fs20Happer.log', mode='w', encoding='utf-8')) #details to log file
	logger.setLevel(logging.DEBUG)
	logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S")))
	
	try:
		driver = AccessoryDriver(port=51826)
		signal.signal(signal.SIGTERM, driver.signal_handler)

		bridge= fsBridge(driver, 'fsBridge')
		add_fs20_to_bridge(bridge, config="fs20.json")
		driver.add_accessory(accessory=bridge)
	
		signal.signal(signal.SIGTERM, driver.signal_handler)

		driver.start()
	except Exception:
		logger.exception('ending fsHap')
	finally:
		logger.info('bye')
		
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
