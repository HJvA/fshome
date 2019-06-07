#!/usr/bin/env python3
""" general purpose storage handler e.g. for devices continuously spitting numeric values 
"""
from sqlite3 import connect,OperationalError
import logging
import os
import time

__author__ = "Henk Jan van Aalderen"
__version__ = "1.0.0"
__email__ = "hjva@notmail.nl"
__status__ = "Development"


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
		
	def log(self, iname, itemval, tstamp=None):
		''' append message to the store '''
		if tstamp is None:
			tstamp=time.time()
		id = self.checkitem(iname)
		self.file.write('%d\t%.6f\t%s\t%s\n' % (id,tstamp,iname,itemval))
	
	def additem(self, ikey, iname, isource, itype=None):
		''' adds item type i.e. quantity descriptor '''
		self.items.update({ikey:(iname,isource,itype)})
		logger.debug('adding item %s,%s,%s with ikey=%s' % (iname,isource,itype,ikey))
	
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
		return self.items[ikey][1]
		
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
				self.items.update({rec[0]:(rec[1],rec[2],rec[3])})
	
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

		with self.con:
			cur = self.con.cursor()
			sql ="SELECT %s FROM logdat,quantities " \
			"WHERE ID=quantity AND ddJulian>julianday('now')-? %s" \
			"ORDER BY ddJulian;" % (fields,where)
			cur.execute(sql, (daysback,))
			return cur.fetchall()  # list of tuples with field-vals
	
	def fetchlast(self, ikey):
		''' '''
		sql = "SELECT ddJulian AS dd,numval,source,type " \
			"FROM logdat,quantities " \
			"WHERE ID=quantity AND quantity=? AND ddJulian=(SELECT MAX(ddJulian) FROM logdat WHERE quantity=?);"
		with self.con:
			cur = self.con.cursor()
			cur.execute(sql, (ikey,ikey))
			return cur.fetchone()
			
	def fetchavg(self, name, tstep=30, daysback=100, jdend=None, source=None):
		''' fetch logged messages from the log store 
			takes averaged numval of name over tstep minutes intervals'''
		ids = self.checkitem(name,source,addUnknown=False) # get all quantity ids for source
		logger.info("nm:%s src:%s ids:%s" % (name,source,ids))
		return self.fetchiavg(ids, tstep, daysback, jdend)
		
	def fetchiavg(self, ikey, tstep=30, daysback=100, jdend=None, source=None):
		''' fetch averaged interval values from the database '''
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
			"FROM logdat,quantities " \
			"WHERE active AND ID=quantity AND ddJulian>? AND ddJulian<? %s " \
			"GROUP BY quantity,source,dd " \
			"ORDER BY ddJulian;" % (where,)
		logger.info('sql:%s' % sql)
		try:
			interval=1440/tstep  # minutes per day = 1440
			with self.con:
				cur = self.con.cursor()
				cur.execute(sql, (interval,interval,jdend-daysback,jdend))
				return cur.fetchall()  # list of tuples with field-vals
		except KeyboardInterrupt:
			raise
		except Exception:
			logger.exception("unknown!!!") # probably locked
						
	def fetchiiavg(self, ikey1,ikey2, tstep=30, daysback=100, jdend=None, source=None):
		''' fetch averaged interval values from the database '''
		rec1 = self.fetchiavg(ikey1,tstep,daysback,jdend,source)
		rec2 = self.fetchiavg(ikey2,tstep,daysback,jdend,source)
		if rec1 is None or rec2 is None:
			return
		i2=0
		rslt=[]
		for rc1 in rec1:
			while rec2[i2][0]<rc1[0]:
				i2+=1
				if i2>=len(rec2):
					continue
			rslt.append(list(rc1))
			rslt[-1][1] =rc1[1] + rec2[i2][1]
		return rslt
					
	def statistics(self, ndays=10, flds="source,quantity,name,type"):
		''' queries database for quantity prevalence. keeps list of them internaly '''
		#cur = self.con.cursor()
		with self.con:
			sql = "SELECT %s,COUNT(*) as cnt,AVG(numval) as avgval,MIN(ddJulian) jdFirst FROM logdat,quantities WHERE ID=quantity AND ddJulian>julianday('now')-%d GROUP BY %s ORDER BY ID;" % (flds,ndays,flds)
			cur = self.con.cursor()
			cur.execute(sql)
			recs= cur.fetchall()
			for rec in recs:
				if 'name' in rec and 'source' in rec:
					self.checkitem(rec.name, rec.source, rec.type)
			return recs
	
	def logi(self, ikey, numval, strval=None, tstamp=None):
		''' save value to the database '''
		if tstamp is None:
			tstamp = round(time.time(),0)	# granularity 1s
		logger.debug('logging %s (%g) @jd:%.6f' % (self.qname(ikey),numval,julianday(tstamp)))
		#cur = self.con.cursor()
		try:
			with self.con as cur:
				cur.execute('INSERT INTO logdat (ddJulian,quantity,numval) VALUES (?,?,?)', (julianday(tstamp),ikey,numval))
				if not strval is None:
					cur.execute('UPDATE logdat SET strval="%s" WHERE ddJulian=? AND quantity=?' % strval,(julianday(tstamp),ikey))
		except OperationalError:
			logger.error("unable to update database with id:%d at jd:%.6f" % (ikey,julianday(tstamp)))
		except KeyboardInterrupt:
			raise
		except Exception:
			logger.exception("unknown !!!")
		#cur.close()
	
					
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
		super().additem(ikey,iname,isource,itype)
		with self.con:
			cur=self.con.cursor()
			cur.execute('SELECT name FROM quantities WHERE ID=%d' % ikey)
			if cur.fetchone() is None:
				if isource is None:
					isource='NULL'
				else:
					isource='"%s"' % isource
				cur.execute('INSERT INTO quantities (ID,name,source,type,firstseen) ' 
					'VALUES (%d,"%s",%s,%s,julianday("now"))' % (ikey,iname,isource,'NULL' if itype is None else itype))
			else: 
				logger.debug('db updating %s %s with %s typ %s' %(ikey,iname,isource,itype))
				cur.execute('UPDATE quantities SET name=?,source=?,type=? WHERE ID=%d' % ikey, (iname,isource,itype))
			#cur.close()
			#self.con.commit()

