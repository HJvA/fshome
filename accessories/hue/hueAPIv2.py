#!/usr/bin/env python3.5
""" Philips / Signify HUE Application Programming Interface
	allows a user app to read sensors and set actors on the Hue bridge.
	Will create user id first time (press button on hue bridge) to be copied to conf file
	http://dresden-elektronik.github.io/deconz-rest-doc/
	https://developers.meethue.com/develop/get-started-2/
	"""

import asyncio, aiohttp #, functools

MDNS = 'meethue'
if MDNS:
	import requests
else:
	from http.client import HTTPSConnection

import math
import time,os,sys,json
from datetime import datetime,timedelta,timezone,date
from enum import Enum
from typing import Dict,Tuple,List,Any
import logging

sys.path.append(os.getcwd()) # + '/..')
import lib.tls as tls
from lib.devConst import DEVT
import lib.sse_client as sse

ChDat = Dict[str,Dict[str,Any]]

#UTCOFS = datetime.now().utcoffset()
UTCOFS = '+0100' # winter +0200 zomer
ENDPOINTS = ['bridge', 'device', 'light', 'motion', 'button', 'scene', 'room']
	
#RESOURCES = ['lights','sensors','whitelist','groups','locations','config', 'scenes','schedules','resourcelinks','rules']
# mapping hue quantity to DEVT 
#SENSTYPES = {'temperature':0,'lightlevel':5,'buttonevent':12,'presence':11}
#LIGHTTYPES = ['On/off light','Dimmable light','Extended color light','Color temperature light', 'On/Off plug-in unit']

class HueTyps(Enum): 
	light,grouped_light,scene,button, bridge,device,room,relative_rotary, bridge_home, \
	temperature,motion,light_level,device_power, zigbee_connectivity, \
	unknown	= range(1,16) 
	@property
	def qTyp(self):
		if self is HueTyps.light:
			return DEVT['lamp']
		#grouped_light: DEVT[''],
		#scene: DEVT[''],
		if self is HueTyps.button: 
			return DEVT['button']
		#bridge,device,room,relative_rotary, bridge_home, \
		if self is HueTyps.temperature: 
			return DEVT['temperature']
		if self is HueTyps.motion: 
			return DEVT['motion']
		if self is HueTyps.light_level: 
			return DEVT['illuminance']
		#device_power, zigbee_connectivity
		return DEVT['unknown']
	@classmethod
	def fromstr(cls, s):
		for en in cls:
			if en.name==s:
				return en
		return cls.unknown

HUETYP = {
	 HueTyps.light:{'prop':['dimming.brightness','on.on','color.xy.x', 'color.xy.y', 'color_temperature.mirek'], 'qtyp':DEVT['lamp']},
	 HueTyps.grouped_light:{'prop':['on.on','dimming.brightness'], 'qtyp':DEVT['unknown']},
	 HueTyps.temperature:{'prop':['temperature.temperature'], 'qtyp':DEVT['temperature']},
	 HueTyps.motion:{'prop':['motion.motion'], 'qtyp':DEVT['motion']},
	 HueTyps.light_level:{'prop':['light.light_level'], 'qtyp':DEVT['illuminance']},
	 HueTyps.device_power:{'prop':['power_state.battery_level'], 'qtyp':DEVT['unknown']},
	 HueTyps.button:{'prop':['button.last_event'], 'qtyp':DEVT['button']},
	 HueTyps.zigbee_connectivity:{'prop':['status.'], 'qtyp':DEVT['unknown']},
	 HueTyps.bridge_home:{'prop':['children'], 'qtyp':DEVT['unknown']},
	 HueTyps.scene:{'prop':['action'], 'qtyp':DEVT['unknown']},
	}

UPDATEINTERVAL=300
_loop = None
Semaphore=None

def getIP(url="https://discovery.meethue.com"):
	""" automatically fetch IP of hue bridge """
	stuff = None
	if (MDNS):
		resp = requests.get(url)
		stuff = resp.json()
	else:
		connection = HTTPSConnection(url)
		try:
			connection.request("GET", "/")
			response = connection.getresponse()
			stuff = response.read()
			#process_response(response)
		finally:
			connection.close()
		"""
	with aiohttp.ClientSession() as session:
		with session.get( url=url) as response:
			if response.status==200:
				try:
					stuff = response.json()
				except aiohttp.client_exceptions.ContentTypeError as ex:
					logger.warning('bad:{}'.format(response.text()))
					stuff={}
		"""
	if (stuff):
		logger.info("meethue stuff:{}".format(stuff))
		return stuff[0]['internalipaddress']

