
import requests
import math
import time,os
from datetime import datetime,timedelta,timezone
import logging

conf={	# defaults when not in config file
	"hueuser": "iDBZ985sgFNMJruzFjCQzK-zYZnwcUCpd7wRoCVM",
	"huebridge": "192.168.1.21"
	}
	
RESOURCES = ['lights','sensors','whitelist','groups','locations','config', 'scenes','schedules','resourcelinks','rules']
# mapping hue quantity to DEVT 
SENSTYPES = {'temperature':0,'lightlevel':5,'buttonevent':12,'presence':11}
LIGHTTYPES = ['On/off light','Dimmable light','Extended color light','Color temperature light']

UPDATEINTERVAL=15

def basurl(user=None,ipadr=None):
	if user is None:
		user=list(conf['hueuser'].values())[0]
	if ipadr is None:
		ipadr = conf['huebridge']
	return 'https://'+ipadr+'/api/'+user

def hueGET(ipadr,user='',resource='',timeout=2):
	''' get state info from hue bridge '''
	url='https://'+ipadr+'/api/'
	if len(user)>0:
		url += user+'/'
	if len(resource)>0:
		url += resource
	try:
		r = requests.get(url, verify=False, timeout=timeout)
	except requests.exceptions.Timeout:
		logger.warning('hueGET failed with %s for %s' % (resource,ipadr))
		r = None
	#logger.debug('hueGET resource:%s with %s ret:%d' % (resource,r.url,r.status_code))
	return r

def createUser(devname,appname,devtype,ipadr=None):
	''' create user on hue bridge '''
	if ipadr is None:
		ipadr = ipadrGET()
	logger.critical('please press button on hue bridge within 30s')
	time.sleep(30)
	pst = requests.post('https://'+ipadr+'/api/', data='{"%s":"%s#%s"}' % (devtype,appname,devname),verify=false)
	logger.warning('newuser:%s' % (pst.json()))
	return pst.json()

def ipadrGET(bridgeName=None, portal='https://discovery.meethue.com/'):
	''' finds ip adres of hue bridge on LAN '''
	r = requests.get(portal)
	logger.info('hue bridge ip request:%s' % r.json())
	for user in r.json():  #[1:]:
		adr = user['internalipaddress']
		try:
			r = hueGET(adr, timeout=0.1)  # requests.get('http://'+adr,verify=False,timeout=0.1)
		except requests.ConnectionError:
			continue
		if r.status_code == 200:
			cnf =  hueGET(adr,resource='config') # requests.get('https://%s/api/config' % adr,verify=False)
			if cnf:
				logger.info('config:%s' % cnf.json())
				if bridgeName is None or bridgeName == cnf['name']:
					return adr
	return None


class HueBaseDev (object):
	''' base class for a hue bridge characteristic '''
	def __init__(self,hueId,resource,userid,ipadr):
		self.hueId = hueId
		self.resource = resource
		self.user=userid
		self.ipadr=ipadr
		self.dtActive = datetime.now(timezone.utc)
		self.last=None
		
	def hueGET(self,resource):
		''' get state info from hue bridge '''
		r = hueGET(self.ipadr, self.user, resource)
		self.life=0
		if r is None:
			return {}
		logger.debug('hueGET resource:%s with %s ret:%d at %s' % (resource,r.url,r.status_code,datetime.now()))
		return r.json()
		
	def refresh(self):
		self._cache(self.hueGET(self.resource))
		logger.debug('refreshing %s len=%d' % (self.resource,len(self._cache())))
		
	def state(self, prop=None, reskey='state'):
		''' fetch state info from local cache (cache will be refreshed if too old) '''
		cache= self._cache()
		if self.hueId in cache:
			if prop is None:
				return cache[self.hueId][reskey]
			return cache[self.hueId][reskey][prop]
		else:
			logger.warning('hueid %s not in cache %s' % (self.hueId,prop))
		return None
		
	def name(self):
		''' get accessoire name from cache '''
		cache= self._cache()
		if self.hueId in cache:
			return cache[self.hueId]['name']
		return None
		
	def setState(self, prop='on', val='true', reskey='state'):
		''' executes put request for changing some hue bridge property '''
		if self.last != val:
			self.dtActive = datetime.now(timezone.utc)
		logger.info('setting %s of %s to %s' % (prop,self.hueId,val))
		requests.put('https://%s/api/%s' % (self.ipadr,self.user) + '/%s/%s/%s' % (self.resource,self.hueId,reskey), data='{"%s":%s}' % (prop,val),verify=False)
		self.last=val
	
	def deleteProperty(self, reskey, resource='config/whitelist'):
		''' removes some property from hue bridge '''
		logger.warning('deleting %s from %s' % (reskey,resource))
		if len(reskey)>0 and len(resource)>0:
			requests.delete('https://%s/api/%s' % (self.ipadr,self.user) +resource+'/'+reskey, verify=False)
			
	def lastupdate(self):
		''' to be overriden by ancesters to return real time updated '''
		return self.dtActive
			
	def newval(self, minChangeInterval=0):
		''' checks whether self.prop value has been updated '''
		val =self.state(prop=self.prop)
		if val is not None:
			return self.lastupdate()-self.dtActive >= timedelta(seconds=minChangeInterval) and (val != self.last)
			#return self.lastupdate()<datetime.now(timezone.utc)-timedelta(minutes=1) and 
			#return (self.last is None or val != self.last)
		logger.warning('no prop %s in state %s' % (self.prop,val))
		return None
		
	def value(self):
		''' get last self.prop value from cache '''
		self.dtActive=self.lastupdate()
		self.last = self.state(prop=self.prop)
		return self.last
		
