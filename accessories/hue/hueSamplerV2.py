#!/usr/bin/env python3.5
""" logs hue sensor values to a database """

import sys,os,time,logging,asyncio
from datetime import datetime
if __name__ == "__main__":
	sys.path.append(os.getcwd())
	#sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	#from hueAPI import HueSensor,HueLight,HueBaseDev,getTyp,getProp

from accessories.hue.hueCharacteristic import hueLight,hueSensor,hueBase #getTyp,getProp
from accessories.hue.hueAPIv2 import HueTyps,FindId,findName
from lib.sampleCollector import DBsampleCollector
from lib.devConst import DEVT,qSRC
from lib.tls import get_logger
#import accessories.hue.hueAPIv2 as hueAPI
from typing import Tuple,Any

class hueSampler(DBsampleCollector):
	""" fshome interface to a Hue or deCONZ bridge """
	#devdat = {}	# dict of hue devices (either lights or sensors)
	charact = {}
	@property
	def manufacturer(self):
		return "SignifyV2" #  "deCONZ" if self.deCONZ else "Signify"
	#minqid= QID['HUE'] # 500 for deCONZ
	
	def __init__(self,iphue,appkey, *args, **kwargs):
		super().__init__(*args, **kwargs) # gets _servmap from config
		hueBase(iphue,appkey, self.debug)
		for hid,rec in hueBase.chDat:
			nm = rec['name']
			qtyp = rec['type'].qTyp
			qid = self.qid(typ=qtyp,name=nm)
			if qid and qtyp<DEVT['unknown']:
				hueSampler.charact[qid] = hueBase.create(nm, qTyp)
			else:
				logger.warning("no conf for {} as {}".format(nm,qtyp))
		self.minqid = qSRC['HUE'] # qSRC['deCONZ'] if self.deCONZ else qSRC['HUE']
		
		#logger.info("%s lights:%s" % (self.manufacturer,len(hueSampler.devdat)-nDev))
		self.defSignaller(self.name)
		
	async def receive_message(self):
		''' get sensors state from hue bridge and check for updates and process recu when new '''
		n=0
		dt=datetime.now()
		"""
		if hueBase.chDat:
			#self.chDat.update(await hueAPI.getCharDat(self._iphue, self._appkey))
			for rid,rec in hueBase.chDat.items():
				qid = None
				nam = rec['name'] if 'name' in rec else findName(rid, hueBase.chDat)
				htyp = rec['type']
				typ = htyp.qTyp if htyp else None 
				sid = FindId(nam, typ, hueBase.chDat)
				if sid and typ and typ!=DEVT['unknown']:
					qid = self.qCheck(quantity=None, devadr=sid, name=nam, typ=typ)
				if qid is None:
					logger.warning('unknown qid for:{},{},{}={}'.format(rid,nam,typ,rec['type']))
		"""
		return n,await super().receive_message(dt)
	"""
			if not htyp:
				if 'services' in rec:
					for sv in rec['services']:
						htyp=hueAPI.HueType(sv['rtype'])
						typ = htyp['qtyp'] if htyp else None 
						if typ:
							qid = self.qid(devadr=None, name=nam, typ=typ)
						if qid:
							sid = sv['rid']
							logger.debug("qidsvr fnd:{} as:{} for {} as {}".format(sid,nam,rid,htyp))
							if typ:
								break
			if qid:
				self.qCheck(quantity=qid, devadr=sid, name=nam, typ=typ)
				continue
			typ = htyp['qtyp'] if htyp else None
			#DEVT[rec['type']] if rec['type'] in DEVT else None
			
			if nam and typ:
				qid = self.qid(devadr=None, name=nam, typ=typ) 
				if qid:
					self.qCheck(quantity=qid, devadr=rid, name=nam, typ=typ)
				#self._servmap[qid]['devadr']=rid
				
			if qid is None:
				logger.warning('unknown qid for:{},{},{}={}'.format(rid,nam,typ,rec['type']))
		return
		
		rec = await hueAPI.eventListener()
		
		for qid,dev in hueSampler.devdat.items():
			if self.deCONZ == dev.deCONZ:  # same bridge
				newval = await dev.newval()
				if newval:
					n-=1
					dtm = await dev.lastupdate()
					val = await dev.value()
					if dtm and not isinstance(val, dict):
						self.check_quantity(dtm.timestamp(), qid, val)
					else:
						logger.warning('bad hue val %s at %s' % (dtm,val))
				else:
					await asyncio.sleep(dev.refreshInterval/1000)
			else:
				logger.debug('(%d) other hue_sampler %s<>%s in %s' % (qid,self.deCONZ,dev.deCONZ,self.manufacturer))
		return n,await super().receive_message(dt)
	"""

	def evCallback(self, hid:str, tm:datetime, name, val, htyp): #-> Tuple[datetime,str,float]:
		""" called by eventListener on receiving an hue event """
		hueBase.evCallback(hid,tm,name,val,htyp)
		qid = self.qCheck(quantity=None, devadr=None, typ=htyp.qTyp, name=name)
		if qid:
			#if DBsampleCollector.signaller.checkEvent(qid,val):
			#	logger.info('%s event by %s=>%s typ(%s) cnt:%s' % (devName,qid,rec,typ,mcnt))
			#	DBsampleCollector.signaller.signal(qid, rec)
			#dtm = datetime.now(timezone.utc)
			self.check_quantity(tm.timestamp(), qid, val)
			if DBsampleCollector.signaller.checkEvent(qid,val):
				logger.info('%s signal by %s=>%s typ(%s) ' % (name,qid,val,htyp))
				# sampleCollector.signaller.signal(qid, val)
		elif self.debug:
			logger.warning("unknown event from:{} as:{}={} for:{}".format(name,htyp,val,hid))
		return qid
		
	
	async def eventListener(self, signaller):
		''' waiting for events indefinitely, will be registered by defSignaler '''
		await super().eventListener(signaller)  # virtual empty one
		#allready scheduled eventlistener by hueBase
		logger.info("starting eventListener from {} in {}".format(self.__class__.__name__, self))
		await hueBase.eventListener(self.evCallback)  #self._iphue, self._appkey, self.evCallback, self.chDat)
		logger.warning("error:{} should keep listening".format(self.name))
		return
		
		if self.deCONZ:
			mcnt=0
			for qid,dev in hueSampler.devdat.items():
				logger.info('running eventListener for (%s) %s' % (qid,dev))
				if self.deCONZ and dev.deCONZ:  # deCONZ bridge
					#await asyncio.sleep(30)
					devName = await dev.name()
					logger.info('waiting for events on %s for %s with %s' % (qid,devName,self))
					while True:
						msg = await dev.eventListener()  # calls websocket
						if msg and 'id' in msg:
							qid = self.qCheck(quantity=None,devadr=msg['id'])
							if qid and 'state' in msg:
								rec = msg['state']
								typ = getTyp(rec)
								val = getProp(rec)
								#if typ!=dev.typ:
								#	logger.warning('uneq event types: %d != %d' % (typ,dev.typ))
								if 'buttonevent' in rec:
									logger.info('button chg:%s' % rec['buttonevent'])
								if signaller.checkEvent(qid,val):
									logger.info('%s event by %s=>%s typ(%s) cnt:%s' % (devName,qid,rec,typ,mcnt))
									signaller.signal(qid, rec)
								await asyncio.sleep(4)
								mcnt=0
							else:
								mcnt +=1
						else:
							await asyncio.sleep(0.01)
		logger.warning('no eventListener in %s, deCONZ:%s' % (self,self.deCONZ))
			
		
	def set_state(self, quantity, state, prop='bri', dur=None):
		''' stateSetter callback =for HAP to set hue device '''
		if not super().set_state(quantity, state, prop=prop):
			return None
		if self.qtyp(quantity)==DEVT['lamp']:
			if prop=='bri':
				hueSampler.charact[qid].on = state>0
				hueSampler.charact[qid].brightness = state
			elif prop=='hue':
				pass  # todo
			elif prop=='sat':
				pass  # todo
		logger.warning("no set_state implemented yet for hue")
		return
		devadr = self.qdevadr(quantity)
		if devadr:  #quantity in hueSampler.devdat:
			name = self.qname(quantity)
			typ = self.qtyp(quantity)
			hueAPI.st_hueSET(self.ipadr,self.appkey, rid=lightid, resource='light', reskey='on', prop=prop,val=state)
			#return hueSampler.devdat[quantity].setValue(prop, state)
		else:
			logger.warning('no such quantity:%s' % quantity)

	async def setState(self, quantity, state, prop='brightness'):
		devadr = self.qdevadr(quantity)
		if devadr:  #if quantity in hueSampler.devdat:
			logger.info("setState {}->{} on {}".format(quantity,state,devadr))
			#return await hueSampler.devdat[quantity].setState(prop, state)
			await hueAPI.hueSET(self.ipadr,self.appkey, rid=lightid, resource='light', reskey='dimming', prop=prop, val=state)
		else:
			logger.warning('no such quantity:%s' % quantity)
		
	def semaphore(self):
		''' to use to block concurrent http tasks '''
		return HueBaseDef.Semaphore

