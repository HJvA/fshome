#!/usr/bin/env python3
""" general purpose storage handler e.g. for devices continuously spitting numeric values 
"""
from sqlite3 import connect,OperationalError
import logging
import os
import time
import enum
from lib.grtls import julianday

__author__ = "Henk Jan van Aalderen"
__version__ = "1.0.0"
__email__ = "hjva@notmail.nl"
__status__ = "Development"

class its(enum.IntEnum):
	SRC=0
	NAME=2
	KEY=1
	TYP=3

class txtLogger(object):
	""" handler for log messages in a text file
		base class for other number loggers
	"""
	def __init__(self, filepath):
		''' open file for logging'''
		self.items={}
		self.file=open(filepath, 'a+')
	def close(self):
		self.file.close()
		
	def backup(self):
		''' '''
		# lock db file first!
		# rclone copy -P /mnt/extssd/storage/fs20store.sqlite gdrive:/rpi-sync
		pass
	
	def logi(self, ikey, numval, strval=None, tstamp=None):
		if tstamp is None:
			tstamp=time.time()
		iname = self.qname(ikey)
		if numval:
			itemval=numval
			if strval:
				itemval += ','+strval
		else:
			itemval=strval
		self.file.write('%d\t%.6f\t%s\t%s\n' % (ikey,tstamp,iname,itemval))
		
	def log(self, iname, itemval, tstamp=None):
		''' append message/sample to the store '''
		if tstamp is None:
			tstamp=time.time()
		id = self.checkitem(iname)
		self.file.write('%d\t%.6f\t%s\t%s\n' % (id,tstamp,iname,itemval))
	
	def additem(self, ikey, iname, isource, itype=None):
		''' adds item type i.e. quantity descriptor '''
		isnew = ikey not in self.items
		self.items.update({ikey:(iname,isource,itype)})
		logger.debug('%slogitem %s,%s,%s with ikey=%s' % ("new " if isnew else "",iname,isource,itype,ikey))
		return isnew
	
	def sources(self, quantities=None):
		''' set of actual sources that have been saved to the store '''
		return set([tup[1] for id,tup in self.items.items() if quantities is None or tup[0] in quantities])
		
	def quantities(self, sources=None, prop=0):
		''' set of quantity properties: 0=name,1=source,2=typ '''
		return set([tup[prop] for id,tup in self.items.items() if len(tup)>prop and (sources is None or tup[1] in sources)])
		
	def quantity(self, source, typ):
		for ikey,tup in self.items.items():
			if tup[1]==source and tup[2] is not None and tup[2] % 100==typ:
				return ikey
				
	def qname(self, ikey):
		#if type(ikey)==string and ikey.isnumber():
		#	ikey=int(ikey)
		if ikey in self.items:
			return self.items[ikey][0]
		return "nk:%s" % ikey
		
	def qsource(self, ikey):
		if ikey in self.items:
			return self.items[ikey][1]
		return None
		
	def checkitem(self, iname, isource=None,itype=None, addUnknown=True):
		''' check whether item has been seen before, adds it if not 
			returns unique itemid
		'''
		ids=[]
		for ikey,val in self.items.items():
			if iname==val[0] and (itype is None or itype==val[2]):
				if isource is None:
					ids.append(ikey)
				elif isource==val[1]:
					return ikey
		if isource is None:
			return tuple(ids)  # multiple sources for same item
		if addUnknown:
			if len(self.items)>0:
				ikey = max(self.items.keys())+1
			else:
				ikey=100
			self.additem(ikey,iname,isource,itype)
			return ikey
		else:
			return -1
		
	def fetch(self, iname, daysback=100):
		''' gets filtered list of items from store '''
		ikey = self.checkitem(iname,addUnknown=False)
		self.file.flush()
		rfl = open(self.file.name,'r')
		after = time.time() - (daysback * 86400)
		buf=[]
		for ln in rfl:
			itms=ln.split('\t')
			if ikey==int(itms[0]) and after<float(itms[1]):
				buf.append(tuple(itms[1:])) # strip ikey
		return buf


