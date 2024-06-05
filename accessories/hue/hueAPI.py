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
import time,os,sys
from datetime import datetime,timedelta,timezone
import logging
	
RESOURCES = ['lights','sensors','whitelist','groups','locations','config', 'scenes','schedules','resourcelinks','rules']
# mapping hue quantity to DEVT 
SENSTYPES = {'temperature':0,'lightlevel':5,'buttonevent':12,'presence':11,'lux':5,'relative_rotary':12}
SCALERS   = {'temperature':100,'lightlevel':10000,'lux':1}
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

async def createUser(devname,appname,ipadr=None,deCONZ=False):
	''' create user on hue bridge '''
	if ipadr is None:
		#_loop = asyncio.get_event_loop()
		ipadr = await ipadrGET()
	logger.critical('please press button on hue bridge within 30s')
	time.sleep(30)
	if deCONZ:
		data = '{ "devicetype": "%s-%s" }' % (appname,devname)
		#data.add_field('username',"fsHenkJan120361")
	else:
		data = aiohttp.FormData()
		data.add_field('devicetype', "%s#%s" % (appname,devname))
	async with aiohttp.ClientSession() as session:
		async with session.post(url=('http://' if deCONZ else 'https://') +ipadr+'/api/', data=data, ssl=not deCONZ) as response:
			pst = await response.json()
	#pst = requests.post('https://'+ipadr+'/api/', data='{"%s":"%s#%s"}' % ('devicetype',appname,devname), verify=False)
	logger.warning('newuser:%s' % (pst))
	return pst

async def ipadrGET(bridgeName=None, portal='https://discovery.meethue.com/'):
	''' finds ip adres of hue bridge on LAN '''
	
	async with aiohttp.ClientSession() as session:
		async with session.get(url=portal, ssl=True) as response:
			stuff = await response.json()
	logger.info('hue bridge ip request:%s' % stuff)
	for user in stuff:  #[1:]:
		adr = user['internalipaddress']
		try:
			r = await hueGET(adr, timeout=0.1)  # requests.get('http://'+adr,verify=False,timeout=0.1)
		except requests.ConnectionError:
			logger.error("Hue ConnectionError ")
			continue
		if r and r.status_code == 200:
			cnf =  await hueGET(adr,resource='config') # requests.get('https://%s/api/config' % adr,verify=False)
			if cnf:
				logger.info('config:%s' % cnf.json())
				if bridgeName is None or bridgeName == cnf['name']:
					return adr
	return None

async def webSocket(ipadr,user,port=443,reskey='state'):
	''' waits for deCONZ to emit event 
		https://dresden-elektronik.github.io/deconz-rest-doc/endpoints/websocket/#websocket-configuration
	'''
	url='ws://'+ipadr + ':%d' % port
	if reskey:
		url += "/%s" % reskey
	try:
		logger.debug('waiting for events on webSocket :%s' % url)
		jsdat = {}
		#timeout = aiohttp.ClientTimeout(total=6000)
		async with aiohttp.ClientSession() as session:
			async with session.ws_connect(url,timeout=None) as ws:
				async for msg in ws:
					if msg.type == aiohttp.WSMsgType.TEXT:
						jsdat = msg.json()
						if 'state' in jsdat:
							logger.info('deCONZ event type:%s data:%s' % (msg.type,msg.data))
						await asyncio.sleep(0.5)
						break
					elif msg.type == aiohttp.WSMsgType.CLOSED:
						logger.warning('webSocket closed')
					elif msg.type == aiohttp.WSMsgType.ERROR:
						logger.warning('webSocket error')
					else:
						logger.warning('webSocket:%s unknown typ:%s' % (url,msg.type))
		return jsdat
	except Exception as ex:
		logger.warning('error websocket %s' % ex)
		
def getProp(state):
	""" get property value """
	typ = getTyp(state)
	if typ is not None:
		prop=next(prp for prp in SENSTYPES if prp in state)
		if prop in state:
			val= state[prop]
			if prop=='lightlevel':  # to lux
				val /= 10000.0
				val = math.pow(10.0,val)
				val = round(val,2)
			elif prop in SCALERS:
				val = float(val) / SCALERS[prop]
			return val
	return None
	