def createUser(ipadr:str, ssl=False):
	"""	press button on bridge before ..
	"""
	url=('https://' if ssl else 'http://') +ipadr+'/api'
	json = 	{"devicetype":"fshome#hjPhony"}
	resp = requests.post(url, json=json)
	stuff = resp.text
	logger.info("creating User {} on {} -> {}".format(json,url,stuff))
	if (stuff):
		return stuff['success']['username']

async def hueGET(ipadr:str,appkey:str,resource='',rid='',timeout=2, ssl=True) -> dict:
	''' get state info from hue bridge '''
	global Semaphore
	if Semaphore is None:
		Semaphore = asyncio.Semaphore()
		
	stuff:dict
	url=('https://' if ssl else 'http://') +ipadr+'/clip/v2/resource'
	headers = {'Content-Type': 'application/json'}
	headers = {'hue-application-key': appkey } # "{}".format(appkey) }
	#logger.info("hueGET:{}: with headers:{} on {}".format(resource,headers,url))
	
	if len(resource)>0:
		url += '/'+resource
	if rid:
		url+= '/'+rid
	#auth = aiohttp.BasicAuth(user, pwd)
	try:
		tic = time.perf_counter()
		async with aiohttp.ClientSession(headers=headers) as session:
			async with Semaphore, session.get( url=url, timeout=timeout, ssl=ssl) as response:
				if response.status==200:
					try:
						stuff = await response.json()
					except aiohttp.client_exceptions.ContentTypeError as ex:
						#stuff = await response.text()
						logger.warning('bad json:%s:%s' % (resource,await response.text()))
						stuff={}
				else:
					logger.warning('bad hue response :%s on %s' % (response.status,url))
					await session.close()
					await asyncio.sleep(0.2)
		toc = time.perf_counter()
		logger.info("hueGET: {url} in {t:0.4f} s {stat}".format(url=url, t=toc-tic, stat=response.status))
	except asyncio.TimeoutError as te:
		logger.warning("hueGET timeouterror %s :on:%s" % (te,url))
		await asyncio.sleep(10)
		stuff={}
	except Exception as e:
		logger.exception("hueGET unknown exception!!! %s :on:%s" % (e,url))
	#logger.debug('hueGET resource:%s with %s ret:%d' % (resource,r.url,r.status_code))
	return stuff

def st_hueGET(ipadr,user='',resource='',rid='',timeout=2,semaphore=None):
	global _loop
	if _loop is None:
		_loop = asyncio.get_event_loop()
	global Semaphore
	if Semaphore is None:
		Semaphore = asyncio.Semaphore()
	if _loop is None or Semaphore is None:  # and _loop.isrunning():
		logger.warning('no loop or semaphore')
	else:
		ssl = len(user) > 20  # no ssl for deCONZ
		ret = asyncio.run(hueGET(ipadr,user, resource,rid,timeout,ssl=ssl))
		if ret:
			#logger.info('static hueGET %s' % ret)
			return ret
	return {}
	
def st_hueSET(ipadr,appkey,rid,val, resource='light',reskey='dimming',prop='brightness',  ssl=True):
	return asyncio.run(hueSET(ipadr,appkey, rid,val, resource,prop, reskey, ssl))
	future = asyncio.run_coroutine_threadsafe(hueSET(ipadr,appkey,rid,val,prop, resource,reskey, ssl))
	return future.result()
	global _loop
	if _loop is None:
		#ret = asyncio.create_task(hueGET(ipadr,user, resource,timeout))
		_loop = asyncio.get_event_loop()
	#logger.info('hueSET:{} on {}'.format(data,url))
	return _loop.run_until_complete(hueSET(ipadr,appkey,rid,val,resource,reskey, prop,  ssl))
	

async def hueSET(ipadr,appkey,rid,val,resource='light',reskey='dimming',prop='brightness',  ssl=True):
	""" huiId: rid """
	global Semaphore
	if Semaphore is None:
		Semaphore = asyncio.Semaphore()
	url=('https://' if ssl else 'http://') +ipadr+'/clip/v2/resource/'
	headers = {'Content-Type': 'application/json'}
	headers = {'hue-application-key': appkey } # "{}".format(appkey) }
	logger.debug("headers:{}".format(headers))
	if len(resource)>0:
		url += resource
	if rid:
		url += '/'+rid
	data = {reskey:{prop:val}}
	#url += '%s%s' % (rid,reskey)
	#logger.info('hueSET:{} on {}'.format(data,url))
	tic = time.perf_counter()
	async with aiohttp.ClientSession(headers=headers) as session:
		async with Semaphore, session.put(url, json=data, ssl=ssl) as resp:
			toc = time.perf_counter()
			logger.info('hueSet {url} data:{dat} resp:{stat} in {t:0.4f} s'.format(url=url, dat=data, stat=resp.status, t=toc-tic))
			return resp