if __name__ == "__main__":
	import asyncio
	import secret
	logger = get_logger(__file__, levelConsole=logging.INFO, levelLogfile=logging.DEBUG)
	
	conf={	# to be loaded from json file
		"hueuser":secret.keySIGNIFY,   # secret.keyDECONZ,
		"huebridge": "192.168.44.21",  # secret.IP	
		#"dbFile": "/mnt/extssd/storage/fs20store.sqlite"
		"dbFile": '~/fs20store.sqlite'
	}
	QCONF = {  # example default configuration
  "207": {
    "source": "entree",
    "name": "DeurMot",
    #"devadr": "7",
    "typ": 11,
    "signal": "109=26"
  },
  
  "208": {
    "source": "entree",
    "name": "DeurMot",
    #"devadr": "8",
    "typ": 5
  },
  "206": {
    "source": "entree",
    "name": "DeurMot",
    #"devadr": "9",
    "typ": 0
  },
  "230": {
    "source": "woon",
    "name": "woonTapper", #"tapKnops",
    #"devadr": "2",
    "typ": 12
  },
  
  "231": {
    "source": "keuken",
    "name": "keukMot",
    #"devadr": "19",
    "typ": 0
  },
  "232": {
    "source": "keuken",
    "name": "keukMot",
    #"devadr": "17",
    "typ": 11
  },
  "233": {
    "source": "keuken",
    "name": "keukMot",
    #"devadr": "18",
    "typ": 5
  },
   "235": {
    "source": "kamerEet",
    "name": "eetKnops",
    #"devadr": "5",
    "typ": 12
   },
  "236": {
    "source": "keuken",
    "name": "afzuigSwi",
    #"devadr": "5",
    "typ": 13,
    "mask":0
  },
   "244": {
    "source": "tuin",
    "name": "motMaroc",
    #"devadr": "10",
    "typ": 11,
    "signal": "117=00"
  },
  "243": {
    "source": "tuin",
    "name": "motMaroc",
    #"devadr": "12",
    "typ": 0
  },
   "245": {
    "source": "tuin",
    "name": "motMaroc",
    #"devadr": "11",
    "typ": 5
  },
  "246": {
    "source": "terras",
    "name": "motTerras",
    #"devadr": "54",
    "typ": 11
  },
  "247": {
    "source": "terras",
    "name": "motTerras",
    #"devadr": "56",
    "typ": 0
  },
  "248": {
    "source": "terras",
    "name": "motTerras",
    #"devadr": "55",
    "typ": 5
  },
  "256": {
    "source": "woon",
    "name": "zSwitch",
    #"devadr": "3",
    "typ": 12
  },
  "257":{
	  "source":"woon",
	  "name":"tapDial",
	  "typ":12
  },
  "260":{    
    "typ": 13,
    "name": "eetStrip",
    #"devadr":"4",
    "aid":20,
    "mask":0
  },
  "261":{    
    "typ": 13,
    "name": "broodStrip",
    #"devadr":"4"
    "mask":0
  },
  "262":{    
    "typ": 13,
    "name": "kookStrip",
    "mask":0 #"devadr":"4"
  },
  "263":{    
    "typ": 13,
    "name": "gradStrip",
    "mask":0 #"devadr":"4"
  },
  "264":{    
    "typ": 13,
    "name": "buroStrip",
    "mask":0    #"devadr":"4"
  },
   "265":{    
    "typ": 13,
    "name": "kasStrip",
    "mask":0    #"devadr":"4"
  },
  "266":{    
    "typ": 13,
    "name": "gradStaak",
    "mask":0    #"devadr":"4"
  },
   "267":{    
    "typ": 13,
    "name": "kaleAmb",
    "mask":0    #"devadr":"4"
  },
  "268":{    
    "typ": 13,
    "name": "colStraler",
     "source":"woon",
    "mask":0    #"devadr":"4"
  },
  "269":{    
    "typ": 13,
    "name": "garSwi4pi",
    "source":"woon",
    #"devadr":"4"
  },
  "270":{    
    "typ": 13,
    "name": "colBol",
    "source":"woon",
    "mask":0    #"devadr":"4"
  },
  "271":{    
    "typ": 13,
    "name": "ambBanq",
     "source":"woon",
    "mask":0    #"devadr":"4"
  },
  "272":{    
    "typ": 13,
    "name": "ambDeur",
    "source":"woon",
    "mask":0    #"devadr":"4"
  },
  "273":{    
    "typ": 13,
    "name": "wambUpper",
    "source":"woon",
    "mask":0    #"devadr":"4"
  },
  "274":{    
    "typ": 13,
    "name": "colSpot",
    "source":"woon",
    "mask":0    #"devadr":"4"
  },
  "275":{    
    "typ": 13,
    "name": "witStraler",
    "source":"woon",
    "mask":0    #"devadr":"4"
  },
  "220":{
	  "source":"zolder",
	  "name":"motZol",
	  "typ":11
	  },
  "221":{
	  "source":"zolder",
	  "name":"motZol",
	  "typ":0
	  },
  "222":{
	  "source":"zolder",
	  "name":"motZol",
	  "typ":5
	  },
  "224":{
	  "source":"zolder",
	  "name":"zolPlug",
	  "typ":13,
	  "mask":0
	  },
  "225":{
	  "source":"zolder",
	  "name":"zolWekk",
	  "typ":13,
	  "mask":0
	  },
  "226":{
	  "source":"zolder",
	  "name":"LivCol",
	  "typ":13,
	  "mask":0
	  }}

	QDECONZ={  # config for deconz alternative hue bridge
  "570": {
    "source": "gang",
    "name": "gangSwitch",
    "devadr": "2",
    "typ": 12,
    "signal" :"116=17,4cfa"
  },
  "580":{
    "source" :"gang",
    "typ": 13,
    "name": "deurLmp",
    "devadr": "2"
	 },
	 
  "207": {
    "source": "entree",
    "name": "DeurMotion",
    "devadr": "7",
    "typ": 11
  },
  "243": {
    "source": "tuin",
    "name": "tempMaroc",
    "devadr": "12",
    "typ": 0
  },
  "208": {
    "source": "entree",
    "name": "DeurLux",
    "devadr": "8",
    "typ": 5
  },
  "256": {
    "source": "zeSlaap",
    "name": "zSwitch",
    "devadr": "3",
    "typ": 12
  },
  "245": {
    "source": "tuin",
    "name": "luxMaroc",
    "devadr": "11",
    "typ": 5
  },
  "206": {
    "source": "entree",
    "name": "DeurTemp",
    "devadr": "9",
    "typ": 0
  },
  "231": {
    "source": "keuken",
    "name": "keukTemp",
    "devadr": "19",
    "typ": 0
  },
  "244": {
    "source": "tuin",
    "name": "motMaroc",
    "devadr": "10",
    "typ": 11
  },
  "230": {
    "source": "woon",
    "name": "tapKnops",
    "devadr": "2",
    "typ": 12
  },
  "232": {
    "source": "keuken",
    "name": "keukMot",
    "devadr": "17",
    "typ": 11
  },
  "235": {
    "source": "kamerEet",
    "name": "eetKnops",
    "devadr": "5",
    "typ": 12
  },
  "233": {
    "source": "keuken",
    "name": "keukLux",
    "devadr": "18",
    "typ": 5
  },
  "260":{    
    "typ": 13,
    "name": "eetStrip",
    "devadr":"4",
    "aid":20
  }}
	
	bri=1
	async def huepoll(hueobj):
		#while True:	
		#loop = asyncio.get_running_loop()
		global bri
		dt = await hueobj.receive_message()  # both sensors and lights
		qa = hueobj.qactive()
		if dt:
			logger.debug('receive_polled:%s qactive=:%s' % (dt, [q for q in qa]))
		for qid in qa:
			upd = hueobj.isUpdated(qid)
			if upd:
				last = hueobj.get_last(qid)
				logger.debug('qid %s updated to %s' % (qid,last))
			typ = hueobj.qtype(qid)
			if typ == DEVT['lamp']:
				bri += 1
				#logger.info("set bri of %s to %s" % (qid,bri))
				await hueobj.setState(qid, bri % 100, prop='brightness')
				#hueobj.set_state(qid, bri % 100, prop='bri', loop=loop)
				#hueobj.devdat[qid].setValue(prop='bri', bri)
				#await asyncio.sleep(0.1)
		await asyncio.sleep(120)
	
	async def main(conf):
		hueobj = hueSampler(conf['huebridge'], conf['hueuser'], dbFile=conf['dbFile'], quantities=QCONF, minNr=1, maxNr=3, minDevPerc=0.5)
		
		try:		
			#hueobj.set_state(260, 'true', prop='on')		
			while True:
				await huepoll(hueobj)
		
		except KeyboardInterrupt:
			logger.warning("terminated by ctrl c")
		except Exception:
			logger.exception("unknown exception!!!")
		finally:
			#hueobj.set_state(260, 'false', prop='on')
			time.sleep(1)
			hueobj.exit()


	loop = asyncio.get_event_loop()
	
	loop.run_until_complete(main(conf))
	logger.critical("bye")
else:	# this is running as a module
	logger = get_logger()  # get logger from main program