def getTyp(state):
	if state and set(state) & set(SENSTYPES):
		prop = next(prp for prp in SENSTYPES if prp in state)
		#name = HueSensor._sensors[self.ipadr][self.hueId]['name'] 
		typ = SENSTYPES[prop] if prop in SENSTYPES else None
		return typ

class HueBaseDev (object):
	''' base class for a hue bridge characteristic '''
	Semaphore=None
	def __init__(self,hueId,resource,ipadr,userid,semaphore):
		''' hueId : Id of hue characteristic on hue bridge
			resource : 'sensors' or 'lights'
		'''
		self.hueId = hueId
		self.resource = resource
		self.user=userid
		self.ipadr=ipadr
		self.dtActive = datetime.now(timezone.utc)
		self.last=None
		self.deCONZ = (len(userid) <20)  # either deCONZ or HUE bridge
		if semaphore is not None:
			HueBaseDev.Semaphore=semaphore
		if HueBaseDev.Semaphore is None:
			HueBaseDev.Semaphore = asyncio.Semaphore()
			logger.info('setting up hueSemaphore')
		logger.info('creating hue dev:%s for %s' % (hueId,userid))
		#urllib.disable_warnings(InsecureRequestWarning)
	
	@property
	def devDescr(self):
		descr ="deCONZ" if self.deCONZ else "Signify"  # either deCONZ or HUE bridge
		return descr
		
	def __repr__(self):
		return 'device={} hueId={}>'.format(self.devDescr, self.hueId)

	async def hueGET(self,resource):
		''' get state info from hue bridge '''
		r = await hueGET(self.ipadr, self.user, resource, semaphore=HueBaseDev.Semaphore, ssl=not self.deCONZ)
		#self.life=0
		if r is None:
			return {}
		#logger.debug('hueGET resource:%s with %s ret:%d at %s' % (resource,r.url,r.status_code,datetime.now()))
		return r
	
	async def eventListener(self):
		''' raw event listener '''
		msg = await webSocket(self.ipadr, self.user, reskey=None ) 
		logger.debug('event from webSocket:%s' % msg)
		return msg
		
	async def refresh(self):
		self._cache(await self.hueGET(self.resource))
		logger.debug('refreshing %s len=%d' % (self.resource,len(self._cache())))
		
		
	async def state(self, prop=None, reskey='state'):
		''' fetch state info from local cache (cache will be refreshed if too old) '''
		cache = await self._cache()
		if self.hueId in cache:
			if prop is None:
				return cache[self.hueId][reskey]
			elif reskey in cache[self.hueId] and isinstance(cache[self.hueId], dict) and prop in cache[self.hueId][reskey]:
				return cache[self.hueId][reskey][prop]
		elif cache: # when fetching cache failed
			logger.warning('hueid %s not in cache %s' % (self.hueId,prop))
		return None
		
	async def lastupdate(self):
		''' to be overriden by ancesters to return real time updated '''
		return self.dtActive
			
	async def newval(self, minChangeInterval=0):
		''' checks whether self.prop value has been changed
			only provokes update when last activity has been some time (minChangeInterval) ago '''
		dtm = await self.lastupdate()  # cach maybe refreshed
		if dtm-self.dtActive >= timedelta(seconds=minChangeInterval):
			val =await self.state(prop=self.prop)
			if val is not None:
				return (val != self.last)
			logger.debug('no prop %s in state %s' % (self.prop,val))
		else:
			await asyncio.sleep(0.01)
		return False

	async def value(self):
		''' get last self.prop value from cache '''
		self.dtActive = await self.lastupdate()	# mark using as activity
		self.last = await self.state(prop=self.prop)
		return self.last
	
	def name(self, cache=None):
		''' get accessoire name from cache '''
		if cache is None:
			future = asyncio.run_coroutine_threadsafe(self._cache())
			cache = future.result()
			#cache=asyncio.get_event_loop().run_until_complete( self._cache() )
		if self.hueId in cache:
			return cache[self.hueId]['name']
		return None
		
	async def setState(self, prop='on', val='true', reskey='/state'):
		''' executes put request for changing some hue bridge property '''
		upd = self.last != val
		if upd:
			self.dtActive = datetime.now(timezone.utc)
			if val is None or prop is None:
				logger.warning('could not putState %s of %s to %s' % (prop,self.hueId,val))
			else:
				await hueSET(self.ipadr,self.user,prop,val,self.hueId,self.resource,reskey)
				logger.info('putState %s of %s to %s' % (prop,self.hueId,val))
			self.last=val
		else:
			logger.debug('not updating hueId %s val=%s' % (self.hueId,val))
		return upd
	
	def setValue(self, prop=None, val=None):
		''' high level property setter assuming Si units '''
		return asyncio.create_task(self.setState(prop,val))
		
	async def touchlink():
		# https://devotics.fr/ikea-tradfri-et-installation-hue/
		#pst = requests.post('https://'+ipadr+'/api/', data='{"%s":%s}' % ('touchlink','true'),verify=False)
		#return pst.json()
		#Perform a touchlink action if set to true, setting to false is ignored. When set to true a touchlink procedure starts which adds the closest lamp (within range) to the ZigBee network.  You can then search for new lights and lamp will show up in the bridge.  This field is Write-Only so it is not visible when retrieving the bridge Config JSON.
		return await setState('touchlink','true',reskey='/config')

	async def deleteProperty(self, reskey, resource='config/whitelist'):
		''' removes some property from hue bridge '''
		logger.warning('deleting %s from %s' % (reskey,resource))
		if len(reskey)>0 and len(resource)>0:
			async with aiohttp.ClientSession() as session:
				await session.delete('https://%s/api/%s' % (self.ipadr,self.user) +resource+'/'+reskey, ssl=True)

