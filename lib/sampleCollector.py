
""" generic template for sampler devices generating (averaged and filtered) data to be stored
"""

import logging,time,json,enum,re
from datetime import datetime
import collections
import asyncio
from lib.grtls import julianday,prettydate
from lib.dbLogger import sqlLogger
from lib.devConst import qCOUNTING,DEVT,DVrng
from lib.tls import get_logger
logger = get_logger(__file__)	# get logger from main program
from typing import Dict,Tuple,List,Any,Set,Union

async def forever(func, *args, **kwargs):
	''' run (await) function func over and over '''
	while (True):
		await func(*args, **kwargs)

# index to self.average[]
qVAL=0	# meas value
qCNT=1	# counted events
qSTMP=2	# time stamp

class sm(enum.IntFlag):
	ADR=0	# devadr
	TYP=1	# DEVT
	NM= 2	# name
	SRC=3	# source
	MSK=4	# mask
	SIG=5	# signaller spec
	
class signaller(object):
	""" detector and actuator for trigger events 
		e.g. add to json quantity config:
		"signal": "109=26"
		which will cause to call set_state on quantity:109 to value 26
		"signal": ""
	"""
	#reSIGDEF = r"^(\d+)\=(\d+\.*\d*)"   # qid=qval,bitnr    fs20qid=cmd
	#reSIGPTRN = r"(?:[^|=|,])(\d+\.*\d*)"
	reSIGPTRN = r'(“(?:[^"]*)"|[^,=]*)(,|=|$)'  #r"(?:[=|\,])*(\d+\.*\d*)"  # numbers csv
	minEventInterval = 120	# only allow trigger of same event once every x s
	
	def __init__(self):
		self._eventDetect={}
		self._signalDef={}	# from config
		self._handlers={}		# callback functions for handling event
		self._occurances={}  # last occurance time for qid event
		logger.info('creating signaller for %s' % self)
	
	def __repr__(self):
		return '%s with %s' % (type(self).__name__,['%s' % hnd for hnd in self._handlers])

	def setSignalDef(self, requester, qid, defstr):
		''' if qid occurs then signal will be called to do defstr =
			 trgqid=trgval,trgprop,trgdur e.g.  "600=0.2,zounds/37.wav" or "410=1,5,0.8" '''
		#sdef=defstr.split('->')
		#if len(sdef)>1:
		#	self._eventDetect[qid]=sdef[0]
		self._signalDef[qid] = defstr # sdef[-1]
		logger.info('do "%s" on detection ch:%s of %s' % (defstr,qid,requester))
		
	def checkEvent(self, qid, qval):
		''' check loaded qid whether it arms an event. todo check qval for something in def '''
		active = False
		if qid in self._eventDetect:
			logger.warning('TODO: checking qid:%s with %s for having %s' % (qid,qval,self._eventDetect[qid]))
			active=True
		if qid in self._signalDef:
			active=True
		if type(qval) is bool:
			logger.info('bool event:%d = %s' % (qid,qval))
			return True # deConz bool event only adrrives once  # qval  # only trigger once on motion detect
		return active
		
	def signal(self, qid, qval=None):
		''' qid has occured, now look if a signaldef is attached, then execute it '''
		if qid in self._signalDef:
			sdef=self._signalDef[qid]  #.split('->')[-1]  # get cmd to execute after -> if there
			if qid in self._occurances:
				tsince = datetime.now() - self._occurances[qid]
				tsince = tsince.total_seconds()
			else:
				tsince = None
			if tsince and tsince<signaller.minEventInterval:
				logger.warning('event on %s occuring to soon:%s' % (qid,tsince))
			else:
				mch = re.compile(signaller.reSIGPTRN).finditer(sdef) # find pattern in signal def
				if mch:
					lst =[x.group(1) for x in mch] # all numbers
					logger.info("event signalling:{}".format(lst))
					lst += [None]*(4-len(lst))  # expand to len 4
					if lst and lst[0]:
						#lst =[float(x) if x.isnumeric() else x for x in lst]
						trgqid,trgval,trgprop,trgdur = lst[:4]
						trgqid=int(trgqid)
						#else:
						#	trgqid,trgval,trgprop,trgdur = (0,None,None,None)
						logger.info('signalling %s=%s with %s => %s' % (qid,qval,sdef,lst))
						for hnd,stscb in self._handlers.items():  # check all handlers till acq
							if stscb(trgqid, trgval, trgprop, trgdur):  # set_state callback
								self._occurances[qid] = datetime.now()
								logger.info('event with:%s handled by %s' % (qid,hnd))
								break
					else:
						logger.warning('qid -> trg not handled:%s -> %s' % (qid,sdef))
				else:
					logger.info('qid:%s no match in %s' % (qid,sdef))
		else:
			#logger.warning('qid %s has no event handler' % qid)
			pass

	def registerStateSetter(self, handler, setStateCallback):
		''' typically called by sampleCollector class to register its set_state method 
			handler = name of actual sampleCollector class
		'''
		logger.info('%ssetting signaller callback for %s' % ("RE-" if handler in self._handlers else "" , handler))
		self._handlers[handler] = setStateCallback  # !!!
		
	def registerEventSource(self, handler, eventListenerCoro):
		""" add eventListener to actual async loop """
		loop =asyncio.get_event_loop()
		logger.info("starting eventListener from {} in {}".format(self.__class__.__name__, self))
		task =loop.create_task(eventListenerCoro)
		logger.info('created events task from %s task:%s on:%s' % (handler,task,loop))
		time.sleep(1)

