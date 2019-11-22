
""" generic template for sampler devices generating (averaged and filtered) data to be stored
"""

import logging,time,json
from lib.dbLogger import julianday,prettydate,sqlLogger
from lib.devConst import qCOUNTING,DEVT
logger = logging.getLogger(__name__)	# get logger from main program

async def forever(func, *args, **kwargs):
	''' run (await) function func over and over '''
	while (True):
		await func(*args, **kwargs)

class sampleCollector(object):
	""" base class for collection of sampling quantities """
	def __init__(self, *args, maxNr=120,minNr=2,minDevPerc=5.0,name=None, **kwargs):
		self.maxNr = maxNr
		self.minDevPerc = minDevPerc
		self.minNr = minNr
		self.average={}
		self.lastval={}
		self.actual={}
		self.minqid=None	# allow unknown quantities to be created if not None
		self.servmap={}
		if name is None:
			self.name=type(self).__name__ #hash(self)
		else:
			self.name=name
		self.updated=set() # quantities that have been updated and not accepted yet

	def __repr__(self):
		"""Return the representation of the sampler."""
		return 'name={} quantities={}>' \
			.format(self.name, {self.qname(qid):qid for qid in self.servmap})

	async def receive_message(self):
		''' read device state and call check_quantity '''
		return None
		
	def servicesmap(self,quantities):
		''' compute dict of recognised services from quantities config '''
		smap={}
		for qid,rec in quantities.items():
			if type(rec) is dict and qid.isnumeric():
				adr=rec['devadr'] if 'devadr' in rec else "%d" % (int(qid) % 100,)
				typ=rec['typ'] if 'typ' in rec else DEVT['unknown']
				nm =rec['name'] if 'name' in rec else "no:%s" % adr
				src =rec['source'] if 'source' in rec else ''
				smap[int(qid)]=(adr,typ,nm,src)
		return smap
		
	def qCheck(self,quantity,devadr,typ=None,name=None,source=None):
		''' get/update/create (unknown) quantity to self.servmap '''
		if not quantity:
			quantity=self.qid(devadr,typ)
		#if not quantity:
		#	quantity=self.qid(devadr)
		if typ and (typ>=DEVT['unknown'] or typ==DEVT['fs20']):
			typ=None
		if not source:
			source = self.qsrc(quantity)
		mp = [devadr,typ,name,source]
		if quantity in self.servmap:
			if self.qtype(quantity)==DEVT['secluded']:
				mp[1]=DEVT['secluded']
			mp = [itold if itnew is None else itnew for itnew,itold in zip(mp,self.servmap[quantity])]
		elif devadr:
			if not quantity and self.minqid:
				quantity = max(self.servmap)+1
				if quantity<self.minqid:
					quantity=self.minqid
				logger.info("creating quantity:%s = %s" % (quantity,mp))
		if mp[1] is None:
			mp[1]=DEVT['unknown']
		if quantity:
			self.servmap[quantity] = tuple(mp)
		return quantity
	
	def jsonDump(self):
		''' extract modified quantities config enhanced by newly discovered and more info'''
		cnf={}
		for qid,tp in self.servmap.items():
			cnf[qid] = {'devadr':tp[0],'typ':tp[1],'name':tp[2],'source':tp[3]}
		return json.dumps(cnf, ensure_ascii=False, indent=2, sort_keys=True)
			
	def qname(self, qkey):
		''' quantity name '''
		if qkey in self.servmap:
			return self.servmap[qkey][2]
		return None
	def qsrc(self, qkey):
		''' quantity source or location '''
		if qkey in self.servmap:
			return self.servmap[qkey][3]
		return None
	def qtype(self, qkey):
		''' quantity type as defined in DEVT '''
		return self.servmap[qkey][1]
	def qIsCounting(self, qkey):
		''' is not analog but just counter '''
		return self.qtype(qkey) in qCOUNTING
	def qid(self,devadr,typ=None):
		for quid,tp in self.servmap.items():
			if devadr==tp[0] and (typ is None or typ==tp[1]):
				return quid
		return None
			
	def check_quantity(self,tstamp,quantity,val):
		''' to be called by receive_message to assert actual quantity value;
		 filters quantity updates and 
		 calls accept_result to store and send it'''
		if quantity not in self.servmap:
			logger.debug("unknown quantity:%s val=%s in %s" % (quantity,val,self.name))
			#self.servmap[quantity] = {'typ':DEVT['unknown']}
			return
		if self.qtype(quantity)>=DEVT['secluded']:	# ignore
			return
		self.actual[quantity] = val
		if self.qIsCounting(quantity): 
			if quantity in self.average and val>0:
				self.average[quantity][0] += val
				self.average[quantity][1] +=1
			else:
				self.average[quantity] = [val,1,tstamp]
			self.accept_result(tstamp, quantity)
			logger.info('accepting cnt val=%s quantity=%s(%s) tm=%s' % (val,self.qname(quantity),quantity, prettydate(julianday(tstamp))))
		elif quantity in self.average:
			n = self.average[quantity][1]
			avg = self.average[quantity][0] / n
			if (n>=self.minNr and abs(val-avg)>avg*self.minDevPerc/100) or n>=self.maxNr:
				logger.info('(%s) accepting avg n=%d avg=%g val=%s quantity=%s devPrc=%g tm=%s' % (quantity,n,avg,val, self.qname(quantity), abs(val-avg)/avg*100 if avg>0 else 0.0, prettydate(julianday(tstamp))))
				self.accept_result((tstamp+self.average[quantity][2])/2, quantity)
				self.average[quantity] = [val,1,tstamp]
			else:
				self.average[quantity][0] += val
				self.average[quantity][1] += 1
		else:
			self.average[quantity] = [val,1,tstamp]
			if self.maxNr<=1:
				self.accept_result(tstamp, quantity)
				logger.info('accepting one val=%s quantity=%s(%s) tm=%s' % (val,self.qname(quantity),quantity, prettydate(julianday(tstamp))))
				
	def accept_result(self,tstamp,quantity):
		''' process the (averaged) result and init new avg period '''
		qval=None
		if self.qIsCounting(quantity):
			qval = self.average[quantity][0]
			self.average[quantity][0]=0
		elif self.average[quantity][1]>0:
			rec=self.average.pop(quantity)
			qval = rec[0]/rec[1]
		if qval:
			self.lastval[quantity] = qval
			self.updated.add(quantity)
		#logger.debug("accepted %s=%s tm=%s n=%d" % (quantity, qval, prettydate(julianday(tstamp)), rec[1]))
		return qval
		
	def set_state(self, quantity, state, prop=None):
		''' stateSetter to operate actuator '''
		pass	# implemented by derived classes
		
	def get_state(self, quantity):
		''' get averaged or counted value of quantity since last accept '''
		qval=None
		if quantity in self.average:
			rec =self.average[quantity]
			if self.qIsCounting(quantity):
				qval = rec[0]
			else:
				qval = rec[0]/rec[1]
			#self.updated.discard(quantity)
		elif quantity in self.actual:
			qval = self.actual[quantity]
		elif self.qIsCounting(quantity):
			qval=0	# initial val for HAP
		else:
			rec = self.dbStore.fetchlast(quantity)
			if rec:
				qval = rec[1]
		return qval
		
	def isUpdated(self, quantity):
		''' quantity value has changed since get_last call '''
		if self.qIsCounting(quantity) and quantity in self.average and self.average[quantity][1]>0:
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
		self.inkeys=[] 
		self.servmap = self.servicesmap(quantities)
		logger.info('servmap:%s' % self.servmap)
		if self.servmap:
			for qid in self.servmap:
				if qid>0 and self.qtype(qid)<DEVT['secluded']:
					name = self.qname(qid)
					src = self.qsrc(qid)
					if self.dbStore and name is not None and src:
						self.dbStore.additem(qid, name,src,self.qtype(qid))
					self.inkeys.append(qid)

		
	def qname(self, quantity):
		#nm = "qn:%s" % quantity
		if quantity in self.inkeys:
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
		qval=super().accept_result(tstamp,quantity)
		if qval is not None:
			if quantity in self.inkeys:
				if qval>0 or not self.qIsCounting(quantity): 
					if self.dbStore:
						self.dbStore.logi(quantity,qval,tstamp=tstamp)
			else:
				logger.debug("warning q:%s not in dbkeys %s" % (quantity,self.inkeys))
		return qval

	def exit(self):
		logger.error("%s proposed json config:\n%s" % (self.name, self.jsonDump()))
		if self.dbStore:
			self.dbStore.close()