class HueSensor (HueBaseDev):
	''' class representing one sensor value on hue bridge '''
	_sensors = {}  # cache (static)
	_lastread = {} # time of cache refresh
	def __init__(self,hueId,ipadr,userid,semaphore=None):
		''' setup hue sensor. hueId must be one of ids on bridge. '''
		super().__init__(hueId,'sensors',ipadr,userid,semaphore=semaphore) # defines deCONZ
		self.refreshInterval=UPDATEINTERVAL
		self.prop=None  # unknown type yet
		if HueSensor._sensors:
			name = HueSensor._sensors[self.ipadr][self.hueId]['name'] 
			logger.info('%s Sensor %s %s for %s' % (self.devDescr,hueId,name,userid))
			
	async def name(self):
		''' get name from actual cache '''
		return super().name(cache=HueSensor._sensors[self.ipadr])
		
	async def _cache(self, setval=None):
		''' get or set_local cache. cache will be refreshed from bridge automatically if too old i.e. > self.refreshInterval '''
		if setval:
			HueSensor._sensors[self.ipadr] = setval
		else:
			tpast = datetime.now(timezone.utc) - HueSensor._lastread[self.ipadr]
			if tpast > timedelta(seconds=self.refreshInterval):
				logger.info('%s update Sens cache tpast:%s > %s' % (self.devDescr, tpast,self.refreshInterval))
				HueSensor._lastread[self.ipadr] = datetime.now(timezone.utc)
				HueSensor._sensors[self.ipadr]= await self.hueGET(self.resource) 
				if HueSensor._sensors:
					if not self.prop:
						state = await self.state()
						if state and 'status' not in state:
							#typ = getTyp(state)
							self.prop = next(prp for prp in SENSTYPES if prp in state)
							name = HueSensor._sensors[self.ipadr][self.hueId]['name'] 
							typ = SENSTYPES[self.prop] if self.prop in SENSTYPES else None
							logger.info('new sensor %s:prop=%s:name=%s:typ=%s:tpast=%s' % (self.hueId,self.prop,name,typ,tpast))
						else:
							logger.warning('no state for sensor %s : %s' % (self.hueId,state))
					logger.debug('sensorCache: %s last:%s len:%d, prop:%s' % (self.resource,HueSensor._lastread,len(HueSensor._sensors[self.ipadr]),self.prop))
				#HueSensor._lastread = datetime.now(timezone.utc)
			else:
				pass
				#logger.debug('tpast %s' % tpast)
		return HueSensor._sensors[self.ipadr]
			
	async def lastupdate(self):
		''' last time the self.prop value was updated on the hue bridge'''
		ddlast = await self.state('lastupdated')
		if ddlast and ddlast[:4] != 'none':
			if '.' not in ddlast:
				ddlast += '.0'  # add milli sec for hue
			try:
				dtm = datetime.strptime(ddlast+'+0000', "%Y-%m-%dT%H:%M:%S.%f%z") # aware utc
			except Exception as ex:
				logger.warning(('deCONZ' if self.deCONZ else 'hue')+' bad datetime:%s' % ex)
				dtm = HueSensor._lastread[self.ipadr]
			#logger.debug('hueSensId(%s) lastupdated:%s' % (self.hueId,ddlast))
		else:
			dtm = datetime.now(timezone.utc)
		#dtm.replace(tzinfo = timezone.utc)
		#logger.debug('dt:%s act:%s' % (dtm.strftime("%Y-%m-%d %H:%M:%S %Z"),self.dtActive.strftime("%H:%M:%S")))
		return dtm
			 
	async def value(self):
		''' get self.prop value converted to proper units '''
		val = await super().value()
		if val is None:
			logger.info('%s no val with %s' % (self.hueId,self.prop))
			return val
		else:
			if self.prop is None:
				self.prop = next(typ for typ in SENSTYPES if typ in val)
				val1 = await self.state(prop=self.prop)
				if val1 is None:
					logger.warning('no event val for hueid:%s at prop:%s dev:%s val:%s' % (self.hueId,self.prop,self.devDescr,val))
					return None
				else:
					val=val1
			if self.prop in SCALERS:
				val /= SCALERS[self.prop]
			else:
				if self.prop=='temperature':
					val/=100.0
				elif self.prop=='lightlevel': # compute lux
					val /= 10000.0
					val = math.pow(10.0,val)
					val = round(val,2)
				elif self.prop=='buttonevent':
					if val>=1000:
						typ = val % 100
						val /= 1000
					elif val>15:
						val = [34,16,17,18].index(val)
				elif self.prop=='presence':
					pass
				else:
					logger.error('(%s) unknown prop:%s val:%s' % (self.hueId,self.prop,val))
		return val
		
	@staticmethod
	def devTypes(ipadr,user,types=SENSTYPES):
		''' get  list of available sensor types from HUE or deCONZ bridge '''
		if HueSensor._sensors is None or ipadr not in HueSensor._sensors:
			HueSensor._sensors[ipadr] =st_hueGET(ipadr,user,'sensors')  # .json()
			logger.info('HueSensor_@:%s: %s' % (ipadr,HueSensor._sensors[ipadr]))
			HueSensor._lastread[ipadr] = datetime.now(timezone.utc)
		if len(HueSensor._sensors)>0:  # build dict of hueid:dat with type in dat
			lst = {hueid:set(dat['state'].keys()) & set(types) for hueid,dat in HueSensor._sensors[ipadr].items() if 'CLIP' not in dat['type']}
			logger.info('list of sensor types in hue bridge=%s, possible=%s' % (lst,set(types)))
			return {hueid:{**(HueSensor._sensors[ipadr][hueid]['state']), 'typ':next(tpid for tpnm,tpid in types.items() if tpnm in typ), 'name':HueSensor._sensors[ipadr][hueid]['name']} for hueid,typ in lst.items() if len(typ)>0}
		return {}

