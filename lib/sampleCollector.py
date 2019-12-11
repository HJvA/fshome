
""" generic template for sampler devices generating (averaged and filtered) data to be stored
"""

import logging,time,json,enum,re
from lib.dbLogger import julianday,prettydate,sqlLogger
from lib.devConst import qCOUNTING,DEVT
logger = logging.getLogger(__name__)	# get logger from main program

async def forever(func, *args, **kwargs):
	''' run (await) function func over and over '''
	while (True):
		await func(*args, **kwargs)

# index to self.average[]
qVAL=0
qCNT=1

class sm(enum.IntFlag):
	ADR=0	# devadr
	TYP=1
	NM=2
	SRC=3	# source
	MSK=4
	SIG=5	# signaller spec
	
class signaller(object):
	""" actuator for trigger events """
	reSIGDEF = r"^(\d+)\=(\d+\.*\d*)"
	def __init__(self):
		self._signalDef={}
		self._handlers={}
		logger.info('setting signaller for %s' % type(self).__name__)
	def setSignalDef(self, requester, qid, defstr):
		self._signalDef[qid] = defstr
		logger.info('signal %s on detection ch:%s of %s' % (defstr,qid,requester))

	def signal(self, qid, qval=None):
		if qid in self._signalDef:
			sdef=self._signalDef[qid]
			mch = re.search(signaller.reSIGDEF, sdef)
			if mch:
				trgqid,trgval,trgprop = (int(mch.group(1)),float(mch.group(2)),None)
			else:
				trgqid,trgval,trgprop = (0,None,None)
			logger.info('signalling %s=%s on %s' % (qid,qval,sdef))
			for hnd,cb in self._handlers.items():
				if cb(trgqid, trgval, trgprop):
					break
			else:
				logger.debug('qid -> trg not handled:%s -> %s' % (qid,trgqid))
		else:
			#logger.warning('qid %s has no event handler' % qid)
			pass

	def registerStateSetter(self, handler, setStateCallback):
		logger.info('setting signaller callback for %s' % (handler))
		self._handlers[handler] = setStateCallback