class sampleCollector(object):
	""" base class for collection of sampling quantities; 
	    typically a device collecting multiple samples is a derived sampleCollector """
	signaller:signaller =None # each sampler will have its own statesetter in the signaller set by childs
	objCount=0
	dtStart = datetime.now()
	mintinterval=4
	@property
	def manufacturer(self):
		return self.name

	def __init__(self, maxNr:int=120,minNr:int=2, minDevPerc:float=5.0, name:str='', debug=False):
		""" create object for handling measured quantities of a device 
		minDevPerc: only store quantity values having deviation larger than this from avg 
		maxNr : still store sample if nr of samples exceeds this """
		self._servmap: Dict[int,Dict[int,Any]] = {}
		self.maxNr = maxNr
		self.minDevPerc = minDevPerc
		self.minNr = minNr
		self.average: Dict[int,Dict[int,Any]] ={}
		self._lastval: Dict[int,float]={}
		self._actual: Dict[int,Dict[int,Any]]= {}
		self.minqid=None	# allow unknown quantities to be created if not None
		self.debug=debug
		sampleCollector.objCount+=1
		if name:
			self.name=name
		else:
			self.name=type(self).__name__ + "_%d" % sampleCollector.objCount		# name of class
			
		logger.info('%s sampler minNr=%d maxNr=%d minDevPerc=%.5g' % (self.name,minNr,maxNr,minDevPerc))
		self._updated:Set[int]=set() # quantities that have been updated and not accepted yet
		self._tAccept: Dict[int, float] = {}

	def __repr__(self):
		"""Return the representation of the sampler."""
		return 'name={} quantities={}>' \
			.format(self.name, {self.qname(qid):qid for qid in self._servmap})
	
	def defSignaller(self, forName=None):
		""" creates signaller class, registers set_state for each sampler
		    registers eventListener of a sampler if it has one
			typically called by sampler constructor
		"""
		if not hasattr(sampleCollector, 'signaller') or not sampleCollector.signaller:
			sampleCollector.signaller = signaller()
		if forName is None:
			forName = self.name  # unique for each sampler
		sampleCollector.signaller.registerStateSetter(forName, self.set_state)
		if hasattr(self, 'eventListener'):  # may be defined in ancester
			sampleCollector.signaller.registerEventSource(forName, self.eventListener(signaller=sampleCollector.signaller))
			logger.info('registered eventListener for %s on %s' % (forName,sampleCollector.signaller))
		else:
			logger.info('no eventListener for %s' % forName)
	
	def defServices(self, quantitiesConfig:Dict[Any,Dict[str,Any]]):
		''' compute dict of recognised services from quantities config => self._servmap '''
		for qid,rec in quantitiesConfig.items():
			if type(qid) == str:
				if qid.isnumeric():
					qid = int(qid)
				else:
					qid = None
			if type(rec) is dict:  # and qid.isnumeric():
				adr=rec['devadr'] if 'devadr' in rec else None  # "%d" % (qid % 100,)
				typ=rec['typ'] if 'typ' in rec else DEVT['unknown']
				if type(typ) is str:
					typ = DEVT[typ]
				nm =rec['name'] if 'name' in rec else "no:%s" % adr
				src =rec['source'] if 'source' in rec else ''
				self._servmap[qid]={sm.ADR:adr, sm.TYP:typ, sm.NM:nm, sm.SRC:src}
				if 'mask' in rec:
					logger.info('masking:{} for qid:{} nm:{} with:{}'.format(rec['mask'],qid,nm,typ))
					self._servmap[qid][sm.MSK] = rec['mask']
				if 'signal' in rec:
					if sampleCollector.signaller:
						sampleCollector.signaller.setSignalDef(self.name, qid, rec['signal'])
					#self.servmap[int(qid)][sm.SIG] = rec['signal']
		return self._servmap
		
	def nAvgSamps(self, qid):
		""" nr of samples to average, before accepting the avg """
		if qid in self.average:
			return self.average[qid][qCNT]
		return None
	
	def qid(self,devadr=None,typ=None,name=None):
		''' search for qid of quantity having devadr and or typ '''
		for quid,rec in self._servmap.items():
			qi = None
			if devadr is None or not rec[sm.ADR]:
				if (typ==rec[sm.TYP]) and (name==rec[sm.NM]):
					qi = quid
			elif (devadr==rec[sm.ADR] or rec[sm.ADR] == '{}'.format(devadr)):
				if (typ is None or typ==rec[sm.TYP]) and (name is None or name==rec[sm.NM]):
					qi = quid
			if qi:
				return qi
		return None
	
	def qCheck(self,quantity,devadr,typ=None,name=None,source=None):
		''' check whether quantity with devadr,typ,name,source attributes exists in servmap;
			creates or updates (unknown) quantity to self._servmap '''
		if not quantity:
			quantity=self.qid(devadr=devadr,typ=typ,name=name)
			if quantity and name and self.debug:
				logger.debug("qid:{} nm:{} adr:{} tp:{} n={}".format(quantity,name,devadr,typ, self.nAvgSamps(quantity)))
		if typ and (typ>=DEVT['unknown'] or typ==DEVT['fs20']):  # not precise
			typ=None
		if not source:
			source = self.qsrc(quantity)
		mp = {sm.ADR:devadr, sm.TYP:typ, sm.NM:name, sm.SRC:source}
		if quantity in self._servmap:
			if self.qtype(quantity)==DEVT['secluded']:
				mp[sm.TYP]=DEVT['secluded']
			mp = {smi:mp[smi] if smi in mp and mp[smi] is not None else it for smi,it in self._servmap[quantity].items() }
		else:
			if devadr and typ:
				if not quantity and self.minqid:
					quantity = max(self._servmap)+1  # TODO look for exists
					if quantity<self.minqid:
						quantity=self.minqid
					logger.info("%s creating quantity:%s = %s" % (self.manufacturer,quantity,mp))
		if mp[sm.TYP] is None:
			mp[sm.TYP]=DEVT['unknown']
		if quantity:
			if quantity not in self._servmap:
				logger.info("defining {}->{}".format(quantity,mp))
			elif self._servmap[quantity][sm.ADR] != devadr:
				logger.info("assigning devadr {} (typ:{})->{} (nm:{})".format(quantity,mp[sm.TYP],devadr,mp[sm.NM]))
			self._servmap[quantity] = mp
		return quantity
	
	def jsonDump(self):
		''' extract modified quantities config enhanced by newly discovered and more info'''
		cnf={}
		for qid,tp in self._servmap.items():
			if tp and isinstance(tp,dict):
				cnf[qid] = {'devadr':tp[sm.ADR],'typ':tp[sm.TYP],'name':tp[sm.NM],'source':tp[sm.SRC]}
		return json.dumps(cnf, ensure_ascii=False, indent=2, sort_keys=True)

	def serving(self, qid, smItem):
		''' get quantity attribute '''
		if qid in self._servmap:
			if smItem in self._servmap[qid]:
				return self._servmap[qid][smItem]
		return None
	
	def qactive(self):
		''' list of active quantities i.e. known and not secluded '''
		return (qid for qid in self._servmap if self.qIsActive(qid))
		#(self._servmap[qid][sm.TYP] < DEVT['secluded']) and not self._servmap[qid][sm.NM].startswith("nk."))
	
	def qname(self, qid):
		''' quantity name '''
		return self.serving(qid, sm.NM)
	def qsrc(self, qid):
		''' quantity source or location '''
		return self.serving(qid, sm.SRC)
	def qtype(self, qid):
		''' quantity type as defined in DEVT '''
		return self.serving(qid, sm.TYP)
	def qdevadr(self, qid):
		''' quantity devadr '''
		return self.serving(qid, sm.ADR)
	
	def qIsActive(self, qid):
		if qid and qid>0 and qid in self._servmap:
			if self._servmap[qid][sm.SRC] and self._servmap[qid][sm.TYP] < DEVT["secluded"]:
				if sm.MSK in self._servmap[qid]:
					return not self._servmap[qid][sm.MSK] # disable those with "mask":0
				if sm.NM in self._servmap[qid]:
					return not self._servmap[qid][sm.NM].startswith("nk.") # disable new created
				return True
		return False  # not known

	def qIsCounting(self, qid):
		''' is not analog but just an incrementing counter '''
		return self.qtype(qid) in qCOUNTING
	
	def qInRng(self, qid, value):
		qtp = self.qtype(qid)
		if qtp in DVrng and isinstance(value, (float,int)):
			if value<DVrng[qtp][0]:
				return False
			if value>DVrng[qtp][1]:
				return False
			return True
		return None

	def sinceAccept(self,qid=None):
		''' time diff [s] since qid was last accepted or least from all qs
		'''
		if qid in self._tAccept:
			return time.time()-self._tAccept[qid]
		if len(self._tAccept)>0:
			tmn = 0.0
			for qid,t in self._tAccept.items():
				if t<tmn:
					tmn=t
			return time.time()-tmn
		else:
			return 999
	
	def sinceStamp(self,qid=None):
		''' time diff [s] since previous sample of qid '''
		if qid and qid in self._actual:
			trun = time.time() - self._actual[qid][qSTMP]
		elif qid and qid in self.average:
			trun = time.time() - self.average[qid][qSTMP]
		elif self._actual and qid is None:
			trun = time.time() - max([qv[qSTMP] for q,qv in self._actual.items()])
		else:
			trun =None
		return trun
		
	#abstractmethod
	async def receive_message(self, dt:datetime=None) -> float:
		''' read device state and call check_quantity 
			main entry for fsHapper for polling interface for each sampler '''
		if dt is None:
			dt = sampleCollector.dtStart
		tdelt = datetime.now()-dt
		return tdelt.total_seconds()
	
	def check_quantity(self,tstamp,quantity,val):
		''' filters, validates, averages, checks, quantity results
		 calls accept_result when quantity rules are fullfilled
		 to be called by receive_message if a new quantity value has been received '''
		if quantity is None:
			return
		if quantity not in self._servmap:
			logger.info("unknown quantity:%s val=%s in %s" % (quantity,val,self.manufacturer))
			#self.servmap[quantity] = {'typ':DEVT['unknown']}
			return
		if not isinstance(val, (float,int)):
			logger.warning("val not numeric:{} for:{}".format(val,quantity))
			return
		if self.qtype(quantity)>=DEVT['secluded']:	# ignore
			return
		if isinstance(val, collections.Sequence):
			logger.warning('not numeric %d = %s' % (quantity,val))
		if val is None or self.qInRng(quantity,val)==False:
			logger.warning("quantity {} typ:{} out of range with {}".format(quantity,self.qtype(quantity),val))
			return
		else:
			self._actual[quantity] = {qVAL:val, qSTMP:tstamp}

		if sampleCollector.signaller:
			if sampleCollector.signaller.checkEvent(quantity, val):  # handle event by polling
				sampleCollector.signaller.signal(quantity, val)
		if self.qIsCounting(quantity): 
			if quantity in self.average:   # and val>0: # only first and pos edge
				if val>0:
					self.average[quantity][qVAL] += val
				elif self.average[quantity][qVAL]==0:  # !!! some bool types only give false values 
					#self.average[quantity][qVAL] +=1
					logger.info("not counting falses for {} cnt={}".format(quantity,self.average[quantity][qCNT]))
				self.average[quantity][qCNT] +=1
			else: 
				self.average[quantity] = [1,1,tstamp]   # first counting val  [qVAL,qCNT,qSTMP]
			if self.sinceAccept(quantity)>sampleCollector.mintinterval:
				self.accept_result(tstamp, quantity)
				logger.info('(%s) cnt val=%s quantity=%s tm=%s since=%.6g' % (quantity,val, self.qname(quantity), prettydate(julianday(tstamp)), self.sinceAccept(quantity)))
			else:
				logger.info('{}={} rejected mintinterval={}'.format(quantity,val,self.sinceAccept(quantity)))
					
		elif quantity in self.average:
			self.average[quantity][qVAL] += val
			self.average[quantity][qCNT] += 1
			n = self.average[quantity][qCNT]
			avg = self.average[quantity][qVAL] / n
			if (n>=self.minNr and abs(val-avg)>abs(avg*self.minDevPerc/100)) or n>=self.maxNr:
				logger.info('(%s) n=%d avg=%g val=%s quantity=%s devPrc=%g>%g tm=%s since=%.6g' % (quantity,n,avg,val, self.qname(quantity), abs(val-avg)/avg*100 if avg>0 else 0.0, self.minDevPerc, prettydate(julianday(tstamp)), self.sinceAccept(quantity)))
				tm = (tstamp+self.average[quantity][qSTMP])/2
				if self.sinceAccept(quantity)>sampleCollector.mintinterval:
					self.accept_result(tm, quantity)
				else:
					logger.info('{}={} rejected mintinterval={}'.format(quantity,val,self.sinceAccept(quantity)))
				#del self.average[quantity]
				self.average[quantity] = [val,1,tstamp]
			else:
				if abs(avg)>0 and self.debug:
					logger.debug('quantity:%d avgCount:%d devperc:%.6g ' % (quantity,self.average[quantity][qCNT], (val-avg)/avg*100) )
		else:  # first avg val
			self.average[quantity] = [val,1,tstamp]
			if self.maxNr<=1:
				self.accept_result(tstamp, quantity)
				logger.info('accepting one val=%s quantity=%s(%s) tm=%s' % (val,self.qname(quantity),quantity, prettydate(julianday(tstamp))))
	
	def accept_result(self,tstamp,quantity):
		''' process and stores the (averaged) result and init new avg period '''
		qval=None
		if self.qIsCounting(quantity):
			qval = self.average[quantity][qVAL]   # must have some positives edges
			self.average[quantity][qVAL]=0
			rec = self.average[quantity]
		elif self.average[quantity][qCNT]>0:
			rec=self.average.pop(quantity)
			qval = rec[qVAL]/rec[qCNT]
		if qval:
			self._lastval[quantity] = qval
			self._updated.add(quantity)
			self._tAccept[quantity] = time.time()
		if self.debug:
			logger.debug("accepted %s=%s tm=%s n=%d" % (quantity, qval, prettydate(julianday(tstamp)), rec[qCNT] ))
		return qval
		
	def set_state(self, quantity, state, prop=None, dur=None):
		''' stateSetter to operate actuator; used as callback for trigger events '''
		if quantity in self._servmap:
			logger.info('setting %s to %s with %s in %s' % (quantity, state, prop, self.manufacturer))
			return True
		return False
		# implemented by derived classes
		
	def get_state(self, quantity):
		''' get averaged or counted value of quantity since last accept '''
		qval=None
		if quantity in self.average:
			rec =self.average[quantity]
			if self.qIsCounting(quantity):
				qval = rec[qVAL]
			else:
				qval = rec[qVAL]/rec[qCNT]
			#self.updated.discard(quantity)
		elif quantity in self._actual:
			qval = self._actual[quantity][qVAL]
		elif self.qIsCounting(quantity):
			qval=0	# initial val for HAP
		else:
			rec = self.dbStore.fetchlast(quantity)
			if rec:
				qval = rec['numval']  #[qCNT]
		return qval
		
	def isUpdated(self, quantity):
		''' quantity value has changed since get_last call '''
		if self.qIsCounting(quantity) and quantity in self.average and self.average[quantity][qCNT]>0:
			trun = time.time() - self.average[quantity][qSTMP]
			#logger.debug("qcnt:%s trun=%s" % (quantity,trun))
			if trun > 60:  # assume counting quantity updated
				rec =self.average.pop(quantity)
				self._lastval[quantity] = 0
				self._updated.add(quantity)
				logger.debug('assume counting qid=%s rec=%s' % (quantity,rec))
		return quantity in self._updated
		
	def get_last(self, quantity):
		''' last accepted and averaged result '''
		self._updated.discard(quantity)
		return self._lastval[quantity]	
		
	async def eventListener(self, signaller):
		""" virtual: to be overriden; should wait indefinitely for events e.g. on webSocket
		"""
		logger.info('%s waiting for events in eventListener to:%s' % (self.name, signaller))
		#signaller.signal(qid, val)
		
		
	""" should not depend on HAP here 
	def create_accessory(self, HAPdriver, qname, quantity, qtyp, stateSetter, aid, samplername):
		return HAP_accessory(HAPdriver, qname, quantity=quantity, typ=qtyp,  stateSetter=stateSetter, aid=aid, receiver=samplername)
	"""