class HueLight(HueBaseDev):
	''' class representing 1 light on a hue bridge '''
	_lights = {} # all lights discovered on the bridge
	_lastread = {}
	def __init__(self,hueId,ipadr,userid,semaphore=None):
		super().__init__(hueId,'lights',ipadr=ipadr,userid=userid,semaphore=semaphore)
		self.refreshInterval=UPDATEINTERVAL*10
		self.prop = 'bri'
		if HueLight._lights:
			name = HueLight._lights[self.ipadr][self.hueId]['name'] 
			logger.info('HueLight %s %s for %s' % (hueId,name,len(self.user)))
			
		#self.gammut = self.hueGET(r'lights/%s/capabilities/control/colorgammut' % hueId)
		#self.gamut = self.gamut() #HueLight.gammut(cache, hueid) # cache[hueId]['capabilities']['control']
		#logger.info("huelight:%s with gammut:%s" % (hueId,self.gamut))

	async def _cache(self, setval=None):
		if setval:
			HueLight._lights[self.ipadr] = setval
		else:
			tpast = datetime.now(timezone.utc) - HueLight._lastread[self.ipadr]
			if self.ipadr not in HueLight._lights or tpast > timedelta(seconds=self.refreshInterval):
				logger.info("upd lights cache? if tpast=%s > %s; last=%s" % (tpast,timedelta(seconds=self.refreshInterval),HueLight._lastread[self.ipadr])) 
				HueLight._lastread[self.ipadr] = datetime.now(timezone.utc)
				HueLight._lights[self.ipadr] = await self.hueGET(self.resource) 
		return HueLight._lights[self.ipadr]
		
	async def name(self):
		return super().name(cache=HueLight._lights[self.ipadr])
		
	async def newval(self, minChangeInterval=300):
		''' checks whether self.prop value has been changed
			only provokes update when last activity has been some time (minChangeInterval) ago '''	
		#return False
		cach = await self._cache()
		trun = datetime.now(timezone.utc) - HueLight._lastread[self.ipadr]
		return  trun > timedelta(minChangeInterval)
	
	async def value(self, prop=None):
		''' get self.prop value converted to proper units bri,sat:% hue:deg ct:K'''
		if prop:
			self.prop=prop
		val = await super().value()
		if val is None:
			logger.info('%s no val with %s' % (self.hueId,self.prop))
			return val
		elif self.prop=='on':
			return val == 'true'
		elif self.prop=='bri':
			return val/2.54
		elif self.prop=='ct':
			return 100000/val
		elif self.prop=='xy':
			return val
		elif self.prop=='hue':
			return val*360/65535
		elif self.prop=='sat':
			return val/2.54
			
	def setValue(self, prop='on', val='true', loop=None):
		''' executes put request for changing some hue bridge property in Si like units '''
		if prop=='on':
			if val and val!='false':
				val='true'
			else:
				val='false'
		elif prop=='bri':
			val = int(val*2.54)
		elif prop=='ct':
			val = int(1000000/val)
		elif prop=='xy':
			tuple(val)
		elif prop=='hue':
			val = int(val*65535/360)
		elif prop=='sat':
			val = int(val*2.54)
		return super().setValue(prop,val)
		#global _loop
		if loop is None:
			loop = asyncio.get_event_loop()
			return loop.run_until_complete(self.setState(prop,val))
		else:
			return asyncio.create_task(self.setState(prop,val))  # only with running loop
		#return loop.run_until_complete( self.setState(prop,val))
	
	def lightTyp(cache, hueid, types=LIGHTTYPES):
		if hueid in cache:
			dev = cache[hueid]
			return types.index(dev['type'])
	
	#@staticmethod
	def gamut(self):  #ipadr, hueId):
		if HueLight._lights and self.hueId in HueLight._lights[self.ipadr]:
			if self.deCONZ:
				dev = HueLight._lights[self.ipadr][self.hueId]
				logger.debug('deCONZ gamut dev:%s:' % dev)
				return dev['state']
			else:
				dev = HueLight._lights[self.ipadr][self.hueId]['capabilities']['control']  # not for deCONZ
				if 'colorgamut' in dev:
					return dev['colorgamut']	# [[0.6915, 0.3083], [0.17, 0.7], [0.1532, 0.0475]]
				elif 'ct' in dev:
					return dev['ct']	# {'min': 153, 'max': 454}
				elif 'mindimlevel' in dev:
					return dev['mindimlevel']
			return None

	@staticmethod
	def devTypes(ipadr,user,types=LIGHTTYPES):
		#cache = st_hueGET(ipadr,user,'lights')  #.json()
		if HueLight._lights is None or ipadr not in HueLight._lights:
			HueLight._lastread[ipadr] = datetime.now(timezone.utc)
			HueLight._lights[ipadr] =st_hueGET(ipadr,user,'lights')   #.json()
			logger.info('HueLight_@ %s : %s' % (ipadr,HueLight._lights[ipadr]))
		return HueLight._lights[ipadr]
		
		lst = {hueid:{'typ':types.index(dev['type']),'name':dev['name'],**dev['state']} for hueid,dev in HueLight._lights[ipadr].items() if 'CLIP' not in dev['type']}
		logger.info("list of hue lights:%s" % lst)
		return lst
	
