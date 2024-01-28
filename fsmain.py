#!/usr/bin/env python3.5
""" application to receive fs20/hue/DSMR accessoire traffic and log results to sqlite and optionally to homekit.
	uses project HAP-python : https://github.com/ikalchev/HAP-python
"""

import logging
import signal
import time
import os,asyncio
from queue import Empty
import multiprocessing	# https://superfastpython.com/multiprocessing-in-python/

from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import __version__ as pyHAP_version
from lib.fsHapper import fsBridge
from accessories.hue.hueHap import add_HUE_to_bridge
from accessories.p1smart.p1DSMR_Hap import add_p1DSMR_to_bridge
from accessories.fs20.fs20_hap import add_fs20_to_bridge
from accessories.BLEAIOS.aiosHap import add_AIOS_to_bridge
from accessories.netgear.netgear_HAP import add_WNDR_to_bridge
from accessories.sounder.sounds import add_SND_to_bridge
from accessories.openweather.openweather_HAP import add_WeaMap_to_bridge
from submod.pyCommon.tls import get_logger
#from lib.devConfig import devConfig
import fssite

__maintainer__ = "Henk Jan van Aalderen"
__email__  = "hjva@notmail.nl"
__status__ = "Development"

DEBUG = False
CONFFILE = "./config/fs20.json"
logger = None

loop = asyncio.get_event_loop()  # unique loop for application

def fsmainRun(cnfFname=CONFFILE, lock=None, prqueue=None):
	#config = devConfig(cnfFname)
	#dbfile = config.getItem('dbFile',None)
	#global dbStore
	#global prsite
	driver = AccessoryDriver(port=51826, loop=loop) # prevent renewing loop 
	#loop = driver.loop
	bridge= fsBridge(driver, 'fsBridge')
	
	add_SND_to_bridge(bridge,config=None)
	if os.path.isfile("config/aios.json"):
		add_AIOS_to_bridge(bridge, config="./config/aios.json")
	if os.path.isfile("config/deCONZ.json"):
		add_HUE_to_bridge(bridge, config="./config/deCONZ.json")
	if os.path.isfile("config/hue.json"):
		add_HUE_to_bridge(bridge, config="./config/hue.json")
	if os.path.isfile("config/fs20.json"):
		add_fs20_to_bridge(bridge, config="./config/fs20.json")
	if os.path.isfile("config/p1DSMR.json"):
		add_p1DSMR_to_bridge(bridge, config="./config/p1DSMR.json")
	#if os.path.isfile("config/WNDR.json"):
	#	add_WNDR_to_bridge(bridge, config="./config/WNDR.json")
	if os.path.isfile("config/openweather.json"):
		add_WeaMap_to_bridge(bridge, config="./config/openweather.json")
	
	driver.add_accessory(accessory=bridge)
	if prqueue:
		prsite = multiprocessing.Process(name='fssite', target=fssite.fssiteRun, args=(CONFFILE,lock,prqueue))
		driver.add_job(checkAlife, prqueue, prsite )
		#driver.add_job(checkAlife, fssite.fssiteRun, args=(CONFFILE,lock,prqueue))
	signal.signal(signal.SIGTERM, driver.signal_handler)
	driver.start()

async def checkAlife(prqueue,prsite):  #prtask,*args):
	n=0
	#prm = multiprocessing.current_process()
	#prsite = multiprocessing.Process(prtask, args)
	if prqueue:
		logging.info("checking fssite alife process:{} with queue:{}".format(prsite.name,prqueue))
		await asyncio.sleep(20)
		prsite.start()
		pid = prsite.pid
		await asyncio.sleep(10)
		while True:
			try:
				if prsite.is_alive():  # can only test a child process
					item = prqueue.get(timeout=600)
					logger.debug("getting life {} from queue left:{} n:{}".format(item, prqueue.qsize(), n ))
				else:
					await asyncio.sleep(20)					
					logger.info("starting prsite alife :{} exitcode:{} pid:{}".format(prsite.name, prsite.exitcode, prsite.pid))
					prsite.join(1)
					prsite.start()
					pid = prsite.pid
			except Empty:
				try:
					#except Exception as ex:
					logger.warning("not alife: no items in queue n:{} pr={}".format(n, prsite.name)) #prsite.is_alive()))
					if prsite is None:
						logger.info("prsite not alife!!")
					else:
						pid = prsite.pid
						#if prsite.is_alive():  # can only test a child process
						logger.error("killing prsite :{}, pid:{}".format(prsite.name,pid))
						os.kill(pid, signal.SIGTERM)
						await asyncio.sleep(10)
						prsite.kill() 
						await asyncio.sleep(10)
						prsite.terminate()
						await asyncio.sleep(10)
						logger.info("restarting alife:{} pid:{}".format(prsite.name, prsite.pid))
						prsite.start()
				except Exception as ex:
					logger.error("unknown alife exception:{}".format(ex))  #cannot start a process twice 
				await asyncio.sleep(2)
				#prsite.start()
			except Exception as ex:
				logger.error("not alife:{}: unknown ex={} ".format(n,ex))
			if prqueue.empty():
				await asyncio.sleep(300)
			else:
				await asyncio.sleep(1)
			#logger.info("test alife {} nleft:{}".format(n, prqueue.qsize() if prqueue else -1))
			n+=1
	else:
		await asyncio.sleep(300)
		

if __name__ == '__main__':
	logger = get_logger(__file__,logging.INFO, logging.DEBUG if DEBUG else logging.INFO)
	# setup logging for console and error log and generic log
	#logger = get_logger(__file__, levelConsole=logging.INFO, levelLogfile=logging.INFO)
	logger.info('with HAP-python %s' % pyHAP_version)
	#multiprocessing.set_start_method('spawn')
	prqueue = multiprocessing.Queue(maxsize=100)
	lock = multiprocessing.Lock()
	#prsite = multiprocessing.Process(target=fssite.fssiteRun, args=(CONFFILE,lock,prqueue), name='fssite')
	prmain = multiprocessing.Process(target=fsmainRun, args=(CONFFILE,lock,prqueue))
	try:
		prmain.start()
		time.sleep(20)
		#prsite.start()
		
		prmain.join()
		#prsite.join()
	finally:
		logger.warning("terminating")
		prmain.terminate()
		#prsite.terminate()
	# terminate it 
	logger.info('bye')
	for hnd in logger.handlers:
		hnd.flush()
	logging.shutdown()
	logging._handlers.clear()
	time.sleep(2)
else:	# this is running as a module
	logger = get_logger()	# get logger from main program
	
