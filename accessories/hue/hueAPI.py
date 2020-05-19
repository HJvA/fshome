#!/usr/bin/env python3.5
""" Philips / Signify HUE Application Programming Interface
	allows a user app to read sensors and set actors on the Hue bridge.
	Will create user id first time (press button on hue bridge) to be copied to conf file
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
LIGHTTYPES = ['On/off light','Dimmable light','Extended color light','Color temperature light']

UPDATEINTERVAL=15

async def hueGET(ipadr,user='',resource='',timeout=2):
	''' get state info from hue bridge '''
	stuff=None
	url='https://'+ipadr+'/api/'
	if len(user)>0:
		url += user+'/'
	if len(resource)>0:
		url += resource
	#auth = aiohttp.BasicAuth(user, pwd)
	try:
		async with aiohttp.ClientSession() as session:
			async with session.get( url=url, timeout=timeout, ssl=True) as response:
				try:
					stuff = await response.json()
				except aiohttp.client_exceptions.ContentTypeError as ex:
					stuff = await response.text()
	except Exception as e:
		logger.exception("unknown exception!!! %s" % e)
	#logger.debug('hueGET resource:%s with %s ret:%d' % (resource,r.url,r.status_code))
	return stuff

_loop = None
def st_hueGET(ipadr,user='',resource='',timeout=2):
	_loop = asyncio.get_event_loop()
	ret = _loop.run_until_complete( hueGET(ipadr,user, resource,timeout))
	if ret:
		#logger.info('static hueGET %s' % ret)
		return ret
	return {}

async def hueSET(ipadr,user,prop,val,hueId,resource,reskey='/state'):
	url='http://'+ipadr+'/api/'
	if len(user)>0:
		url += user+'/'
	if len(resource)>0:
		url += resource+'/'
	url += '%s%s' % (hueId,reskey)
	logger.info('hueSET:"%s":%s on %s' % (prop,val,url))
	async with aiohttp.ClientSession() as session:
		await session.put(url, data='{"%s":%s}' % (prop,val), ssl=False)
		pass

def createUser(devname,appname,ipadr=None):
	''' create user on hue bridge '''
	if ipadr is None:
		_loop = asyncio.get_event_loop()
		ipadr = _loop.run_until_complete(ipadrGET())
	logger.critical('please press button on hue bridge within 30s')
	time.sleep(30)
	pst = requests.post('https://'+ipadr+'/api/', data='{"%s":"%s#%s"}' % ('devicetype',appname,devname),verify=False)
	logger.warning('newuser:%s' % (pst.json()))
	return pst.json()
	

async def ipadrGET(bridgeName=None, portal='https://discovery.meethue.com/'):
	''' finds ip adres of hue bridge on LAN '''
	
	async with aiohttp.ClientSession() as session:
			async with session.get( url=portal, ssl=True) as response:
				stuff = await response.json()
	
	#r = requests.get(portal)
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


class HueBaseDev (object):
	''' base class for a hue bridge characteristic '''
	def __init__(self,hueId,resource,ipadr,userid):
		''' hueId : Id of hue characteristic on hue bridge
			resource : 'sensors' or 'lights'
		'''
		self.hueId = hueId
		self.resource = resource
		self.user=userid
		self.ipadr=ipadr
		self.dtActive = datetime.now(timezone.utc)
		self.last=None
		#urllib.disable_warnings(InsecureRequestWarning)

		
	async def hueGET(self,resource):
		''' get state info from hue bridge '''
		r = await hueGET(self.ipadr, self.user, resource)
		self.life=0
		if r is None:
			return {}
		#logger.debug('hueGET resource:%s with %s ret:%d at %s' % (resource,r.url,r.status_code,datetime.now()))
		return r
		
	async def refresh(self):
		self._cache(await self.hueGET(self.resource))
		logger.debug('refreshing %s len=%d' % (self.resource,len(self._cache())))
		
		
	async def state(self, prop=None, reskey='state'):
		''' fetch state info from local cache (cache will be refreshed if too old) '''
		cache = await self._cache()
		if self.hueId in cache:
			if prop is None:
				return cache[self.hueId][reskey]
			elif reskey in cache[self.hueId] and prop in cache[self.hueId][reskey]:
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
		dtm = await self.lastupdate()
		if dtm-self.dtActive >= timedelta(seconds=minChangeInterval):
			val =await self.state(prop=self.prop)
			if val is not None:
				return (val != self.last)
			logger.debug('no prop %s in state %s' % (self.prop,val))
		else:
			await asyncio.sleep(0.1)
		return False

	async def value(self):
		''' get last self.prop value from cache '''
		self.dtActive = await self.lastupdate()	# mark using as activity
		self.last = await self.state(prop=self.prop)
		return self.last
	
	def name(self, cache=None):
		''' get accessoire name from cache '''
		if cache is None:
			cache=asyncio.get_event_loop().run_until_complete( self._cache() )
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
	_sensors = None  # cache (static)
	_lastread = None # time of cache refresh
	def __init__(self,hueId,ipadr,userid):
		''' setup hue sensor. hueId must be one of ids on bridge. '''
		super().__init__(hueId,'sensors',ipadr,userid)
		self.refreshInterval=UPDATEINTERVAL
		global _loop
		if not _loop:
			_loop = asyncio.get_event_loop()
		state = _loop.run_until_complete(self.state())
		if state and not 'status' in state:
			self.prop = next(typ for typ in SENSTYPES if typ in state)
			logger.info('%s state=%s typ=%s nm=%s' % (self.hueId,state,self.prop,self.name()))
		else:
			logger.error('unknown hue device: %s' % hueId)
			self.prop=None
			
	async def name(self):
		''' get name from actual cache '''
		return super().name(cache=HueSensor._sensors)
		
	async def _cache(self, setval=None):
		''' get or set_local cache. cache will be refreshed from bridge automatically if too old i.e. > self.refreshInterval '''
		if setval:
			HueSensor._sensors = setval
		else:
			tpast = datetime.now(timezone.utc) - HueSensor._lastread
			if tpast > timedelta(seconds=self.refreshInterval):
				HueSensor._sensors = await self.hueGET(self.resource)
				if HueSensor._sensors:
					logger.debug('sensorCache: %s last:%s life:%d len:%d, prop:%s' % (self.resource,HueSensor._lastread,self.life,len(HueSensor._sensors),self.prop))
				self.life=0
				HueSensor._lastread = datetime.now(timezone.utc)
			else:
				pass
				#logger.debug('tpast %s' % tpast)
		return HueSensor._sensors
			
	async def lastupdate(self):
		''' last time the self.prop value was updated on the hue bridge'''
		ddlast = await self.state('lastupdated')
		if ddlast and ddlast[:4] != 'none':
			#dtm = HueSensor._lastread
			dtm = datetime.strptime(ddlast+'+0000', "%Y-%m-%dT%H:%M:%S%z") # aware utc
			logger.debug('hue(%s) ddlast:%s' % (self.hueId,ddlast))
		else:
			return datetime.now(timezone.utc)
		#dtm.replace(tzinfo = timezone.utc)
		#logger.debug('dt:%s act:%s' % (dtm.strftime("%Y-%m-%d %H:%M:%S %Z"),self.dtActive.strftime("%H:%M:%S")))
		return dtm
			 
	async def value(self):
		''' get self.prop value converted to proper units '''
		val = await super().value()
		if val is None:
			logger.info('%s no val with %s' % (self.hueId,self.prop))
			return val
		elif self.prop=='temperature':
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
			logger.error('unknown prop:%s val:%s' % (self.prop,val))
		return val
		
	@staticmethod
	def devTypes(ipadr,user,types=SENSTYPES):
		''' get  list of available sensor types from hue bridge '''
		if HueSensor._sensors is None:
			HueSensor._sensors =st_hueGET(ipadr,user,'sensors')  # .json()
			HueSensor._lastread = datetime.now(timezone.utc)
		if len(HueSensor._sensors)>0:
			lst = {hueid:set(dat['state'].keys()) & set(types) for hueid,dat in HueSensor._sensors.items() if 'CLIP' not in dat['type']}
			logger.info('list of sensor types in hue bridge=%s, possible=%s' % (lst,set(types)))
			return {hueid:{**(HueSensor._sensors[hueid]['state']), 'typ':next(tpid for tpnm,tpid in types.items() if tpnm in typ), 'name':HueSensor._sensors[hueid]['name']} for hueid,typ in lst.items() if len(typ)>0}
		return {}


class HueLight(HueBaseDev):
	''' class representing 1 light on a hue bridge '''
	_lights = None # all lights discovered on the bridge
	_lastread = None
	def __init__(self,hueId,gamut,ipadr,userid):
		super().__init__(hueId,'lights',ipadr=ipadr,userid=userid)
		self.refreshInterval=UPDATEINTERVAL*10
		self.prop = 'bri'
		#self.gammut = self.hueGET(r'lights/%s/capabilities/control/colorgammut' % hueId)
		self.gamut = gamut #HueLight.gammut(cache, hueid) # cache[hueId]['capabilities']['control']
		#logger.info("huelight:%s with gammut:%s" % (hueId,self.gamut))

	async def _cache(self, setval=None):
		if setval:
			HueLight._lights = setval
		else:
			tpast = datetime.now(timezone.utc) - HueLight._lastread
			logger.debug("lights refresh in trun=%s last=%s interv=%s" % (tpast,HueLight._lastread,timedelta(seconds=self.refreshInterval))) # - timedelta(seconds=self.refreshInterval))
			if HueLight._lights is None or tpast > timedelta(seconds=self.refreshInterval):
				HueLight._lights =await self.hueGET(self.resource) #_loop.run_until_complete()
				HueLight._lastread = datetime.now(timezone.utc)
		return HueLight._lights
		
	async def name(self):
		return super().name(cache=HueLight._lights)
		
	async def newval(self, minChangeInterval=300):
		''' checks whether self.prop value has been changed
			only provokes update when last activity has been some time (minChangeInterval) ago '''	
		#return False
		cach = await self._cache()
		trun = datetime.now(timezone.utc) - HueLight._lastread
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
		return asyncio.create_task(self.setState(prop,val))
		#return loop.run_until_complete( self.setState(prop,val))
	
	def lightTyp(cache, hueid, types=LIGHTTYPES):
		if hueid in cache:
			dev = cache[hueid]
			return types.index(dev['type'])
	
	@staticmethod
	def gamut(hueid):
		if HueLight._lights and hueid in HueLight._lights:
			dev = HueLight._lights[hueid]['capabilities']['control']
			if 'colorgamut' in dev:
				return dev['colorgamut']	# [[0.6915, 0.3083], [0.17, 0.7], [0.1532, 0.0475]]
			elif 'ct' in dev:
				return dev['ct']	# {'min': 153, 'max': 454}
			elif 'mindimlevel' in dev:
				return dev['mindimlevel']
			return None

	@staticmethod
	def devTypes(ipadr,user,types=LIGHTTYPES):
		cache = st_hueGET(ipadr,user,'lights')  #.json()
		if HueLight._lights is None:
			HueLight._lastread = datetime.now(timezone.utc)
			HueLight._lights =st_hueGET(ipadr,user,'lights')   #.json()
		return cache
		lst = {hueid:{'typ':types.index(dev['type']),'name':dev['name'],**dev['state']} for hueid,dev in HueLight._lights.items() if 'CLIP' not in dev['type']}
		logger.info("list of hue lights:%s" % lst)
		return lst
			
if __name__ == '__main__':	# just testing the API and gets userId if neccesary
	#from lib import tls
	logger = logging.getLogger()
	[logger.removeHandler(h) for h in logger.handlers[::-1]] # handlers persist between calls
	logger.addHandler(logging.StreamHandler())	# use console
	logger.addHandler(logging.FileHandler(filename=os.path.expanduser('hueApi.log'), mode='w', encoding='utf-8')) #details to log file
	logger.setLevel(logging.DEBUG)
	logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S%z")))
	CONF={	# defaults when not in config file
		"hueuser": "RnJforsLMZqsCbQgl5Dryk9LaFvHjEGtXqcRwsel",
		"huebridge": "192.168.1.21"
	}
	#CONF['huebridge'] =ipadrGET()
	
	ipadr=CONF['huebridge']
	user=CONF['hueuser']
	
	#from urllib3.exceptions import InsecureRequestWarning
	#urllib3.disable_warnings(InsecureRequestWarning)

	
	lights = HueLight.devTypes(ipadr,user)
	
	UPDNMS = { "DeurMot":{0:"DeurTemp", 5:"DeurLux", 11:"DeurMot"},
			  "motMaroc":{0:"tempMaroc", 5:"luxMaroc", 11:"motMaroc"},
			  "keukMot":{0:"keukTemp", 5:"keukLux", 11:"keukMot"} }

	sns = st_hueGET(ipadr,user=user, resource='sensors')
	if not sns:  # or sns.status != 200:
		logger.info('could not get sensors from %s (%s) with user %s' % (ipadr,sns,user))
		user = createUser('homekit','fshome',ipadr=ipadr)
		print('put hueuser in the config file:\n%s' % user)
	else:
		for adr,rec in sns.items():
			logger.info("rsns %s:%s" % (adr,rec))
		#r = requests.get(basurl('config'),verify=False)
		#print('config:\n%s' % r.text)
		
		for adr in sorted(lights, key=lambda x: int(x)):
			rec=lights[adr]
			logger.info("ligt %s: rec=%s" % (adr,lights[adr]))
			
		sensors = HueSensor.devTypes(ipadr,user)
		dev=None
		for adr in sorted(sensors, key=lambda x: int(x)):
			rec=sensors[adr]
			sens = HueSensor(adr,ipadr,user)
			logger.info("sns %s:nm=%s rec=%s" % (adr,sens.name(),sensors[adr]))
			if rec['name'] in UPDNMS:
				dev = rec['name']
			if dev and rec['typ'] in UPDNMS[dev]:
				nm = rec['name']
				due = UPDNMS[dev][rec['typ']]
				UPDNMS[dev].pop(rec['typ'])
				if nm!=due:
					logger.warning("setting hue %s to %s on %s" % (nm,due,dev))
					_loop.run_until_complete(sens.setState('name', '"%s"' % due, reskey='') ) #'"%s"' % due)
		
		#logger.info('all:%s' % hueGET(''))

		#sens = HueSensor('6',ipadr,user)
		#sens.setState('name','"KeukLux"','')
		#print('sens%s:%s' % (sens.hueId,sens.state()))
		#print('temp %s upd:%s' % (sens.value(),sens.lastupdate()))
	
		illum = HueSensor('8',ipadr,user)
		#illum.setState('name','"DeurLux"','')
		logger.info('sens8:%s' % illum.state())
		logger.info('illum %s upd:%s' % (illum.value(),illum.lastupdate()))
		
		gamut = HueLight.gamut('4')
		lmp = HueLight('4',gamut,ipadr,user)
		lmp.setValue('on')
		lmp.setValue('ct',3000)
		lmp.setValue('bri',30)
		logger.info('lmp4:%s' % lmp.state())
		#lmp.setState('sat',4)
		#lmp.setState('effect','"colorloop"')
		lmp.setValue('on', False)
	
		whitelist = _loop.run_until_complete(sens.hueGET('config'))['whitelist']
		logger.info("wl:%s" % whitelist)
		#sens.deleteProperty('M4Ga2aj9VIYP7OFIMlgxfuXzkrjRkoBkdoR5SO7-')
		#logger.info('lights lst:\n%s' % lights)

	#requests.put(basurl()+ '/lights/3/state', data='{"on":false}',verify=False)
	
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program