async def getCharDat(ipadr:str, appkey:str, endpoints:List[str]=ENDPOINTS[:5], chDat:ChDat={}) -> ChDat:
	""" read characteristics properties from bridge 
	ep:light->data:{'id': '02a77987-ed59-42c1-8d1b-fb86da1881da', 'id_v1': '/lights/20', 'owner': {'rid': 'c31a0002-48a8-4501-9897-3e02db8be411', 'rtype': 'device'}, 'metadata': {'name': 'gradStrip', 'archetype': 'hue_lightstrip'}, 'on': {'on': True}, 'dimming': {'brightness': 89.37, 'min_dim_level': 0.009999999776482582}, 'dimming_delta': {}, 'color_temperature': {'mirek': None, 'mirek_valid': False, 'mirek_schema': {'mirek_minimum': 153, 'mirek_maximum': 500}}, 'color_temperature_delta': {}, 'color': {'xy': {'x': 0.1957, 'y': 0.077}, 'gamut': {'red': {'x': 0.6915, 'y': 0.3083}, 'green': {'x': 0.17, 'y': 0.7}, 'blue': {'x': 0.1532, 'y': 0.0475}}, 'gamut_type': 'C'}, 'dynamics': {'status': 'none', 'status_values': ['none', 'dynamic_palette'], 'speed': 0.0, 'speed_valid': False}, 'alert': {'action_values': ['breathe']}, 'signaling': {}, 'mode': 'normal', 'gradient': {'points': [{'color': {'xy': {'x': 0.1957, 'y': 0.077}}}, {'color': {'xy': {'x': 0.2741, 'y': 0.1305}}}, {'color': {'xy': {'x': 0.4248, 'y': 0.23}}}, {'color': {'xy': {'x': 0.5578, 'y': 0.3216}}}, {'color': {'xy': {'x': 0.5198, 'y': 0.3755}}}], 'mode': 'interpolated_palette', 'points_capable': 5, 'mode_values': ['interpolated_palette', 'interpolated_palette_mirrored'], 'pixel_count': 24}, 'effects': {'status_values': ['no_effect', 'candle', 'fire'], 'status': 'no_effect', 'effect_values': ['no_effect', 'candle', 'fire']}, 'timed_effects': {'status_values': ['no_effect', 'sunrise'], 'status': 'no_effect', 'effect_values': ['no_effect', 'sunrise']}, 'powerup': {'preset': 'safety', 'configured': True, 'on': {'mode': 'on', 'on': {'on': True}}, 'dimming': {'mode': 'dimming', 'dimming': {'brightness': 100.0}}, 'color': {'mode': 'color_temperature', 'color_temperature': {'mirek': 366}}}, 'type': 'light'} 
	"""
	for endpnt in endpoints:
		dat = await hueGET(ipadr, appkey, resource=endpnt)
		#logger.info("ep:{}".format(endpnt))
		for dt in dat['data']: # a list usually 1 elm?
			_id = dt['id']
			nact,nsvr,nchld,ngrpnts = (0,0,0,-1)
			atyp = None
			chDat[_id] = {}
			chDat[_id]['type'] = HueTyps.fromstr(dt['type'])
			logger.debug("ep:{}->data:{}".format(endpnt,dt))
			
			if 'dimming' in dt:
				chDat[_id]['dimming'] = dt['dimming']
			if 'on' in dt:
				chDat[_id]['on'] = dt['on']
			if 'color' in dt:
				chDat[_id]['color'] = dt['color']
			if 'gradient' in dt:
				ngrpnts = len(dt['gradient']['points'])
			if 'button' in dt:
				chDat[_id]['button'] = dt['button']
			if 'motion' in dt:
				chDat[_id]['motion'] = dt['motion']
			if 'actions' in dt:
				nact = len(dt['actions'])
			if 'children' in dt:
				nchld = len(dt['children'])
			if 'services' in dt:
				svr = dt['services']
				nsvr = len(svr)
				chDat[_id]['services']=svr 
				"""
				continue
				for sv in svr:
					rtp=sv['rtype']
					if rtp in ['temperature','motion','light','button']:  #'zigbee_connectivity','entertainment','light']:
						rid=sv['rid']
						tmps= await hueGET(ipadr,appkey=appkey, resource='{}/{}'.format(rtp,rid)) # !!!
						if 'data' in tmps:
							tmps = tmps['data']
							for rec in tmps:
								if rtp in rec:
									 chDat[_id][rtp]= rec[rtp]  # save service data
									 logger.debug("svrid:{}({}) for {}->{} nsvr={}".format(rid,rtp,_id,rec,len(svr)))
						else:
							logger.warning("no data for svr:{}, tp:{}".format(sv,rtp))
				"""
			if 'metadata'in dt:
				mt = dt['metadata']
				if 'control_id' in mt:
					bid = mt['control_id']
					chDat[_id]['butidx'] = bid
				else:
					bid = None
				if 'archetype' in mt:
					atyp = mt['archetype']
				if 'name' in mt:
					chDat[_id]['name'] = mt['name']
					logger.info("fnd:{} htyp:{} actions:{} services:{} children:{} npoints:{} atyp:{} butidx:{}".format(mt['name'], dt['type'], nact,nsvr,nchld,ngrpnts, atyp,bid))
				elif 'owner' in dt:
					own = dt['owner']
					chDat[_id]['owner'] = own
					if own['rid'] in chDat:  # owner allready known
						nm = chDat[own['rid']]['name']
						logger.debug("but:{} owned by {}=({})".format(mt,own,nm))
			elif 'bridge_id' in dt:
				chDat[_id]['name'] = dt['bridge_id']
	return chDat
	"""
	# find owners for nameless ones
	for id,dat in chDat.items():
		if 'name' in dat:
			pass
		elif 'owner' in dat:
			rid = dat['owner']['rid'] # owner device of button
			if rid in chDat:
				nm = chDat[rid]['name']
				logger.info("{} owned by {} ({})".format(id,rid,nm))
				chDat[id]['name'] = nm
	return chDat
	"""