#some small helpers

def julianday(tunix = None):
	''' convert unix time i.e. seconds since 00:00:00 Thursday, 1 January 1970 to julianday i.e. days since noon on Monday, January 1 4713 BC '''
	if tunix is None:
		tunix = time.time()
	return (tunix / 86400.0 ) + 2440587.5
	
def localtime(julianday):
	return time.localtime(unixsecond(julianday))

def unixsecond(julianday):
	''' convert  julianday to '''
	return (julianday - 2440587.5) * 86400.0

def prettydate(julianday, format="%d %H:%M:%S"):
	''' generates string representation of julianday '''
	if format=="#j4":
		fd = int(4*(julianday % 1))
		return ('after noon','evening','night','morning')[fd]	
	return time.strftime(format, time.localtime(unixsecond(julianday)))

def SiNumForm(num):
	''' format number with SI prefixes '''
	pref = ['f','p','n','u','m',' ','k','M','G','T','P','E','Z','Y']
	mul=1e-15
	for pr in pref:
		if abs(num)/mul<999:
			break
		mul *= 1000
	return "{:4.3g}{}".format(num/mul,pr)

def prettyprint(fetchrecs):
	''' print the records fetched by fetch method to the console '''
	for tpl in fetchrecs:
		tm = prettydate(tpl[0])   
		print("%s %4.3g %s %s" % (tm,tpl[1],tpl[2],tpl[3]))

def graphyprint(fetchrecs, ddfrm = "%a %H:%M", xcol=0, ycol=1):
	''' print graphically to console selected quantity trace from database '''
	curve = [rec[ycol] for rec in fetchrecs]
	printCurve(curve)
	jdays = [rec[xcol] for rec in fetchrecs]
	printTimeAx(jdays)

def printTimeAx(jddata):
	''' print time x axis to console '''
	def diffxh(julday, hr24=0):
		julday -= 0.5
		julday += hr24/24.0
		julday -= time.timezone / 60 / 60 / 24
		return abs(round(julday)-julday)
	noon=-3
	print("=",end='')
	for i in range(len(jddata)-2):
		df = [diffxh(jd) for jd in jddata[i:i+3]]
		if df.index(min(df))==1:
			print("|",end='')
			logger.debug("marker@%s df:%s jd=%.5f" % (prettydate(jddata[i+1]),df,jddata[i+1]))
		elif df.index(max(df))==1:
			print(prettydate(jddata[i+1],"%a"),end='')
			noon=i+1
		elif i>noon+1:
			print("-",end='')
	print("=")
	

def printCurve(data, height=10, vmax=None, vmin=None, backgndchar=0x2581):
	''' print float data array graphically to console using block char fillings '''
	if data is None or len(data)==0:
		logger.error("no data to graph")	
		return
	if vmax is None: 
		vmax = max(data)
	if vmin is None: 
		vmin = min(data)
	if vmax==vmin:
		sf=1.0
	else:
		sf = (height-1)/(vmax-vmin)
	logger.info("curve min=%f max=%f sf=%f" % (vmin,vmax,sf))
	for ln in range(height-1,-1,-1):  # 9..0
		for y in data:
			lny = (y-vmin)*sf
			if ln < lny-1:
				print(chr(0x2588),end='')
			elif ln < lny:
				print(chr(0x2581+int((lny-ln)*8.0)),end='')	
			else:
				print(chr(backgndchar),end='')
		print("|%4.3g" % (vmin + (ln)/sf,))

				
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
	