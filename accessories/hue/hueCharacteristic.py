import asyncio
import sys,os,logging
from typing import Dict,Tuple,List,Any
from datetime import datetime
from enum import Enum

sys.path.append(os.getcwd()) # + '/..')
import submod.pyCommon.tls as tls
from lib.devConst import DEVT

from accessories.hue.hueAPIv2 import ChDat,getCharDat,ENDPOINTS,HueTyps, FindId, hueSET,hueGET,evListener, HueTyps

from enum import Enum

class Resource(Enum):
	light,scene,room,zone,bridge_home,grouped_light,device,bridge,device_power, zigbee_connectivity,zgp_connectivity,zigbee_device_discovery, motion,temperature,light_level,button, relative_rotary,behaviour_script,behaviour_instance, geofence_client,geolocation,entertainment_configuration,entertainment, homekit,matter,matter_fabric,smart_scene	= range(1, 28)

class hueBase():
	chDat:ChDat={}
	eventCallback = None
	def __init__(self, ipadr:str, appkey:str, debug=False):
		hueBase.ipadr = ipadr
		hueBase.appkey = appkey
		if not hueBase.chDat:
			 asyncio.ensure_future(hueBase._charLoad(hueBase.chDat) )
		#if evCallback:
		#	hueBase.eventCallback = evCallback
		#else:
		#	hueBase.eventCallback = hueBase.evCallback
		#if hueBase.eventCallback:
		#	logger.info("starting eventListener from {} in {}".format(self.__class__.__name__, self))
		#	asyncio.ensure_future(hueBase.eventListener(hueBase.eventCallback))
				
	@classmethod
	async def _charLoad(cls, chDat):
		chDat.update(await getCharDat(cls.ipadr, cls.appkey, endpoints=ENDPOINTS[:5]))
		
	@classmethod
	async def eventListener(cls, evCallback=None): #, ipadr:str, appkey:str, evCallback, chDat:ChDat):
		""" wait for events forever """
		if evCallback is None:
			evCallback = cls.eventCallback
		await evListener(cls.ipadr, cls.appkey, evCallback, cls.chDat)
		
	@classmethod
	async def create(cls, name, htyp:HueTyps = HueTyps.unknown):
		if htyp in [HueTyps.light, HueTyps.grouped_light]:
			return hueLight(name )
		else:
			if htyp==HueTyps.motion:
				return hueSensor(name, htyp.qTyp )
			elif htyp==HueTyps.temperature:
				return hueSensor(name, htyp.qTyp )
			elif htyp==HueTyps.button:
				return hueSensor(name, htyp.qTyp )
			elif htyp==HueTyps.light_level:
				return hueSensor(name, htyp.qTyp )
		logger.warning("unknown typ:{} to create {}".format(htyp, name))
		#return cls(name) # nc
	
	@classmethod
	def evCallback(cls, id:str, tm:datetime, name, val, htyp) -> Tuple[datetime,str,float,int]:
		""" default virtual only logging """ 
		logger.info("evCallback:{}->{} as:{} dd:{}".format(name,val,htyp,tm))
		return tm,name,val,htyp.qTyp

