#!/usr/bin/env python3.5
""" 
logs hue sensor values to a database """

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
from lib.devConst import DEVT

typLIM = DEVT['secluded']

class hueLogger(object):
	""" logger for multiple hue sensors """
	devdat = {}
	def __init__(self, cnf):
		''' constructor : setup database logger for hue sensors
		'''
		self.acttyp={}
		dbfile = cnf.getItem('dbFile','~/fs20store.sqlite')
		self.dbStore = sqlLogger(dbfile)	# must be created in same thread

		iphue = cnf['huebridge']
		if iphue is None:
			iphue = ipadrGET()
			cnf['huebridge'] = iphue
		devlst = HueSensor.devTypes(iphue,cnf['hueuser']) # list of sensors from hue bridge
		for ikey,dev in devlst.items():
			crec = cnf.getItem("{}".format(int(ikey)+200), default=dict(typ=dev['typ'],name=dev['name'],source=None,aid=None))
			hueLogger.devdat[ikey] = HueSensor(ikey,iphue,cnf['hueuser']) # create sensor 
			if len(crec)>1:
				#logger.debug('hue dev:%s cnf:%s' % (dev,crec))
				if crec['source'] is None:
					self.acttyp[ikey] = typLIM # not active default
				else:
					self.acttyp[ikey] = crec['typ']
					logger.info('updating hue quantity def:%s %s %s %d' % (ikey, dev['name'], crec['source'],crec['typ']))
					self.dbStore.additem(int(ikey)+200, dev['name'],crec['source'],crec['typ'])			
			
	async def receive_message(self):
		''' poll hue bridge and maintain devdat state '''
		await asyncio.sleep(5)
		logger.debug('===rec msg===')
		for ikey,dev in hueLogger.devdat.items():
			if dev.newval(60):
				#dev.name()
				self.process_recu(ikey,dev.lastupdate().timestamp(),dev.value(),self.acttyp[ikey])
			else:
				await asyncio.sleep(0.5)
	
	def process_recu(self,ikey,tstamp,val,typ):
		logger.info("recu: ikey:%s %s=%s @%s" % (ikey,typ,val,tstamp))
		if typ < typLIM and val is not None:
			self.dbStore.logi(int(ikey)+200,val,tstamp=tstamp)
		
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
		cnf['hueuser'] = "RnJforsLMZqsCbQgl5Dryk9LaFvHjEGtXqc Rwsel"
		#"iDBZ985sgFNMJruzFjCQzK-zYZnwcUCpd7wRoCVM"

	try:
		hueLog = hueLogger(cnf)

		loop.run_until_complete(forever(hueLog.receive_message))
	except Exception as e:
		logger.error('exception %s' % e)
	finally:
		cnf.save()
		logger.info('bye')
		
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
