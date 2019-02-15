#!/usr/bin/env python3
""" general purpose storage handler e.g. for devices continuously spitting numeric values 
"""
from sqlite3 import connect
import logging
import os
import time

__author__ = "Henk Jan van Aalderen"
__credits__ = ["Henk Jan van Aalderen"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Henk Jan van Aalderen"
__email__ = "hjva@homail.nl"
__status__ = "Development"


class txtLogger(object):
	""" handler for log messages in a text file
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
	
	def additem(self, id, iname, isource):
		''' adds item type i.e. quantity descriptor '''
		self.items.update({id:(iname,isource)})
		logger.debug('adding item %s,%s with id=%d' % (iname,isource,id))
	
	def sources(self, quantities=None):
		return set([tup[1] for id,tup in self.items.items() if quantities is None or tup[0] in quantities])
		
	def quantities(self, sources=None):
		''' set of quantity names '''
		return set([tup[0] for id,tup in self.items.items() if sources is None or tup[1] in sources])
		
	def checkitem(self, iname, isource=None, addUnknown=True):
		''' check whether item has been seen before, adds it if not 
			returns unique itemid
		'''
		ids=[]
		for id,val in self.items.items():
			if iname==val[0]:
				if isource is None:
					ids.append(id)
				elif isource==val[1]:
					return id
		if isource is None:
			return tuple(ids)  # multiple sources for same item
		if addUnknown:
			if len(self.items)>0:
				id = max(self.items.keys())+1
			else:
				id=100
			self.additem(id,iname,isource)
			return id
		else:
			return -1
		
	def fetch(self, iname, daysback=100):
		''' gets filtered list of items from store '''
		id = self.checkitem(iname,addUnknown=False)
		self.file.flush()
		rfl = open(self.file.name,'r')
		after = time.time() - (daysback * 86400)
		buf=[]
		for ln in rfl:
			itms=ln.split('\t')
			if id==int(itms[0]) and after<float(itms[1]):
				buf.append(tuple(itms[1:])) # strip id
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
		if not os.path.isfile(store):
			logger.info("creating sqlStore in %s" % store)
			self.con=connect(store)	# will create file
			cur = self.con.cursor()
			cur.execute('CREATE TABLE logdat( '
				'ddJulian REAL	NOT NULL,'
				'quantity INT  NOT NULL,'
				'numval	REAL,'
				'strval  TEXT);' )
			cur.execute('CREATE TABLE quantities( '
				'ID	 INT PRIMARY KEY	NOT NULL,'
				"name  TEXT NOT NULL,"
				"source   TEXT,"
				"firstseen REAL);")
			cur.close()
		else:
			self.con=connect(store)
			logger.info("opening sqlStore in %s with %s" % (store,self.con.isolation_level))
			cur = self.con.cursor()
			cur.execute('SELECT ID,name,source FROM quantities;')
			rows=cur.fetchall()
			for rec in rows:
				self.items.update({rec[0]:(rec[1],rec[2])})
			cur.close()
	
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

		cur = self.con.cursor()
		cur.execute("SELECT %s FROM logdat,quantities "
			"WHERE ID=quantity AND ddJulian>julianday('now')-%d %s" 
			"ORDER BY ddJulian;" % (fields,daysback,where))
		return cur.fetchall()  # list of tuples with field-vals
		buf=[]
		for rec in cur.fetchall():
			buf.append({rec['ddJulian']:[rec[it] for it in fields.split(',')[1:] ]})
		return buf
		
	def fetchavg(self, name, tstep=30, daysback=100, source=None):
		''' fetch logged messages from the log store 
			takes averaged numval of name over tstep minutes intervals'''
		ids = self.checkitem(name,source,addUnknown=False) # get all quantity ids for source
		logger.info("nm:%s src:%s ids:%s" % (name,source,ids))
		where =""
		if not source is None:
			where=" AND source='%s'" % source
		if isinstance(ids, tuple):
			where+=" AND quantity IN (%s)" % ','.join(map(str,ids))
		else: # len(ids)==1:
			where+=" AND quantity=%d" % ids
		cur = self.con.cursor()
		# minperday=1440
		cur.execute("SELECT ROUND(ddJulian*1440/%d)/1440*%d AS dd,AVG(numval) AS nval,COUNT(*) AS cnt,source "
			"FROM logdat,quantities "
			"WHERE ID=quantity AND ddJulian>julianday('now')-%d %s " 
			"GROUP BY quantity,source,dd "
			"ORDER BY ddJulian;" % (tstep,tstep,daysback,where))
		return cur.fetchall()  # list of tuples with field-vals

	def statistics(self, ndays=10, flds="source,quantity,name"):
		cur = self.con.cursor()
		cur.execute("SELECT %s,COUNT(*) as cnt,AVG(numval) as avgval,MIN(ddJulian) jdFirst "
			"FROM logdat,quantities "
			"WHERE ID=quantity AND ddJulian>julianday('now')-%d " 
			"GROUP BY %s "
			"ORDER BY ID;" % (flds,ndays,flds))
		recs= cur.fetchall()
		for rec in recs:
			if 'name' in rec and 'source' in rec:
				self.checkitem(rec.name, rec.source)
		return recs
					
	def log(self, itemname, numval, strval=None, source=None, tstamp=None):
		''' add a log message to the log store '''
		if tstamp is None:
			tstamp = round(time.time(),0)	# granularity 1s
		itemid = self.checkitem(itemname,source)
		logger.debug('logging %s=%g with id=%d @jd:%.6f' % (itemname,numval,itemid,julianday(tstamp)))
		cur = self.con.cursor()
		cur.execute('INSERT INTO logdat (ddJulian,quantity,numval) '
			'VALUES (%.6f,%d,%g)' % (julianday(tstamp),itemid,numval))
		if not strval is None:
			cur.execute('UPDATE logdat SET strval="%s" WHERE ddJulian=%.6f AND quantity=%d' %
				(strval,julianday(tstamp),itemid))
		self.con.commit()
		cur.close()

	def additem(self, id, iname, isource):
		''' add a quantity descriptor (will be called automatic for unknown quantities) '''
		super(sqlLogger,self).additem(id,iname,isource)
		if isource is None:
			isource='NULL'
		else:
			isource='"%s"' % isource
		cur=self.con.cursor()
		cur.execute('INSERT INTO quantities (ID,name,source,firstseen) '
			'VALUES (%d,"%s",%s,julianday("now"))' % (id,iname,isource))
		cur.close()
		self.con.commit()

#some small helpers
#@staticmethod
def julianday(tunix = None):
	''' convert unix time to julianday i.e. days since noon on Monday, January 1 4713 BC '''
	if tunix is None:
		tunix = time.time()
	return (tunix / 86400.0 ) + 2440587.5
	
#@staticmethod
def unixsecond(julianday):
	return (julianday - 2440587.5) * 86400.0

def prettydate(julianday, format="%d %H:%M:%S"):
	return time.strftime(format, time.localtime(unixsecond(julianday)))

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
	import time,random
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
	