class sqlLogger(txtLogger):
	""" keeper for log data in a (sqlite) database
	"""
	def __init__(self, store=':memory:'):
		''' create database if it does not exist
			loads previously seen items from quantities table
		'''
		if store[-1]!=':':
			store = os.path.expanduser(store)
		self.items={}
		if not os.path.isfile(store):  # => create database
			self.con=self.create(store)
		else:
			self.con=connect(store, check_same_thread=False)
			logger.info("opening sqlStore in %s with %s" % (store,self.con.isolation_level))
			with self.con:
				cur = self.con.cursor()
				""" SELECT quantity,name,source,type,COUNT(*) as cnt,AVG(numval) as avgval,MIN(ddJulian) jdFirst FROM logdat,quantities WHERE ID=quantity AND ddJulian>julianday('now')-1 GROUP BY source,quantity,name,type ORDER BY ID """
				sql = "SELECT qs.ID,qs.name,qs.source,qs.type,qt.unit FROM quantities AS qs LEFT JOIN quantitytypes AS qt ON qs.type=qt.ID WHERE qs.active;"
				try:
					cur.execute(sql)
				except OperationalError:
					cur.execute('ALTER TABLE quantities ADD COLUMN active INT DEFAULT 1;')
					cur.execute('ALTER TABLE quantities ADD COLUMN type INT;')
					cur.execute(sql)
					logger.exception("db error now adding 'type' field")
				rows=cur.fetchall()
				#cur.close()
			for rec in rows:
				super().additem(rec[0],rec[1],rec[2],rec[3])
				#self.items.update({rec[0]:(rec[1],rec[2],rec[3])})
	
	def create(self, fname):
		logger.info("creating sqlStore in %s" % fname)
		con=connect(fname, check_same_thread=False)	# will create file
		with con:
			cur = con.cursor()
			cur.execute('CREATE TABLE logdat( '
				'ddJulian REAL	NOT NULL,'
				'quantity INT  NOT NULL,'
				'numval	REAL,'
				'strval  TEXT);' )
			cur.execute('CREATE INDEX ld1 ON logdat(ddJulian,quantity);')
			cur.execute('CREATE TABLE quantities( '
				'ID	 INT PRIMARY KEY NOT NULL,'
				"name  TEXT NOT NULL,"
				"source TEXT,"
				"type  INT,"
				"active INT DEFAULT 1,"
				"firstseen REAL);")
			cur.execute("CREATE TABLE quantitytypes(ID INT PRIMARY KEY NOT NULL, name TEXT NOT NULL, unit TEXT);")
			cur.close()
		return con
	
	def close(self):
		logger.info("closing sqlStore")
		self.con.close()
		
	def execute(self, sql, params=None):
		''' list of tuples with field-vals '''
		with self.con:
			tm=time.perf_counter()
			cur = self.con.cursor()
			if params:
				cur.execute(sql, params)
			else:
				cur.execute(sql)
			recs = cur.fetchall()
			logger.debug("SQL:%s with(%s) run in %.3fs nrecs=%d" % (sql,params,time.perf_counter()-tm, len(recs)))
			return recs
		
	def fetch(self, name, daysback=100, source=None, fields='ddJulian,numval,strval,source'):
		''' fetch logged messages from the log store '''
		ids = self.checkitem(name,source,addUnknown=False)
		where =""
		if not source is None:
			where=" AND source='%s'" % source
		if isinstance(ids, tuple):
			where+=" AND quantity IN (%s)" % ','.join(map(str,ids))
		else: # len(ids)==1:
			where+=" AND quantity=%d" % ids
		
		sql ="SELECT %s FROM logdat,quantities " \
			"WHERE ID=quantity AND ddJulian>julianday('now')-? %s" \
			"ORDER BY ddJulian;" % (fields,where)
		return self.execute(sql, (daysback,))
		 
	
	def fetchlast(self, ikey):
		''' 
		sql = "SELECT ddJulian AS dd,numval,source,type,qu.name,qt.unit " \
			"FROM logdat AS ld,quantities AS qu,quantitytypes AS qt " \
			"WHERE qu.ID=ld.quantity AND ld.quantity=? AND qt.ID=qu.type " \
			"AND ddJulian=(SELECT MAX(ddJulian) FROM logdat WHERE quantity=?) LIMIT 1;"
		'''
		sql = "select ddJulian,numval,vq.name,source,vq.type,vq.unit " \
				"from logdat as ld inner join vwQuantities as vq on vq.ID=quantity " \
				"where quantity=? AND ddJulian in (select MAX(ddJulian) from logdat WHERE quantity=?)"
		recs = self.execute(sql, (ikey,ikey))
		if recs:
			rec = recs[0]
			return {'ddJulian':rec[0],'name':rec[2],'numval':rec[1], 'source':rec[3],'type':rec[4],'unit':rec[5]}
		return None
	
	def fetchavg(self, name, tstep=30, daysback=100, jdend=None, source=None):
		''' fetch logged messages from the log store 
			takes averaged numval of name over tstep minutes intervals'''
		ids = self.checkitem(name,source,addUnknown=False) # get all quantity ids for source
		logger.info("nm:%s src:%s ids:%s" % (name,source,ids))
		return self.fetchiavg(ids, tstep, daysback, jdend)
		
	def fetchiavg(self, ikey, tstep=30, daysback=100, jdend=None, source=None):
		''' fetch averaged interval values from the database, 
			takes averaged numval of name over tstep minutes intervals'''
		where =""
		if not source is None:
			where=" AND source='%s'" % source
		if isinstance(ikey, tuple):
			where+=" AND quantity IN (%s)" % ','.join(map(str,ikey))
		else: # len(ids)==1:
			where+=" AND quantity=%d" % ikey	
		if jdend is None:
			jdend=julianday()
		sql = "SELECT ROUND(ddJulian*?)/? AS dd,AVG(numval) AS nval,COUNT(*) AS cnt,source,type " \
			"FROM logdat AS ld,quantities AS qu " \
			"WHERE active AND qu.ID=ld.quantity AND ddJulian>? AND ddJulian<? %s " \
			"GROUP BY quantity,source,dd " \
			"ORDER BY ddJulian;" % (where,)
		try:
			interval=1440/tstep  # minutes per day = 1440
			return self.execute(sql, (interval,interval,jdend-daysback,jdend))
		except KeyboardInterrupt:
			raise
		except Exception:
			logger.exception("unknown!!!") # probably locked
						
	def fetchiiavg(self, ikey1,ikey2, tstep=30, daysback=100, jdend=None, source=None):
		''' fetch 2 numval quantities added,  from the database '''
		rec1 = self.fetchiavg(ikey1,tstep,daysback,jdend,source)
		rec2 = self.fetchiavg(ikey2,tstep,daysback,jdend,source)
		if rec1 is None or rec2 is None:
			return
		i2=0
		rslt=[]
		for rc1 in rec1:
			while len(rec2)>i2 and rec2[i2][0]<rc1[0]: # match ddJulian
				i2+=1
			if i2>=len(rec2) or len(rc1)<2 or len(rec2[i2])<2:
				continue
			rslt.append(list(rc1))
			#logger.info("adding recs:%s to %s",(rc1, rec2[i2]))
			rslt[-1][1] =rc1[1] + rec2[i2][1]  # add both ikey numvals
		return rslt
		
	def evtDescriptions(self, jdtill, ndays):
		''' get all event descriptions in ndays period '''
		sql = "SELECT ddJulian,descr FROM eventsLog " \
			" WHERE ddJulian>=? AND ddJulian<=? ORDER BY ddJulian;" 
		#interval=1440/tstep  # minutes per day = 1440
		return self.execute(sql, (jdtill-ndays,jdtill))

	def setEvtDescription(self, julDay, evtDescr, maxMinutesDiff=10.0, root=None):
		sql = "SELECT ddJulian,descr FROM eventsLog WHERE ABS(ddJulian-?)<? LIMIT 1;"
		recs = self.execute(sql, (julDay, maxMinutesDiff/1440.0));  # max minutes diff
		if recs:
			sql = "UPDATE eventsLog SET ddJulian=?,descr=? WHERE ddJulian=?;"
			self.execute(sql, (julDay,evtDescr + " ::%s" % root if root else "",recs[0][0]))
		else:
			sql = "INSERT INTO eventsLog (ddJulian,descr) VALUES (?,?);"
			self.execute(sql, (julDay,evtDescr + " ::%s" % root if root else ""))

	def statistics(self, ndays=10, flds="source,quantity,name,type"):
		''' queries database for quantity prevalence. keeps list of them internaly '''
		sql = "SELECT %s,COUNT(*) as cnt,AVG(numval) as avgval,MIN(ddJulian) jdFirst " \
			"FROM logdat,quantities WHERE ID=quantity AND ddJulian>julianday('now')-%d " \
			"GROUP BY %s ORDER BY ID;" % (flds,ndays,flds)
		recs= self.execute(sql)
		for rec in recs:
			if 'name' in rec and 'source' in rec:
				self.checkitem(rec.name, rec.source, rec.type)
		return recs
	
	def sources(self, quantities=None, minDaysBack=None):
		if minDaysBack is None and self.items:
			return super().sources(quantities)
		self.items={}
		recs = self.statistics(minDaysBack)
		logger.info('building sources :%s' % recs)
		for rec in recs:
			super().additem(ikey=rec[its.KEY], iname=rec[its.NAME], isource=rec[its.SRC], itype=rec[its.TYP])
		return super().sources(quantities)
	
	def logi(self, ikey, numval, strval=None, tstamp=None):
		''' save value to the database '''
		if tstamp is None:
			tstamp = round(time.time(),0)	# granularity 1s
		logger.debug('logging %s (%g) @jd:%.6f' % (self.qname(ikey),numval,julianday(tstamp)))
		try:
			self.execute('INSERT INTO logdat (ddJulian,quantity,numval) VALUES (?,?,?)', (julianday(tstamp),ikey,numval))
			if not strval is None:
				self.execute('UPDATE logdat SET strval="%s" WHERE ddJulian=? AND quantity=?' % strval,(julianday(tstamp),ikey))
		except OperationalError:
			logger.error("unable to update database with id:%d at jd:%.6f" % (ikey,julianday(tstamp)))
		except KeyboardInterrupt:
			raise
		except Exception:
			logger.exception("unknown !!!")

	def log(self, iname, numval, strval=None, source=None, tstamp=None):
		''' add a log message to the log store 
		creates quantity when it does not exist '''
		ikey = self.checkitem(iname,source)
		if ikey and ikey>0:
			self.logi(ikey, numval, strval, tstamp)
		else:
			logger.error("unknown quantity :%s at %s" % (iname,source))
		
	def additem(self, ikey, iname, isource, itype=None):
		''' add or update a quantity descriptor (will be called automatic for unknown quantities) '''
		isnew = super().additem(ikey,iname,isource,itype)
		recs = self.execute('SELECT name FROM quantities WHERE ID=?' ,(ikey,))
		if recs is None or len(recs)==0:
			isnew = True
			if isource is None:
				isource='NULL'
			else:
				isource='"%s"' % isource
			logger.warning('quantities create: %s %s with %s typ %s' % (ikey,iname,isource,itype))
			self.execute('INSERT INTO quantities (ID,name,source,type,firstseen) ' 
				'VALUES (%d,"%s",%s,%s,julianday("now"))' % (ikey,iname,isource,'NULL' if itype is None else itype))
		elif isnew:
			self.updateitem(ikey, iname, isource, itype)
		return isnew

	def updateitem(self, ikey, iname, isource=None, itype=None):
		logger.info('quantities update: %s %s with %s typ %s' % (ikey,iname,isource,itype))
		if iname:
			self.execute('UPDATE quantities SET name=? WHERE ID=?', (iname,ikey))
		if isource:
			self.execute('UPDATE quantities SET source=? WHERE ID=?', (isource,ikey))
		if itype:
			self.execute('UPDATE quantities SET type=? WHERE ID=?', (itype,ikey))

				
if __name__ == "__main__":		# for testing
	import random
	#os.remove('~/tstlogdata.db')
	logger = logging.getLogger()
	[logger.removeHandler(h) for h in logger.handlers[::-1]]
	logger.addHandler(logging.StreamHandler())	# use console
	logger.setLevel(logging.DEBUG)

	try:
		dbst = sqlLogger("~/tstlogdata.db")
		#dbst = txtLogger('logdata.txt')
		logger.info("testing dbLogger version %s" % dbst)
		while True:
			time.sleep(2)
			dbst.log('temp',25.0 * (1.01 -random.random()/50))
			dbst.log('volt', 233 * (1.01 -random.random()/50))
			print('.')			
	except KeyboardInterrupt:
		logger.warning("terminated by ctrl c")
	print('temperatures:',dbst.fetch('temp'))
	print('voltage:',dbst.fetch('volt'))	
	dbst.close()
	logger.critical('bye')
else:
	logger = logging.getLogger(__name__)	# get logger from main program
	