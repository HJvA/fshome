#!/usr/bin/env python3.5
""" logs hue sensor values to a database """

import logging
import os,sys,time
import asyncio
if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	import lib.dbLogger
	from hueAPI import HueSensor,ipadrGET
else:
	from .hueAPI import HueSensor,ipadrGET	
from lib.devConfig import devConfig
from lib.dbLogger import sqlLogger

class hueLogger(object):
	devdat = {}
	def __init__(self, cnf):
		''' constructor : setup database logger for hue sensors
		'''
		#self.dbStore=None
		#if self.dbStore is None:
		if not hasattr(self, 'dbStore'):
			self.acttyp={}
			dbfile = cnf.getItem('dbFile','~/fs20store.sqlite')
			self.dbStore = sqlLogger(dbfile)	# must be created in same thread

		iphue = cnf['huebridge']
		if iphue is None:
			iphue = ipadrGET()
			cnf['huebridge'] = iphue
		devlst = HueSensor.devTypes(iphue,cnf['hueuser'])
		for id,dev in devlst.items():
			crec = cnf.getItem("{}".format(int(id)+200), default=dict(typ=98,name=dev['name'],source=None))
			hueLogger.devdat[id] = HueSensor(id,cnf) # create sensor 
			if len(crec)>1:
				self.acttyp[id] = crec['typ']
				#logger.debug('hue dev:%s cnf:%s' % (dev,crec))
				if crec['source'] is not None:
					logger.info('db upd hue quant:%s %s %s' % (id, dev['name'], crec['source']))
					self.dbStore.additem(int(id)+200, dev['name'],crec['source'],crec['typ'])			
			
	async def receive_message(self):
		await asyncio.sleep(5)
		logger.debug('===rec msg===')
		for id,dev in hueLogger.devdat.items():
			if dev.newval():
				val = dev.value()
				logger.info("%s %s=%s" % (id,dev.name(),val))
				if self.acttyp[id] > 99 and val is not None:
					self.dbStore.logi(int(id)+200,val,tstamp=dev.lastupdate().timestamp())
			else:
				await asyncio.sleep(0.5)
	
async def forever(func, *args, **kwargs):
	''' run (await) function func over and over '''
	while (True):
		await func(*args, **kwargs)
	

if __name__ == "__main__":
	""" run this 
	"""		
	logger = logging.getLogger()
	hand=logging.StreamHandler()
	hand.setLevel(logging.INFO)
	logger.addHandler(hand)	# use console
	logger.addHandler(logging.FileHandler(filename='hueRun.log', mode='w', encoding='utf-8')) #details to log file
	logger.setLevel(logging.INFO)
	logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S")))

	loop = asyncio.get_event_loop()
	
	cnf = devConfig('hue.json')
	if cnf['hueuser'] is None:
		cnf['hueuser'] = "iDBZ985sgFNMJruzFjCQzK-zYZnwcUCpd7wRoCVM"

	try:
		hueLog = hueLogger(cnf)

		loop.run_until_complete(forever(hueLog.receive_message))
	finally:
		cnf.save()
		logger.info('bye')
		
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
