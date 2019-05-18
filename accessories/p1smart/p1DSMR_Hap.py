""" some HAP-python  Accessories
	defines homekit accessory classes for hue type products like 
	"""
import time
import logging

if __name__ == "__main__":
	import sys,os,signal
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	from p1DSMR import p1DSMR,DEVICE,BAUDRATE
else:
	logger = logging.getLogger(__name__)	# get logger from main program
	from .p1DSMR import p1DSMR,DEVICE,BAUDRATE,p1QDEF
from lib.serComm import serComm
from lib.fsHapper import HAP_accessory,fsBridge  #,sampler_accessory
from lib.devConfig import devConfig
from pyhap.accessory_driver import AccessoryDriver

class DSMR_happer(p1DSMR):
	def create_accessory(self, HAPdriver, quantities, aid, sampler):
		aname="-".join([sampler.qname(q) for q in quantities])
		stateSetter = sampler.set_state
		return HAP_accessory(HAPdriver, aname, quantities=quantities, stateSetter=stateSetter, aid=aid, sampler=sampler)		

def add_p1DSMR_to_bridge(bridge, config='p1DSMR.json'):
	conf = devConfig(config)
	p1ser = serComm(DEVICE,BAUDRATE)
	dbFile=conf['dbFile']
		
	sampler = DSMR_happer(p1ser, dbFile=dbFile, quantities=conf.itstore, maxNr=120,minNr=1,minDevPerc=8.0)
	bridge.add_sampler(sampler, conf.itstore)

		
if __name__ == "__main__":
	logger = logging.getLogger()
	hand=logging.StreamHandler()
	hand.setLevel(logging.INFO)
	logger.addHandler(hand)	# use console
	logger.addHandler(logging.FileHandler(filename='p1DSMR_Hap.log', mode='w', encoding='utf-8'))
	logger.setLevel(logging.DEBUG)
	logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S")))
	
	driver = AccessoryDriver(port=51826)
	bridge = fsBridge(driver, 'fsBridge')
	#bridge=get_FS20_bridge(driver, config="fs20.json")

	add_p1DSMR_to_bridge(bridge, config="p1DSMR.json")
	#add_HUE_to_bridge(bridge, config="hue.json")

	driver.add_accessory(accessory=bridge)

	signal.signal(signal.SIGTERM, driver.signal_handler)

	driver.start()

	logger.info('bye')