class DBsampleCollector(sampleCollector):
	""" adds database logging """
	_dbStore=None
	@property
	def dbStore(self):
		return DBsampleCollector._dbStore
		return type(self)._dbStore
		
	def __init__(self, dbFile,  *args, quantities={}, **kwargs):
		super().__init__(*args, **kwargs)
		if dbFile and DBsampleCollector._dbStore is None:
			logger.info("opening dbStore for:{} with nqs:{}".format(self.name, len(quantities)))
			DBsampleCollector._dbStore = sqlLogger(dbFile)
		self.defServices(quantities)  # get _servmap
		logger.info('%s servmap:%s' % (self.name,self._servmap))
		for qid in self.qactive():
			name = self.qname(qid)
			src = self.qsrc(qid)
			if self.dbStore and name is not None and src:
				self.dbStore.additem(qid, name,src,self.qtype(qid))
				if name[:3] == 'nk:' and super().qname(qid): # nk: newly discovered
					logger.warning('changing qid:%d name:%s to %s' % (qid,name,super().qname(qid)))
					self.dbStore.updateitem(qid, super().qname(qid)) 

	def qname(self, quantity):
		if self.dbStore and self.qIsActive(quantity):  # quantity in self.qactive(): 
			nm = self.dbStore.qname(quantity)
		else:
			nm = super().qname(quantity)
		return nm
		
	def qsrc(self, qkey):
		src = super().qsrc(qkey)
		if src:
			return src
		if self.dbStore:
			return self.dbStore.qsource(qkey)
		else:
			return src
			
		
	def accept_result(self,tstamp,quantity):
		""" save accepted result to database """
		qval = super().accept_result(tstamp,quantity)
		if qval is not None:
			if self.qIsActive(quantity):  # in self.qactive():
				if qval>0 or not self.qIsCounting(quantity): 
					if self.dbStore:
						self.dbStore.logi(quantity,qval,tstamp=tstamp)
			else:
				logger.debug("warning q:{}={} not accepted:{} src:{}".format(quantity,qval, self.qname(quantity), self.qsrc(quantity)))
		return qval

	def exit(self):
		logger.error("exit samplecolletor for {}".format(self.name))
		logger.error("{} proposed json config:\n{}".format(self.name, self.jsonDump()))
		if self.dbStore: # might have multiple users
			pass 
			#self.dbStore.close()