def findName(hid, chDat):
	nam:str=''
	oid=None
	if hid and hid in chDat:
		dat = chDat[hid]
		if 'name' in dat:
			nam = dat['name']
		elif 'owner' in dat:
			oid = dat['owner']['rid']
			if oid in chDat:
				if 'metadata' in chDat[oid]:
					nam = chDat[oid]['metadata']['name']
				else:
					nam = chDat[oid]['name']  # buttons
			else:
				logger.warning('owner:{} not fnd for {} in {}'.format(oid,hid,dat))
		elif 'motion' in dat:
			pass # found in services
		else:
			logger.warning('svr {} no good dat:{}'.format(hid,dat))
	if not nam: # look in services
		#logger.debug("look for {} in services ".format(id))
		for own,rec in chDat.items():
			if 'services' in rec:
				for sv in rec['services']:
					if hid==sv['rid']:
						rt=sv['rtype']
						dat=sv
						nam=rec['name']
						logger.debug("svr fndnm:{} as:{} for {} as {}".format(hid,nam,own,rt))
						oid=hid
						break
		if not nam:
			logger.warning("name not found for {} -> {}".format(hid,oid))
	#logger.debug("fndName:{}->{} ".format(id,nam))
	return nam,oid
	
def FindId(name, qtyp, chDat):
	""" find hueId with matching name and type. also look in services of a device """
	sid=None
	for htyp,trec in HUETYP.items():
		if qtyp==htyp.qTyp:  # trec['qtyp']:
			for rid,rec in chDat.items():
				if 'name' in rec and name==rec['name']:
					if	rec['type']==htyp.name:
						sid = rid
						break
					else:
						if 'services' in rec:
							for sv in rec['services']:
								if htyp.name==sv['rtype']:
									sid=sv['rid']
									break
	return sid

def FindOwnerId(sid, htyp, chDat):
	oid=None
	#for htp,trec in HUETYP.items():
	#	if htp==htyp:  #qtyp==trec['qtyp']:
	for rid,rec in chDat.items():
		#if 'name' in rec and name==rec['name']:
		if 'services' in rec:
			for sv in rec['services']:
				if sid==sv['rid'] and htyp==sv['rtype']:
					oid=rid 
					break
	return oid


