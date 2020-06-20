
""" generic template for sampler devices generating (averaged and filtered) data to be stored
"""

import logging,time,json,enum,re,datetime
import collections
import asyncio
from lib.dbLogger import julianday,prettydate,sqlLogger
from lib.devConst import qCOUNTING,DEVT,DVrng
logger = logging.getLogger(__name__)	# get logger from main program

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
	TYP=1 # DEVT
	NM=2  # name
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
	reSIGPTRN = r"(?:[=|\,])*(\d+\.*\d*)"
	def __init__(self):
		self._eventDetect={}
		self._signalDef={}
		self._handlers={}
		logger.info('setting signaller for %s' % type(self).__name__)
		
	def setSignalDef(self, requester, qid, defstr):
		''' if qid occurs then signal will be called to do defstr '''
		sdef=defstr.split('->')
		if len(sdef)>1:
			self._eventDetect[qid]=sdef[0]
		self._signalDef[qid] = sdef[-1]
		logger.info('signal %s on detection ch:%s of %s' % (defstr,qid,requester))
		
	def checkEvent(self, qid, qval):
		''' todo check whether qid event is occuring '''
		if qid in self._eventDetect:
			logger.warning('TODO: checking qid:%s with %s for having %s' % (qid,qval,self._eventDetect[qid]))
		if type(qval) is bool:
			return qval  # only trigger once on motion detect
		return True
		
	def signal(self, qid, qval=None):
		''' qid has occured, now look if a signaldef is attached, then execute it '''
		if qid in self._signalDef:
			sdef=self._signalDef[qid]  #.split('->')[-1]  # get cmd to execute after -> if there
			mch = re.compile(signaller.reSIGPTRN).finditer(sdef)
			if mch:
				lst =[float(x.group(1)) for x in mch] 
				lst += [None]*(4-len(lst))
				trgqid,trgval,trgprop,trgdur = lst
				trgqid=int(trgqid)
				#else:
				#	trgqid,trgval,trgprop,trgdur = (0,None,None,None)
				logger.info('signalling %s=%s with %s => %s' % (qid,qval,sdef,lst))
				for hnd,cb in self._handlers.items():  # check all handlers till acq
					if cb(trgqid, trgval, trgprop, trgdur):
						break
				else:
					logger.warning('qid -> trg not handled:%s -> %s' % (qid,sdef))
		else:
			#logger.warning('qid %s has no event handler' % qid)
			pass

	def registerStateSetter(self, handler, setStateCallback):
		''' typically called by sampleCollector class to register its set_state method 
			handler = name of actual sampleCollector class
		'''
		logger.info('%ssetting signaller callback for %s' % ("RE-" if handler in self._handlers else "" , handler))
		self._handlers[handler] = setStateCallback  # !!!
		
	def registerEventSource(self, handler, eventSrc):
		asyncio.create_task(eventSrc.eventListener(signaller=self))

