#!/usr/bin/env python3.5
""" Philips / Signify HUE Application Programming Interface
	allows a user app to read sensors and set actors on the Hue bridge.
	Will create user id first time (press button on hue bridge) to be copied to conf file
	http://dresden-elektronik.github.io/deconz-rest-doc/
	"""

#import requests
#import requests.packages.urllib3 as urllib
#from requests.packages.urllib3.exceptions import InsecureRequestWarning

import asyncio, aiohttp #, functools

import math
import time,os
from datetime import datetime,timedelta,timezone
import logging
	
RESOURCES = ['lights','sensors','whitelist','groups','locations','config', 'scenes','schedules','resourcelinks','rules']
# mapping hue quantity to DEVT 
SENSTYPES = {'temperature':0,'lightlevel':5,'buttonevent':12,'presence':11}
LIGHTTYPES = ['On/off light','Dimmable light','Extended color light','Color temperature light', 'On/Off plug-in unit']

UPDATEINTERVAL=300

async def hueGET(ipadr,user='',resource='',timeout=2, semaphore=None, ssl=True):
	''' get state info from hue bridge '''
	#global hueSemaphore
	stuff=None
	url=('https://' if ssl else 'http://') +ipadr+'/api/'
	if len(user)>0:
		url += user+'/'
	if len(resource)>0:
		url += resource
	#auth = aiohttp.BasicAuth(user, pwd)
	if semaphore is None:
		semaphore = HueBaseDev.Semaphore
	try:
		async with aiohttp.ClientSession() as session:
			async with session.get( url=url, timeout=timeout, ssl=ssl) as response:
				if response.status==200:
					try:
						stuff = await response.json()
					except aiohttp.client_exceptions.ContentTypeError as ex:
						stuff = await response.text()
						logger.warning('bad json:%s:%s' % (resource,stuff))
						stuff=None
				else:
					logger.warning('bad hue response :%s on %s' % (response.status,url))
					session.close()
					await asyncio.sleep(0.2)
	except asyncio.TimeoutError as te:
		logger.warning("hueAPI timeouterror %s :on:%s" % (te,url))
		await asyncio.sleep(10)
		stuff={}
	except Exception as e:
		logger.exception("hueAPI unknown exception!!! %s :on:%s" % (e,url))
	#logger.debug('hueGET resource:%s with %s ret:%d' % (resource,r.url,r.status_code))
	return stuff

_loop = None
def st_hueGET(ipadr,user='',resource='',timeout=2,semaphore=None):
	global _loop
	if _loop is None:
		#ret = asyncio.create_task(hueGET(ipadr,user, resource,timeout))
		_loop = asyncio.get_event_loop()
	if semaphore is None:
		if HueBaseDev.Semaphore is None:
			HueBaseDev.Semaphore = asyncio.Semaphore()
		semaphore = HueBaseDev.Semaphore
	if _loop is None or semaphore is None:  # and _loop.isrunning():
		logger.warning('no loop or semaphore')
	else:
		ssl = len(user) > 20  # no ssl for deCONZ
		#future = asyncio.run_coroutine_threadsafe(hueGET(ipadr,user, resource,timeout),_loop)
		#ret = future.result()
		#ret = asyncio.wait_for(hueGET(ipadr,user, resource,timeout),timeout)
		ret = _loop.run_until_complete(hueGET(ipadr,user, resource,timeout,ssl=ssl))
		#_loop.close()
		if ret:
			#logger.info('static hueGET %s' % ret)
			return ret
	return {}

async def hueSET(ipadr,user,prop,val,hueId,resource,reskey='/state',semaphore=None):
	#global hueSemaphore
	if semaphore is None:
		semaphore = HueBaseDev.Semaphore
	url='http://'+ipadr+'/api/'
	if len(user)>0:
		url += user+'/'
	if len(resource)>0:
		url += resource+'/'
	url += '%s%s' % (hueId,reskey)
	logger.info('hueSET:"%s":%s on %s' % (prop,val,url))
	async with aiohttp.ClientSession() as session:
		async with semaphore, session.put(url, data='{"%s":%s}' % (prop,val), ssl=False) as resp:
			logger.info('hueSet resp:%s' % resp.status)


class HueBaseDev (object):
	''' base class for a hue bridge characteristic '''
	Semaphore=None
	

	
async def main(ipadr,user,sensors,lmp):
	await asyncio.gather(* [tst_sensors(sensors), tst_light(lmp), tst_webSock(ipadr,user)])
	
if __name__ == '__main__':	# just testing the API and gets userId if neccesary
	#from lib import tls
	import secret
	logger = logging.getLogger()
	[logger.removeHandler(h) for h in logger.handlers[::-1]] # handlers persist between calls
	logger.addHandler(logging.StreamHandler())	# use console
	logger.addHandler(logging.FileHandler(filename= os.path.expanduser('hueApi.log'), mode='w', encoding='utf-8')) #details to log file
	logger.setLevel(logging.DEBUG)
	logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S%z")))
	#hueSemaphore= asyncio.Semaphore(value=1)
	#HueBaseDev.semaphore = hueSemaphore

	CONF={	# defaults when not in config file
		#"hueuser": "",
		"hueuser":  secret.keySIGNIFY,
		#"huebridge": "192.168.1.21"
		"huebridge": "192.168.1.20"
	}
	#CONF['huebridge'] =ipadrGET()
	
	ipadr=CONF['huebridge']
	user=CONF['hueuser']
	
	#from urllib3.exceptions import InsecureRequestWarning
	#urllib3.disable_warnings(InsecureRequestWarning)

	UPDNMS = { "DeurMot":{0:"DeurTemp", 5:"DeurLux", 11:"DeurMot"},
			     "motMaroc":{0:"tempMaroc", 5:"luxMaroc", 11:"motMaroc"},
			     "keukMot":{0:"keukTemp", 5:"keukLux", 11:"keukMot"},
			     "motGeneric":{0:"tempTerras", 5:"luxTerras", 11:"motTerras"} }

	_loop = asyncio.get_event_loop()
	
	config = st_hueGET(ipadr,user=user, resource='config')
	logger.info('config:%s' % config)
	