async def tst_sensors(sensors):
	#r = requests.get(basurl('config'),verify=False)
	#print('config:\n%s' % r.text)
		
	dev=None
	for adr in sorted(sensors, key=lambda x: int(x)):
		rec=sensors[adr]
		sens = HueSensor(adr,ipadr,user)
		logger.info("sns %s:nm=%s rec=%s" % (adr,rec['name'],rec))
		if rec['name'] in UPDNMS:
			dev = rec['name']
		if dev and rec['typ'] in UPDNMS[dev]:
			nm = rec['name']
			due = UPDNMS[dev][rec['typ']]
			UPDNMS[dev].pop(rec['typ'])
			if nm!=due:
				logger.warning("setting hue %s to %s on %s" % (nm,due,dev))
				await sens.setState('name', '"%s"' % due, reskey='')  #'"%s"' % due)
	
	#logger.info('all:%s' % hueGET(''))

	#sens = HueSensor('6',ipadr,user)
	#sens.setState('name','"KeukLux"','')
	#print('sens%s:%s' % (sens.hueId,sens.state()))
	#print('temp %s upd:%s' % (sens.value(),sens.lastupdate()))

	#illum = sensors['8']  #HueSensor('8',ipadr,user)
	#illum.setState('name','"DeurLux"','')
	#logger.info('sens8:%s' % await illum.state())
	#logger.info('illum %s upd:%s' % (illum.value(),illum.lastupdate()))