class HueSensor (HueBaseDev):
	''' class representing one sensor value on hue bridge '''
	_sensors = None  # cache (static)
	_lastread = None # time of cache refresh
	def __init__(self,hueId,conf=conf):
		''' setup hue sensor. hueId must be one of ids on bridge. '''
		super().__init__(hueId,'sensors',userid=conf['hueuser'],ipadr=conf['huebridge'])
		state = self.state()
		if len(state)>0:
			self.prop = next(typ for typ in SENSTYPES if typ in state)
			logger.info('%s state=%s typ=%s nm=%s' % (self.hueId,state,self.prop,self.name()))
		else:
			logger.error('unknown hue device: %s' % hueId)
			self.prop=None
		
	def _cache(self, setval=None, refreshInterval=UPDATEINTERVAL):
		''' get or set_local cache. cache will be refreshed from bridge automatically if too old'''
		if setval:
			HueSensor._sensors = setval
		else:
			tpast = datetime.now() - HueSensor._lastread
			if tpast > timedelta(seconds=refreshInterval):
				HueSensor._sensors =self.hueGET(self.resource)
				if HueSensor._sensors:
					logger.debug('received %s last:%s life:%d len:%d, prop:%s' % (self.resource,HueSensor._lastread,self.life,len(HueSensor._sensors),self.prop))
				self.life=0
				HueSensor._lastread = datetime.now()
			else:
				pass
				#logger.debug('tpast %s' % tpast)
		return HueSensor._sensors
			
	def lastupdate(self):
		''' last time the self.prop value was updated on the hue bridge'''
		ddlast = self.state('lastupdated')
		dtm = datetime.strptime(ddlast+'+0000', "%Y-%m-%dT%H:%M:%S%z") # aware utc
		#dtm.replace(tzinfo = timezone.utc)
		logger.debug('dt:%s' % dtm.strftime("%Y-%m-%d %H:%M:%S %Z"))
		return dtm
			
	def value(self):
		''' get self.prop value converted to proper units '''
		val = super().value()
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
			HueSensor._sensors =hueGET(ipadr,user,'sensors').json()
			HueSensor._lastread = datetime.now()
		lst = {id:set(state['state'].keys()) & set(types) for id,state in HueSensor._sensors.items() if 'CLIP' not in state['type']}
		logger.info('list of types in bridge=%s, possible=%s' % (lst,set(types)))
		return {id:{**(HueSensor._sensors[id]['state']), 'typ':list(typ)[0], 'name':HueSensor._sensors[id]['name']} for id,typ in lst.items() if len(typ)>0}

class HueLight(HueBaseDev):
	_lights = None
	def __init__(self,hueId='6',conf=conf):
		super().__init__(hueId,'lights',userid=conf['hueuser'],ipadr=conf['huebridge'])
		self.prop = 'bri'

	def _cache(self, setval=None):
		if setval:
			HueLight._lights = setval
		if HueLight._lights is None:
			HueLight._lights = self.hueGET(self.resource)
		return HueLight._lights
		
	@staticmethod
	def devTypes(types=LIGHTTYPES):
		lst = {id:{'typ':dev['type'],'name':dev['name'],**dev['state']} for id,dev in HueLight._lights.items() if 'CLIP' not in dev['type']}
		return lst
			
if __name__ == '__main__':
	logger = logging.getLogger()
	[logger.removeHandler(h) for h in logger.handlers[::-1]] # handlers persist between calls
	logger.addHandler(logging.StreamHandler())	# use console
	logger.addHandler(logging.FileHandler(filename=os.path.expanduser('~/hueApi.log'), mode='w', encoding='utf-8')) #details to log file
	logger.setLevel(logging.DEBUG)
	logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S%z")))
	conf['huebridge'] =ipadrGET()
	
	from requests.packages.urllib3.exceptions import InsecureRequestWarning
	requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
	
	#r = requests.get(basurl('config'),verify=False)
	#print('config:\n%s' % r.text)
	print('sensors lst:\n%s' % HueSensor.devTypes(ipadr=conf['huebridge'],user=conf['hueuser']))

	#logger.info('all:%s' % hueGET(''))

	sens = HueSensor('6')
	#sens.setState('name','"KeukLux"','')
	print('sens%s:%s' % (sens.hueId,sens.state()))
	print('temp %s upd:%s' % (sens.value(),sens.lastupdate()))
	
	illum = HueSensor('8')
	#illum.setState('name','"DeurLux"','')
	print('sens8:%s' % illum.state())
	print('illum %s upd:%s' % (illum.value(),illum.lastupdate()))
	
	lmp = HueLight('3')
	print('lmp3:%s' % lmp.state())
	lmp.setState('sat',200)
	#lmp.setState('effect','"colorloop"')
	
	#sensors =hueGET('sensors')
	#print('Sensors\n:%s' % sensors)
	whitelist = sens.hueGET('config')['whitelist']
	logger.info("wl:%s" % whitelist)
	sens.deleteProperty('M4Ga2aj9VIYP7OFIMlgxfuXzkrjRkoBkdoR5SO7-')
	logger.info('lights lst:\n%s' % HueLight.devTypes())

	#requests.put(basurl()+ '/lights/3/state', data='{"on":false}',verify=False)
	
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