class sampleCollector(object):
	""" base class for collection of sampling quantities """
	signaller = None # each sampler will have its own signaller set by childs
	objCount=0
	dtStart = datetime.datetime.now()
	@property
	def manufacturer(self):
		return self.name

	def __init__(self, maxNr=120,minNr=2,minDevPerc=5.0,name=None):
		self.maxNr = maxNr
		self.minDevPerc = minDevPerc
		self.minNr = minNr
		self.average={}
		self.lastval={}
		self.actual={}
		self.minqid=None	# allow unknown quantities to be created if not None
		self._servmap={}
		sampleCollector.objCount+=1
		if name is None:
			self.name=type(self).__name__ + "_%d" % sampleCollector.objCount		# name of class
		else:
			self.name=name
		logger.info('%s sampler minNr=%d maxNr=%d minDevPerc=%.5g' % (self.name,minNr,maxNr,minDevPerc))
		self.updated=set() # quantities that have been updated and not accepted yet
		self.tAccept = {}
		#self.dtStart = datetime.datetime.now()
		#self.defSignaller()

	def __repr__(self):
		"""Return the representation of the sampler."""
		return 'name={} quantities={}>' \
			.format(self.name, {self.qname(qid):qid for qid in self._servmap})
	
	def defSignaller(self, forName=None):
		if not sampleCollector.signaller:
			sampleCollector.signaller = signaller()
		if forName is None:
			forName = self.name  # unique for each sampler
		sampleCollector.signaller.registerStateSetter(forName, self.set_state)
		
	
	def defServices(self,quantitiesConfig):
		''' compute dict of recognised services from quantities config => self._servmap '''
		for qid,rec in quantitiesConfig.items():
			if type(rec) is dict and qid.isnumeric():
				adr=rec['devadr'] if 'devadr' in rec else "%d" % (int(qid) % 100,)
				typ=rec['typ'] if 'typ' in rec else DEVT['unknown']
				if type(typ) is str:
					typ = DEVT[typ]
				nm =rec['name'] if 'name' in rec else "no:%s" % adr
				src =rec['source'] if 'source' in rec else ''
				self._servmap[int(qid)]={sm.ADR:adr,sm.TYP:typ,sm.NM:nm,sm.SRC:src}
				if 'mask' in rec:
					logger.info('masking :%s for qid:%s' % (rec['mask'],qid))
					self._servmap[int(qid)][sm.MSK] = rec['mask']
				if 'signal' in rec:
					if self.signaller:
						self.signaller.setSignalDef(self.name, int(qid), rec['signal'])
					#self.servmap[int(qid)][sm.SIG] = rec['signal']
		return self._servmap
		
	def nAvgSamps(self, qid):
		if qid in self.average:
			return self.average[qid][qCNT]
		return None
		
	def qCheck(self,quantity,devadr,typ=None,name=None,source=None):
		''' check whether quantity with devadr,typ,name,source attributes exists in servmap;
			creates or updates (unknown) quantity to self._servmap '''
		if not quantity:
			quantity=self.qid(devadr,typ)
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
			if devadr:
				if not quantity and self.minqid:
					quantity = max(self._servmap)+1
					if quantity<self.minqid:
						quantity=self.minqid
					logger.info("%s creating quantity:%s = %s" % (self.manufacturer,quantity,mp))
		if mp[sm.TYP] is None:
			mp[sm.TYP]=DEVT['unknown']
		if quantity:
			self._servmap[quantity] = mp
		return quantity
	
	def jsonDump(self):
		''' extract modified quantities config enhanced by newly discovered and more info'''
		cnf={}
		for qid,tp in self._servmap.items():
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
		return (qid for qid in self._servmap if qid>0 and self._servmap[qid][sm.TYP] < DEVT['secluded'])

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

	def qIsCounting(self, qid):
		''' is not analog but just counter '''
		return self.qtype(qid) in qCOUNTING
	def qid(self,devadr,typ=None):
		''' search for qkey of quantity having devadr and or typ '''
		for quid,tp in self._servmap.items():
			if (devadr==tp[sm.ADR] or tp[sm.ADR] == '%s' % devadr) and (typ is None or typ==tp[sm.TYP]):
				return quid
		return None
	def qInRng(self, qid, value):
		if qid in DVrng:
			if value<DVrng[qid][0]:
				return False
			if value>DVrng[qid][1]:
				return False
			return True
		return None

	def sinceAccept(self,qid=None):
		''' time since qid was last accepted or least from all qs
		'''
		if qid in self.tAccept:
			return time.time()-self.tAccept[qid]
		if len(self.tAccept)>0:
			tmn = 0.0
			for qid,t in self.tAccept.items():
				if t<tmn:
					tmn=t
			return time.time()-tmn
		else:
			return 999
	
	def sinceStamp(self,qid=None):
		''' time since previous sample of qid '''
		if qid and qid in self.actual:
			trun = time.time() - self.actual[qid][qSTMP]
		elif qid and qid in self.average:
			trun = time.time() - self.average[qid][qSTMP]
		elif self.actual and qid is None:
			trun = time.time() - min([qv[qSTMP] for q,qv in self.actual.items()])
		else:
			trun =None
		return trun

	async def receive_message(self, dt=None):
		''' read device state and call check_quantity '''
		if dt is None:
			dt = sampleCollector.dtStart
		tdelt = datetime.datetime.now()-dt
		return tdelt.total_seconds()
	
	def check_quantity(self,tstamp,quantity,val):
		''' filters, validates, averages, checks, quantity results
		 calls accept_result when quantity rules are fullfilled
		 to be called by receive_message  '''
		if quantity not in self._servmap:
			logger.info("unknown quantity:%s val=%s in %s" % (quantity,val,self.manufacturer))
			#self.servmap[quantity] = {'typ':DEVT['unknown']}
			return
		if self.qtype(quantity)>=DEVT['secluded']:	# ignore
			return
		if isinstance(val, collections.Sequence):
			logger.warning('not numeric %d = %s' % (quantity,val))
		if self.qInRng(quantity,val)==False:
			logger.warning("quantity out of range %s" % quantity)
			return
		else:
			self.actual[quantity] = {qVAL:val, qSTMP:tstamp}

		if sampleCollector.signaller:
			if sampleCollector.signaller.checkEvent(quantity, val):
				sampleCollector.signaller.signal(quantity, val)
		if self.qIsCounting(quantity): 
			if quantity in self.average and val>0: # only first and pos edge
				self.average[quantity][qVAL] += val
				self.average[quantity][qCNT] +=1
			else:
				self.average[quantity] = [val,1,tstamp]
			self.accept_result(tstamp, quantity)
			logger.info('(%s) accepting cnt val=%s quantity=%s tm=%s since=%.6g' % (quantity,val, self.qname(quantity), prettydate(julianday(tstamp)), self.sinceAccept(quantity)))
		elif quantity in self.average:
			n = self.average[quantity][qCNT]
			avg = self.average[quantity][qVAL] / n
			if (n>=self.minNr and abs(val-avg)>abs(avg*self.minDevPerc/100)) or n>=self.maxNr:
				logger.info('(%s) accepting avg n=%d avg=%g val=%s quantity=%s devPrc=%g>%g tm=%s since=%.6g' % (quantity,n,avg,val, self.qname(quantity), abs(val-avg)/avg*100 if avg>0 else 0.0, self.minDevPerc, prettydate(julianday(tstamp)), self.sinceAccept(quantity)))
				self.accept_result((tstamp+self.average[quantity][qSTMP])/2, quantity)
				self.average[quantity] = [val,1,tstamp]
			else:
				self.average[quantity][qVAL] += val
				self.average[quantity][qCNT] += 1
				if abs(avg)>0:
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
			qval = self.average[quantity][qVAL]
			self.average[quantity][qVAL]=0
		elif self.average[quantity][qCNT]>0:
			rec=self.average.pop(quantity)
			qval = rec[qVAL]/rec[qCNT]
		if qval:
			self.lastval[quantity] = qval
			self.updated.add(quantity)
			self.tAccept[quantity] = time.time()
		#logger.debug("accepted %s=%s tm=%s n=%d" % (quantity, qval, prettydate(julianday(tstamp)), rec[1]))
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
		elif quantity in self.actual:
			qval = self.actual[quantity][qVAL]
		elif self.qIsCounting(quantity):
			qval=0	# initial val for HAP
		else:
			rec = self.dbStore.fetchlast(quantity)
			if rec:
				qval = rec[qCNT]
		return qval
		
	def isUpdated(self, quantity):
		''' quantity value has changed since get_last call '''
		if self.qIsCounting(quantity) and quantity in self.average and self.average[quantity][qCNT]>0:
			trun = time.time() - self.average[quantity][qSTMP]
			#logger.debug("qcnt:%s trun=%s" % (quantity,trun))
			if trun > 60:  # assume counting quantity updated
				rec =self.average.pop(quantity)
				self.lastval[quantity] = 0
				self.updated.add(quantity)
				logger.debug('assume counting qid=%s rec=%s' % (quantity,rec))
		return quantity in self.updated
		
	def get_last(self, quantity):
		''' last accepted and averaged result '''
		self.updated.discard(quantity)
		return self.lastval[quantity]	
		
	""" should not depend on HAP here 
	def create_accessory(self, HAPdriver, qname, quantity, qtyp, stateSetter, aid, samplername):
		return HAP_accessory(HAPdriver, qname, quantity=quantity, typ=qtyp,  stateSetter=stateSetter, aid=aid, receiver=samplername)
	"""

class DBsampleCollector(sampleCollector):
	""" adds database logging """
	def __init__(self, dbFile,  *args, quantities={}, **kwargs):
		super().__init__(*args, **kwargs)
		if dbFile:
			self.dbStore = sqlLogger(dbFile)
		else:
			self.dbStore = None
		#self.inkeys=[] 
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
		if quantity in self.qactive(): 
			nm = self.dbStore.qname(quantity)
		else:
			nm = super().qname(quantity)
		return nm
		
	def qsrc(self, qkey):
		src = super().qsrc(qkey)
		if src:
			return src
		return self.dbStore.qsource(qkey)
		
	def accept_result(self,tstamp,quantity):
		qval = super().accept_result(tstamp,quantity)
		if qval is not None:
			if quantity in self.qactive():
				if qval>0 or not self.qIsCounting(quantity): 
					if self.dbStore:
						self.dbStore.logi(quantity,qval,tstamp=tstamp)
			else:
				logger.debug("warning q:%s not in dbkeys %s" % (quantity,self._servmap))
		return qval

	def exit(self):
		logger.error("%s proposed json config:\n%s" % (self.name, self.jsonDump()))
		if self.dbStore:
			self.dbStore.close()