async def tst_light(lmp):
	asyncio.sleep(1)
	lmp.setValue('on')
	lmp.setValue('ct',3000)
	lmp.setValue('bri',30)
	logger.info('lmp4:%s' % await lmp.state())
	await lmp.setState('sat',4)
	#lmp.setState('effect','"colorloop"')
	await asyncio.sleep(5)
	lmp.setValue('on', False)
	
async def tst_webSock(ipadr,user):
	logger.info('testing on webSocket ')
	for i in range(8):
		msg = await webSocket(ipadr,user)
		if msg:
			#rec = await ws.receive()
			#await ws.close()
			logger.info('webSock %d rec:%s' % (i,msg))
			#ws.close()
		await asyncio.sleep(2)
		
async def main(ipadr,user,sensors,lmp):
	await asyncio.gather(* [tst_sensors(sensors), tst_light(lmp), tst_webSock(ipadr,user)])
	
if __name__ == '__main__':	# just testing the API and gets userId if neccesary
	#from lib import tls
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	
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
		"hueuser": secret.keyDECONZ,
		"huebridge": "192.168.44.20"
		#"hueuser":  secret.keySIGNIFY,
		#"huebridge": "192.168.44.21"
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

	sns = st_hueGET(ipadr,user=user, resource='sensors')
	if not sns:  # or sns.status != 200:
		logger.info('could not get sensors from %s (%s) with user %s' % (ipadr,sns,user))
		input("creating user?")
		#user = asyncio.create_task(createUser('homekit','fshome',ipadr=ipadr))
		print("press Authenticate button in Phoscon-GW app ")
		user =  _loop.run_until_complete(createUser('homekit','fshome',ipadr=ipadr,deCONZ=True))
		print('put hueuser in the secret.py file:\n%s' % user[0])
		breakpoint()
	else:
		logger.info("sensors:{}".format(sns))
		for adr,rec in sns[0].items():
			logger.info("rsns %s:%s" % (adr,rec))
			
		#asyncio.create_task(tst_webSock(ipadr,user))
			
		sensors = HueSensor.devTypes(ipadr,user)
		lights = HueLight.devTypes(ipadr,user)
		
		#_loop.run_until_complete(tst_sensors(sensors))
		
		for adr in sorted(lights, key=lambda x: int(x)):
			rec=lights[adr]
			logger.info("ligt %s: rec=%s" % (adr,lights[adr]))

		lmpid = '2' if len(user) <20 else '4'
		lmp = HueLight(lmpid,ipadr,user)
		gamut = lmp.gamut()
		#_loop.run_until_complete(tst_light(lmp))
	
		whitelist = _loop.run_until_complete(lmp.hueGET('config'))['whitelist']
		logger.info("wl:%s" % whitelist)
		
		#_loop.create_task
		_loop.run_until_complete(main(ipadr,user,sensors,lmp))
		#_loop.run_forever()
		#sens.deleteProperty('M4Ga2aj9VIYP7OFIMlgxfuXzkrjRkoBkdoR5SO7-')
		#logger.info('lights lst:\n%s' % lights)
		input("bye")

	#requests.put(basurl()+ '/lights/3/state', data='{"on":false}',verify=False)
	
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program