class hueLight(hueBase):
	def __init__(self, name, qtyp=DEVT['lamp']):
		self.id = FindId(name,qtyp, hueBase.chDat)
		self.resource = Resource.light.name
		#super.__init__()
		logger.info("light:{} = {}".format(name, self.id))
	def setOn(self, On=True):
		return asyncio.ensure_future(hueSET(hueBase.ipadr,hueBase.appkey, self.id, val=On, resource=self.resource, reskey='on', prop='on' ))
	def setBrightness(self, brightness=50):
		return asyncio.ensure_future(hueSET(hueBase.ipadr,hueBase.appkey, self.id, val=brightness,  resource=self.resource, reskey='dimming',prop='brightness' ))
	@property
	async def on(self):
		rec = await hueGET(hueBase.ipadr, hueBase.appkey, resource=self.resource, rid=self.id)
		logger.info("on-light={}".format(rec))
		return rec['data'][0]['on']['on']
	@on.setter
	def on(self, value):
		return self.setOn(value)
		#await hueSET(hueBase.ipadr,hueBase.appkey, self.id, val=value,  resource=Resource.light.name, reskey='on',prop='on' )
	@property
	async def brightness(self):
		rec = await hueGET(hueBase.ipadr, hueBase.appkey, resource=self.resource, rid=self.id)
		logger.info("bri-light={}".format(rec))
		return rec['data'][0]['dimming']['brightness']
	@brightness.setter
	def brightness(self, value):
		return self.setBrightness(value)
		#await hueSET(hueBase.ipadr,hueBase.appkey, self.id, val=value,  resource=Resource.light.name, reskey='dimming',prop='brightness' )
	@property
	async def color(self):
		rec = await hueGET(hueBase.ipadr, hueBase.appkey, resource=self.resource, rid=self.id)
		logger.info("col-light={}".format(rec))
		return rec['data'][0]['color']['xy']
	@color.setter
	def color(self, xy):
		asyncio.ensure_future(hueSET(hueBase.ipadr,hueBase.appkey, self.id, val=xy,  resource=self.resource, reskey='color',prop='xy' ))
	@property
	async def CCT(self):
		rec = await hueGET(hueBase.ipadr, hueBase.appkey, resource=self.resource, rid=self.id)
		logger.info("CCT-light={}".format(rec))
		mirek = rec['data'][0]['color_temperature']['mirek']
		if mirek:
			return 1000000/mirek
		logger.warning("mirek not valid? for {}".format(self.id))
	@CCT.setter
	def CCT(self, value):
		mirek = int(1000000/value)
		if mirek>500:
			mirek=500
		if mirek<153:
			mirek=153
		asyncio.ensure_future(hueSET(hueBase.ipadr,hueBase.appkey, self.id, val=mirek,  resource=self.resource, reskey='color_temperature',prop='mirek' ))
		
	
class hueSensor(hueBase):
	def __init__(self, name, qtyp=DEVT['temperature']):
		self.id = FindId(name,qtyp, hueBase.chDat)
		logger.info("sensor:{} = {} typ:{}".format(name, self.id, qtyp))
	async def getValue(self):
		return await hueGET(hueBase.ipadr,hueBase.appkey, resource=Resource.temperature.name, rid=self.id) #'{}'.format(self.id)))
	@property
	async def temperature(self):
		rec = await hueGET(hueBase.ipadr, hueBase.appkey, resource=Resource.temperature.name, rid=self.id)
		logger.info("temperature={}".format(rec))
		return rec['data'][0]['temperature']['temperature']
	@property
	async def light_level(self):
		rec = await hueGET(hueBase.ipadr, hueBase.appkey, resource=Resource.light_level.name, rid=self.id)
		logger.info("light_level={}".format(rec))
		return rec['data'][0]['light']['light_level']
	@property
	async def motion(self):
		rec = await hueGET(hueBase.ipadr, hueBase.appkey, resource=Resource.motion.name, rid=self.id)
		logger.info("motion={}".format(rec))
		#creatim = rec['creationtime']
		return rec['data'][0]['motion']['motion']
		
		

async def _main(ipadr,appkey):
	logger.info("testing hue on {} with {}".format(ipadr,appkey))
	huebs = hueBase(ipadr,appkey)
	await asyncio.sleep(10) # wait for chDat to be filled
	gradStrip = await hueLight.create("gradStrip", HueTyps.light)
	gradStaak = await hueLight.create("gradStaak", HueTyps.light)
	motZolM = await hueSensor.create("motZol", HueTyps.motion)
	motZolT = await hueSensor.create("motZol", HueTyps.temperature)
	#gradStaak.setOn(True)
	gradStaak.on = True
	gradStrip.on = True
	gradStrip.CCT = 4000
	lev = await gradStrip.brightness
	xy = await gradStrip.color
	CCT = await gradStaak.CCT
	logger.info("gradStrip bri={} xy={}".format(lev,xy))
	gradStrip.brightness=lev+20 #.setBrightness(lev+20)
	T = await motZolT.temperature
	M = await motZolM.motion
	logger.info("T:{} °C mot:{} CCT:{}K".format(T,M,CCT))
	await asyncio.sleep(300)
	gradStrip.CCT= 2000
	
	
if __name__ == '__main__':	# just testing the API and gets userId if neccesary
	logger = tls.get_logger(__file__, levelConsole=logging.INFO, levelLogfile=logging.DEBUG)
	
	import secret
	#logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S%z")))
	
	CONF={	# defaults when not in config file
		"hueuser":  secret.keySIGNIFY,
		"huebridge": "192.168.44.21"
	}
	
	ipadr=CONF['huebridge']
	user=CONF['hueuser']
	
	_loop = asyncio.get_event_loop()
	_loop.run_until_complete(_main(ipadr, user))
else:
	logger = tls.get_logger() #, levelConsole=logging.INFO, levelLogfile=logging.DEBUG)