async def eventListener(ipadr:str, appkey:str, evCallback, chDat:ChDat) ->None:
	""" keep listening for events arriving at hue bridge """
	headers = {'hue-application-key': appkey, 'Accept': 'text/event-stream'  } # "{}".format(appkey) }
	url = 'https://{}/eventstream/clip/v2'.format(ipadr)
	async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=0)) as session:
		async with sse.EventSource(url, session=session, headers=headers, ssl=False) as event_source:
			try:
				logger.info('Event.src:{} ready:{}'.format(event_source.url,event_source.ready_state))
				async for event in event_source:  # repeat listening
					dat = json.loads(event.data)
					for dt in dat: # is a list
						tm = dt['creationtime'] # ISO 8601						
						if 'Z' in tm:  # The timezone offset for UTC is 0 and would be indicated with the letter Z
							tm = tm.replace('Z','+0000')  # allow parsing to tx:utc
						loct = datetime.strptime(tm, "%Y-%m-%dT%H:%M:%S%z").astimezone() # aware local tz
						#loct = date.fromisoformat(dt['creationtime'])
						for dati in  dt['data']: # try to find numerical value associated with key in EVtypes
							num=float('nan')
							val=None
							tp = dati['type']
							_id = dati['id']
							nam,oid = findName(_id, chDat) # may give owner name
							htyp = HueTyps.fromstr(tp)
							if htyp in HUETYP:
								key = HUETYP[htyp]['prop']
								typ = htyp.qTyp # HUETYP[htyp]['qtyp']
								if _id in chDat:
									oid = _id
									logger.debug("known.ev.id:{} for:{} typ:{} dd:{}".format(oid,nam,typ,tm))
								else:
									oid = FindOwnerId(_id, tp, chDat)
									logger.debug("indir.ev.id:{} typ:{} {} for:{} dd:{}".format(oid,typ,nam,_id,tm))
								if key and len(key)>0:
									for ky in key: # all posible properties of the type
										kys=ky.split('.')
										if kys[0] in dati:
											val = dati[kys[0]]  # entire rec
											if len(kys)>0 and isinstance(val,dict) and kys[1] in val:
												val = val[kys[1]]
												num = val
												if isinstance(val, (float,int)):
													num = float(val)
												elif isinstance(val, str) and val.replace('.','').isnumeric():
													num = float(val)
												elif isinstance(val, dict):  # {'x':0.123, 'y':0.234}
													logger.info("dict({}) for {}:{} has changed".format(val,tp,nam))
												elif isinstance(val, str) and tp=='button':
													logger.info("ev.{} '{}'.[{}] for {}".format(tp,val,kys[1],nam))
												else:
													logger.warning("{} for {} is not a num in {}".format(val,tp,ky))
											else:
												logger.debug("no prop:{} for ev:{} of:{} in:{}".format(key,nam,tp,val))
											evCallback(oid,loct,nam,num,htyp)
											break
							else:
								logger.warning("unknown ev-HueTyp:{} for {} with {}".format(tp,nam,htyp))
			except ConnectionError as ex:
				logger.error("error:{}".format(ex))

				
def evCallback(id:str, tm:datetime,name, val, typ) -> Tuple[datetime,str,float]:
	""" find id in chDat , return name with num val """ 
	logger.info("evCallback:{}->{} as:{} dd:{}".format(name,val,typ,tm))
	return tm,name,val,typ

async def main(ipadr,appkey, chDat:ChDat={}):
	#global chDat
	#chDat={}
	#dat = st_hueGET(ipadr,user=user, resource=ep)
	ret = await getCharDat(ipadr, appkey, ENDPOINTS)
	logger.warning("chDat len:{} ep:{}".format(len(ret),ENDPOINTS))
	for id,dat in ret.items():
		logger.debug("chId:{}->dat:{}".format(id,dat))
	chDat.update(ret)
	await eventListener(ipadr, appkey, evCallback, chDat)
	
	#await asyncio.gather(* [tst_sensors(sensors), tst_light(lmp), tst_webSock(ipadr,user)])

if __name__ == '__main__':	# just testing the API and gets userId if neccesary
	logger = tls.get_logger(__file__, levelConsole=logging.INFO, levelLogfile=logging.DEBUG)
	
	import secret
	#logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S%z")))
	
	CONF={	# defaults when not in config file
		"hueuser":  secret.keySIGNIFY,
		"huebridge": getIP() # "192.168.44.21"
	}
	
	ipadr=CONF['huebridge']
	user= CONF['hueuser'] if CONF['hueuser'] else createUser(ipadr)
	
	_loop = asyncio.get_event_loop()
	_loop.run_until_complete(main(ipadr, user))
	
	lightid='02a77987-ed59-42c1-8d1b-fb86da1881da' # id of a light as example
	ret = _loop.run_until_complete(hueSET(ipadr,appkey=user,resource='light',rid=lightid, reskey='on', prop='on',val=True))
	logger.info('light on:{}'.format(ret))
	ret = _loop.run_until_complete(hueSET(ipadr,appkey=user,resource='light',rid=lightid, reskey='dimming', prop='brightness',val=80))
else:
	logger = tls.get_logger()