class sampleCollector(object):
	""" base class for collection of sampling quantities """
	signaller = None # signaller()
	def __init__(self, *args, maxNr=120,minNr=2,minDevPerc=5.0,name=None, **kwargs):
		self.maxNr = maxNr
		self.minDevPerc = minDevPerc
		self.minNr = minNr
		#self.signaller = signaller
		self.average={}
		self.lastval={}
		self.actual={}
		self.minqid=None	# allow unknown quantities to be created if not None
		self._servmap={}
		if name is None:
			self.name=type(self).__name__ #hash(self)
		else:
			self.name=name
		if not sampleCollector.signaller:
			sampleCollector.signaller = signaller()
		sampleCollector.signaller.registerStateSetter(self.name, self.set_state)
		self.updated=set() # quantities that have been updated and not accepted yet

	def __repr__(self):
		"""Return the representation of the sampler."""
		return 'name={} quantities={}>' \
			.format(self.name, {self.qname(qid):qid for qid in self._servmap})

	async def receive_message(self):
		''' read device state and call check_quantity '''
		return None
		
	def defServices(self,quantitiesConfig):
		''' compute dict of recognised services from quantities config in servmap '''
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
					logger.info('diginp bit:%d for ch:%s' % (rec['mask'],qid))
					self._servmap[int(qid)][sm.MSK] = rec['mask']
				if 'signal' in rec:
					if self.signaller:
						self.signaller.setSignalDef(self.name, int(qid), rec['signal'])
					#self.servmap[int(qid)][sm.SIG] = rec['signal']
		return self._servmap
		
	def qCheck(self,quantity,devadr,typ=None,name=None,source=None):
		''' check whether quantity with devadr,typ,name,source attributes exists in servmap;
			creates or updates (unknown) quantity to self.servmap '''
		if not quantity:
			quantity=self.qid(devadr,typ)
		if typ and (typ>=DEVT['unknown'] or typ==DEVT['fs20']):
			typ=None
		if not source:
			source = self.qsrc(quantity)
		#mp = [devadr,typ,name,source]
		mp = {sm.ADR:devadr, sm.TYP:typ, sm.NM:name, sm.SRC:source}
		if quantity in self._servmap:
			if self.qtype(quantity)==DEVT['secluded']:
				mp[sm.TYP]=DEVT['secluded']
			#mp = [itold if itnew is None else itnew for itnew,itold in zip(mp,self.servmap[quantity])]
			mp = {smi:mp[smi] if smi in mp and mp[smi] is not None else it for smi,it in self._servmap[quantity].items() }
		elif devadr:
			if not quantity and self.minqid:
				quantity = max(self._servmap)+1
				if quantity<self.minqid:
					quantity=self.minqid
				logger.info("creating quantity:%s = %s" % (quantity,mp))
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
			return self._servmap[qid][smItem]
		return None
	def qactive(self):
		''' list of active quantities '''
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
	
	def check_quantity(self,tstamp,quantity,val):
		''' filters, validates, averages, checks, quantity results
		 calls accept_result when quantity rules are fullfilled
		 to be called by receive_message  '''
		if quantity not in self._servmap:
			logger.info("unknown quantity:%s val=%s in %s" % (quantity,val,self.name))
			#self.servmap[quantity] = {'typ':DEVT['unknown']}
			return
		if self.qtype(quantity)>=DEVT['secluded']:	# ignore
			return
		self.actual[quantity] = val
		if sampleCollector.signaller:
			sampleCollector.signaller.signal(quantity, val)
		if self.qIsCounting(quantity): 
			if quantity in self.average and val>0: # only first and pos edge
				self.average[quantity][qVAL] += val
				self.average[quantity][qCNT] +=1
			else:
				self.average[quantity] = [val,1,tstamp]
			self.accept_result(tstamp, quantity)
			logger.info('(%s) accepting cnt val=%s quantity=%s tm=%s' % (quantity,val,self.qname(quantity), prettydate(julianday(tstamp))))
		elif quantity in self.average:
			n = self.average[quantity][qCNT]
			avg = self.average[quantity][qVAL] / n
			if (n>=self.minNr and abs(val-avg)>avg*self.minDevPerc/100) or n>=self.maxNr:
				logger.info('(%s) accepting avg n=%d avg=%g val=%s quantity=%s devPrc=%g tm=%s' % (quantity,n,avg,val, self.qname(quantity), abs(val-avg)/avg*100 if avg>0 else 0.0, prettydate(julianday(tstamp))))
				self.accept_result((tstamp+self.average[quantity][2])/2, quantity)
				self.average[quantity] = [val,1,tstamp]
			else:
				self.average[quantity][qVAL] += val
				self.average[quantity][qCNT] += 1
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
		#logger.debug("accepted %s=%s tm=%s n=%d" % (quantity, qval, prettydate(julianday(tstamp)), rec[1]))
		return qval
		
	def set_state(self, quantity, state, prop=None):
		''' stateSetter to operate actuator; used as callback for trigger events '''
		logger.info('setting %s to %s with %s' % (quantity, state, prop))
		return quantity in self._servmap
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
			qval = self.actual[quantity]
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
			trun = time.time() - self.average[quantity][2]
			#logger.debug("qcnt:%s trun=%s" % (quantity,trun))
			if trun > 60:
				rec =self.average.pop(quantity)
				self.lastval[quantity] = 0
				self.updated.add(quantity)
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
		self.defServices(quantities)
		logger.info('servmap:%s' % self._servmap)
		for qid in self.qactive():
			name = self.qname(qid)
			src = self.qsrc(qid)
			if self.dbStore and name is not None and src:
				self.dbStore.additem(qid, name,src,self.qtype(qid))
			#self.inkeys.append(qid)

	def qname(self, quantity):
		#nm = "qn:%s" % quantity
		if quantity in self.qactive(): #inkeys:
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
