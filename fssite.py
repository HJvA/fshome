#!/usr/bin/env python3.5
""" 
application to display measured quantities graphically and interactively
uses bottle web-framework: https://github.com/bottlepy/bottle
doc: https://bottlepy.org/docs/dev/index.html
and sqlite database
get values and picklists from a database which was filled by fsmain.py et al.
"""

import os,sys,socket
import datetime,time
import logging
import json
try:
	import bottle.bottle as bottle
except ImportError:
	import bottle
	
from lib.devConfig import devConfig
from lib.dbLogger import sqlLogger
from lib.devConst import DEVT,qCOUNTING,qACCUMULATING,strokes,SIsymb,qSrc, qDEF,qtName,typnames,typSI
from submod.pyCommon.tls import get_logger
from lib.grtls import julianday,unixsecond,prettydate,SiNumForm
#from threading import Lock
from contextlib import contextmanager

class TimeoutLock(object):
	def __init__(self, mpLock=None):
		self._lock = mpLock

	def acquire(self, blocking=True, timeout=-1):
		return self._lock.acquire(blocking, timeout)

	@contextmanager
	def acquire_timeout(self, timeout):
		result = self._lock.acquire(timeout=timeout)
		yield result
		if result:
			self._lock.release()

	def release(self):
		self._lock.release()

lock = None  # global to be set to TimeoutLock 
queue = None

__copyright__="<p>Copyright &copy; 2019,2021,2022,2023,2024 hjva</p>"
TITLE=r"fshome quantity viewer"
DEBUG = True
CONFFILE = "./config/fs20.json"
dbfile = None # '~/fs20store.sqlite'
TPL='static/fsapp.tpl'
COOKIE="FSSITE_" + socket.gethostname()
AN1=60*60*24*365.25  # one year for cookie
# definition of plot area
plWIDTH = 800
plHEIGHT = 400
plYMARG= 50
plXMARG=100
# definition of x time axis in svg graph
# ndays:(label, bar minutes, grid step days, time ax lbl format)
# problem having these unicode chars recognizing choice response
tmBACKs={ 5:(u'\u251C 5days \u2524',20,1,'{:%d}'), 
	30.44:(u'\u251C 1mnth \u2524',6*60,7,'{:%V}'), 
	182.6:(u'\u251C 6mnth \u2524',24*60,30.44,'{:%b}'), 
	365.25:(u'\u251C 1yr \u2524',2*24*60,30.44,'{:%b}') }
tmBACKs={0.2:(u'5hr',5,0.0417,'{:%H}'),
	1.0:(u'1day',15,0.25,'#j4'),  #'%H:%M'), 
	5.0:(u'5days',20,1,'{:%d}'),
	30.44:(u'1mnth',6*60,7,'wk{:%V}'), 
	182.6:(u'6mnth',24*60,30.44,'{:%b}'), 
	365.25:(u'1yr',2*24*60,30.44,'{:%b}') }
app =bottle.Bottle()
if DEBUG:
	bottle.debug(DEBUG)
	app.catchall = False # Now most exceptions are re-raised within bottle.
dbStore=None

bottle.response.headers['Content-Type'] = 'application/json'
bottle.response.headers['Cache-Control'] = 'no-cache'

	
def srcQids():
	''' get active quantities either from cookie or last saved to database '''
	Qids=[]
	cookie = bottle.request.get_cookie(COOKIE)
	if cookie:
		logger.info('using cookie :"%s"' % cookie)
		cookie = list(json.loads(cookie))
		cookie.extend([None,None,None])
		src,selqs,ndays = tuple(cookie[:3])
	else:
		src=None
		selqs=typnames(dbStore.quantities([src],prop=2))[:2]  # quantity typs that are in src
		ndays=4
		bottle.response.set_cookie(COOKIE, json.dumps((src,selqs,ndays)), max_age=AN1)

	for qs in sorted(selqs):
		if qs in DEVT:
			typ=DEVT[qs]
			qkey = dbStore.quantity(src,typ)
			Qids += qkey
	return Qids,src

@app.route("/")
@bottle.view(TPL)
def index(name=TITLE):
	''' standard opening page (with settings from cookie or default) '''
	if 'REMOTE_ADDR' in bottle.request.environ:
		ip = bottle.request.environ.get('REMOTE_ADDR')
	else:
		ip = None
	tm=time.perf_counter()
	logger.info("===== frm index request:%s from %s=====" % (bottle.request.body.read(),ip)) 

	if bottle.request.query.title:
		bottle.redirect('/menu')
	
	srcs=list(dbStore.sources())
	src=srcs[0] # default
	quantIds=[]
	cookie = bottle.request.get_cookie(COOKIE)
	if cookie:
		logger.info('using cookie :"%s"' % cookie)
		cookie = list(json.loads(cookie))
		cookie.extend([None,None,None])
		src,selqs,ndays = tuple(cookie[:3])
	else:
		selqs=typnames(dbStore.quantities([src],prop=2))[:2]  # quantity typs that are in src
		ndays=4
		bottle.response.set_cookie(COOKIE, json.dumps((src,selqs,ndays)), max_age=AN1)
	logger.info("frm src:%s,selqs:%s len:%d" % (src,selqs,len(selqs)))
	if len(selqs)==0 or len(selqs)>15:
		selqs=['temperature']
	#page = dict(menitms=buildMenu(srcs,src,typnames(dbStore.quantities(prop=2)),selqs,ndays))
	#page = redraw(src,selqs,julianday())
	jdtill = julianday()
	page = redraw(src, selqs, jdtill, ndays)
	page.update( dict(title=name, footer=__copyright__)) #jdtill=julianday(),ndays=ndays,grQuantIds=quantIds))
	logger.debug("frm index page:(t:%s)\n%s\n" % (time.perf_counter()-tm,page))
	return bottle.template(TPL, page)

@app.post('/cursor', method="POST")
def cursorhandler():
	''' handle end of cursor movement
	receive data send by dragger.js->finalise->senddata '''
	logger.info("cursor posted:%s" % bottle.request.body.read()) 
	rec = bottle.request.json
	jd = float(rec['jdtill']) - (900 -float(rec['cursorPos']))/800*float(rec['ndays']);
	qids = rec['grQuantIds']
	logger.info("frm cursor %s at %s " % (rec,prettydate(jd)))
	#logger.info("curs post:%s" % bottle.request.body.read()) 
	return dict(dd=prettydate(jd),jdtill=jd,evtDescr='curs')
	
	
@app.get('/lastval')
def quantity_lastval():
	''' rest api for getting averaged quantity values from database
	e.g. http://192.168.1.20:8080/quantityact?qkeys=[401]
	will return last results of quantity 401 from database '''
	global lock
	with lock.acquire_timeout(4) as ack:
		if ack:
			recs={}
			qkeys = bottle.request.query.qkeys
			logger.debug('rest lastval get qkeys={}='.format(qkeys))
			if qkeys:
				qkeys = json.loads(qkeys)
				for qid in qkeys:
					dbres = dbStore.fetchlast(qid)
					if dbres:
						logger.info("rest get:qid:{} last:{}".format(qid,dbres))
						recs[qid] = dbres['numval']  # json.dumps(dbres)
			return '{}'.format(recs)
		else:
			logger.warning("unable to get rest lock for lastval")

@app.get('/somevals')
def quantity_somevals():
	''' rest api for getting averaged quantity values from database
	e.g. http://192.168.1.20:8080/quantity?qkeys=[401,403]&ndays=0.2 
	will return last results of quantity 401 from database '''
	global lock
	with lock.acquire_timeout(4) as ack:
		if ack:
			recs={}
			qkeys = bottle.request.query.qkeys
			#logger.info('somevals get qkeys={}='.format(qkeys))
			if qkeys:
				qkeys = json.loads(qkeys)
				ndays = float(bottle.request.query.ndays or '0.2')
				avginterval = float(bottle.request.query.interval or '5') # averaging interval in minutes
				#bottle.response.headers['Content-Type'] = 'application/json'
				#bottle.response.headers['Cache-Control'] = 'no-cache'
				
				for qid in qkeys:
					dbres = dbStore.fetchiavg(qid,mnstep=avginterval,daysback=ndays,jdend=None)
					if dbres:
						#recs['nm{}'.format(qk)] = dbStore.qname(qk)
						if dbStore.qtyp(qid) in qACCUMULATING:
							vFirst = dbres[0][1]
						else:
							vFirst = 0.0
						recs[qid] = [rec[1]-vFirst for rec in dbres]
						recs[qid*10] = [round(rec[0]-2400000.5,3) for rec in dbres]  # MJD
						jdlast = dbres[-1][0]
						logger.info('rest somevals req:{},step:{},vFirst:{},[min],name:{} ={}, {}'.format(qid, avginterval,vFirst, dbStore.qname(qid), recs[qid*10],recs[qid]))
						#logger.info('quantity request:%s' % bottle.request.params.items())
						#return json.dumps({'qval': [rec[1] for rec in recs], 'jdlast':jdlast})
					else:
						logger.warning('no rest for {} ndysbk:{} in {}'.format(qid,ndays, bottle.request.query.qkeys))
						#return '{}'
			return '{}'.format(recs)
			return '{'+'"qvals":{}'.format(recs)+'}'
		else:
			logger.warning("unable to get rest locked for :somevals")
			

@app.put('/qsave')
def quantity_put():
	qid=None
	qval=None
	global queue,lock
	with lock.acquire_timeout(4) as ack:
		if ack:
			try:
				#qkey = bottle.request.params.get('qkey')
				qid=int(bottle.request.query.qkey)
				if qid:  # make sure qid exists in db
					dbStore.additem(qid,qDEF[qid][0], qSrc(qid), qDEF[qid][1])
				qval=float(bottle.request.query.qval)
				#data = json.load(utf8reader(bottle.request.body))
				logger.info('rest put:qid:{}={} qsize:{}'.format(qid,qval,queue.qsize()))
				dbStore.logi(qid,qval)
				if queue:
					queue.put((qid,qval), block=False)
				else:
					logger.warning("no queue for watchdog for qid:{}".format(qid))
			except Exception as ex:
				logger.error("unable to rest save qid:{}={} ex:{}".format(qid,qval,ex))
				raise	ValueError
		else:
			logger.warning("unable to get rest locked for put:{}".format(qid))
			

	
@app.post('/menu', method="POST")
def formhandler():
	''' Handle frm submission '''
	tm=time.perf_counter()
	if 'REMOTE_ADDR' in bottle.request.environ:
		ip = bottle.request.environ.get('REMOTE_ADDR')
	else:
		ip = None
		
	logger.warning("==== frm handler menu main from:{} =====:\n".format(ip)  )
	logger.info("body:{}".format(bottle.request.body.read()))
	selqs = bottle.request.forms.getall('quantities')	# selected quantities
	src=bottle.request.forms.get('source')					# actual source
	tbcknm=bottle.request.forms.get('tmback')				# time span # days
	cursXpos=bottle.request.forms.get('cursorPos')
	jdtill=bottle.request.forms.get('jdtill')				# time at right axis
	evtDescr=bottle.request.forms.get('evtDescr')
	evtData=bottle.request.forms.get('evtData')
	try:
		ndays=next(tb for tb,tup in tmBACKs.items() if tbcknm in tup[0])
	except StopIteration:
		ndays=5

	jdofs =(plXMARG+plWIDTH-int(cursXpos))/plWIDTH * ndays  # cursor pos giving time offset
	if jdtill:
		jdtill=float(jdtill)  # preserve actual time frame
	else:
		jdtill=julianday()
	jdcursor = jdtill -jdofs
	if evtDescr and evtDescr!='comment':  # define event at cursor
		root = sys.modules['__main__'].__file__
		logger.info('form received event descr %s at jd:%s' % (evtDescr,jdcursor))
		
		dbStore.setEvtDescription(jdcursor,evtDescr,root=root)
	else:  # place right side at cursor
		jdtill = jdcursor

	if abs(jdtill-julianday())<ndays/5.0:
		jdtill=julianday()  # adjust to now when close
	else:
		logger.info("frm adjusting jd %f with ofs:%f evt:%s" % (jdtill,jdofs,evtDescr))
	statbar=bottle.request.forms.get('statbar')
	logger.info("statbar=%s" % statbar)
	
	logger.info("frm menu response(t:%s):qtt=%s src=%s jd=%s ndys=%s cPos=%s evtData=%s" % (time.perf_counter()-tm, selqs, src, prettydate(jdtill), tbcknm,cursXpos,evtData))
	bottle.response.set_cookie(COOKIE, json.dumps((src,selqs,ndays)), max_age=AN1)
	return bottle.template(TPL, redraw(src, selqs, jdtill, ndays))
	

def buildCurve(xdat, ydat, xsize, ysize, xstart,ystart):
	''' build svg polyline '''
	xscl=plWIDTH/xsize
	yscl=-plHEIGHT/ysize
	xofs=plXMARG-xstart*xscl
	yofs=plYMARG+plHEIGHT-ystart*yscl
	crvs=[]
	crv=""
	xprv=plXMARG
	for i in range(0,len(xdat)):
		x = xdat[i]*xscl+xofs
		if x-xprv>100:	# large step
			crvs.append(crv)
			crv = ""
		crv += " %.3g,%.3g" % (x,ydat[i]*yscl+yofs)
		xprv=x
	if len(crv)>0:
		crvs.append(crv)
	return crvs

def buildHistogram(xdat, ydat, xsize, ysize, xstart,ystart):
	''' build svg path '''
	xscl=plWIDTH/xsize
	yscl=-plHEIGHT/ysize
	xofs=plXMARG-xstart*xscl
	yofs=plYMARG+plHEIGHT-ystart*yscl
	crv=""
	if xdat:
		for i in range(0,len(xdat)):
			crv += " M%.3g %d V%.3g" % (xdat[i]*xscl+xofs,plYMARG+plHEIGHT, ydat[i]*yscl+yofs)
		crv += " Z"
	return crv
	
def SiNumLbls(vmin,vmax, nr):
	''' numeric axis labels using Si abreviations '''
	if nr:
		lst = [vmin+i*(vmax-vmin)/(nr-1) for i in range(nr)]
		return [SiNumForm(x) for x in lst]  #   ["{:5.2g}".format(lbl) for lbl in lst]
	return []

def TimeLbls(jdats, form="{}"):
	''' date interval labels '''
	if len(jdats)==0:
		return [""]
	return [prettydate(jd, form) for jd in jdats]

def tax_grid(jdnow,ndays,gridstep):
	''' time axis grid locations '''
	utcoff = time.localtime().tm_gmtoff/3600/24  #[d]  #time.localtime()-time.gmtime()

	if gridstep==0.0417:   # 1hrs
		gridofs= (jdnow+utcoff) % 0.0417 #[d]
		gridofs= jdnow-int(jdnow)
		gridofs= gridofs % 0.0417
		gridofs *= 24.0	#[hr]
		logger.debug("frm frac in 1hrs %s utcofs=%s now=%s" % (gridofs,utcoff,prettydate(jdnow)))
	elif gridstep==0.25:   # 6hrs
		gridofs= (jdnow+utcoff) % 0.25  #[d]
		gridofs *= 4.0	#[6h]
		logger.debug("frm frac in 6hrs %s utcofs=%s now=%s" % (gridofs,utcoff,prettydate(jdnow)))
	elif gridstep==7:  # a week
		gridofs = (jdnow+1.5+utcoff) % 7  #[d]
		logger.debug("frm day of week:%s" % gridofs)
		gridofs /= 7	#[w]
	elif int(gridstep)==30:  # a month
		gridofs = datetime.datetime.fromtimestamp(unixsecond(jdnow))
		logger.debug("frm date %s hour %s" % (gridofs.day,gridofs.hour))
		gridofs = gridofs.day + gridofs.hour/24.0  #[d]
		gridofs /= 30.44	#[m]
	else:
		gridofs = jdnow-0.5+utcoff  #noon utc to midnight this tz
		gridofs = gridofs/gridstep - int(gridofs/gridstep)

	gridlocs = [jdnow-(f+gridofs)*gridstep for f in range(int(ndays/gridstep+0.1))]
	gridlocs.reverse()
	logger.debug("frm jdnow=%s gridlocs=%s" % (jdnow,gridlocs))
	return gridlocs

	
def buildChart(jdats, ydats,selqs, jdtill, ndays):
	''' build data for svg chart including axes,labels,gridlines,curves,histogram'''
	data=[]
	subtitle=[]
	ret = dict(title=TITLE,ndays=ndays,jdtill=jdtill,cursorPos=plXMARG+plWIDTH,curves=[])
	
	for jdat,ydat,selq in zip(jdats,ydats,selqs):
		if len(ydat)>0:
			vmax = max(ydat)
			vmin = min(ydat)
			if vmax<=vmin:
				vmin = vmax-1
		if selq in DEVT and DEVT[selq] in strokes:
			stroke=strokes[DEVT[selq]]
			symbol=SIsymb[DEVT[selq]]
			vlast=ydat[-1]
			subtitle.append("%s=%.4g %s " % (symbol[0],vlast,symbol[1]))
		else:
			logger.debug("frm selq %s not in strokes:%s" % (selq,strokes))
			stroke=strokes[0]
		if len(jdat)>0:
			if selq in DEVT and DEVT[selq] in qCOUNTING:
				vmin=0
				vmax = int(vmax/3)*3+3
				crv = buildHistogram(jdat,ydat, ndays,vmax, jdtill-ndays,vmin)
				qtyp=1
			else:
				crv = buildCurve(jdat,ydat, ndays,vmax-vmin, jdtill-ndays,vmin)
				qtyp=0
			ylbls=SiNumLbls(vmin,vmax,4)
			logger.debug("frm selq:%s,len:%d,col:%s,ylbls:%s" % (selq,len(jdat),stroke,ylbls))
			curve=dict(crv=crv, stroke=stroke, ylbls=ylbls, selq=selq, qtyp=qtyp, legend=selq, unit=symbol[1])
			data.append(curve)
	ret['subtitle']='' #" , ".join(subtitle)
	ret['statbar'] =[ " dd:%s , %s" % (prettydate(jdtill), " , ".join(subtitle)) ]
	if len(data)==0:
		logger.warning('frm missing chart data:jd:%d yd:%d q:%d' % (len(jdats),len(ydats),len(selqs)))
		ret.update(dict(curves=[],xgrid=[]))
		return ret
	
	xlbltup = tmBACKs[ndays]
	lblformat=xlbltup[3]
	gridstep=xlbltup[2]
	barwdt=xlbltup[1]
	xscl=plWIDTH/ndays

	gridlocs= tax_grid(jdtill,ndays,gridstep)
	xgrid = [round(plXMARG+plWIDTH-(jdtill-jd)*xscl,1) for jd in gridlocs]
	xlbls=TimeLbls([jd+gridstep/2 for jd in gridlocs[:-1]],lblformat)

	logger.info("frm chart upd: ndays=%.4g xlbls=%s xgrid=%s" % (ndays,xlbls,xgrid))
	ret.update(dict(title=TITLE, curves=data, xgrid=xgrid, xlbls=xlbls))
	return ret

def buildMenu(sources,selsrc,quantities,selqs,ndays,tmbacks=tmBACKs):
	''' data for menu.tpl '''
	#logger.info("bldmenu: srcs:%s qtts:%s selqs:%s" % (sources,quantities,selqs))
	menu =[]
	menu.append({'rf':'/action/sel','nm':'source',
	'cls':[{'nm':src,'cls':'sel' if src==selsrc else ''} for src in sources]})
	menu.append({'rf':'/action/sel','nm':'quantities','typ':'multiple',
	'cls':[{'nm':qtt,'cls':'sel' if qtt in selqs else ''} for qtt in quantities]})
	menu.append({'rf':'/action/sel','nm':'tmback',
	'cls':[{'nm':tnm[0],'cls':'sel' if tm==ndays else ''} for tm,tnm in sorted(tmbacks.items())]})
	menu.append({'rf':'','nm':'ok','cls':'submit'})
	#logger.info("menu=%s" % menu)
	return menu

	
def redraw(src, selqs, jdtill, ndays=7):
	''' create data for main TPL page '''
	tm=time.perf_counter()
	srcs=sorted(dbStore.sources())
	#quantities=sorted(dbStore.quantities())
	quantities=typnames(dbStore.quantities(prop=2))
	SIsymbols = typSI(dbStore.quantities(prop=2))
	units = [rec[1] for rec in SIsymbols]
	jdats=[]
	ydats=[]
	qss=[]
	grQuantIds=set()
	if ndays not in tmBACKs:
		ndays=1.0
	xlbltup = tmBACKs[ndays]
	evtData={"%f" % tup[0]:tup[1] for tup in dbStore.evtDescriptions(jdtill,ndays)}

	avgminutes = xlbltup[1]
	for qs in sorted(selqs):
		if qs in DEVT:
			typ=DEVT[qs]
			qkey = dbStore.quantity(src,typ) # might have multiple?
			if qkey is not None:
				grQuantIds.add(qkey)
				if qs=='energy':
					recs = dbStore.fetchiiavg(310,311,mnstep=avgminutes,daysback=ndays, jdend=jdtill)
				else:
					recs = dbStore.fetchiavg(qkey,mnstep=avgminutes,daysback=ndays, jdend=jdtill)
				if recs is None or len(recs)==0:
					logger.info('frm no samples for %s at %s with %s' % (qkey,qs,src))
					continue
				if typ in qCOUNTING:
					iy=2	# counting quantity
				else:
					iy=1
				if typ in qACCUMULATING:
					vFirst = recs[0][iy]
				else:
					vFirst = 0.0
				logger.info("frm redraw src:%s,qs:%s,iy:%d,typ:%d,qid:%d,vFirst:%f" % (src,qs,iy,typ,qkey,vFirst))
				ydats.append([rec[iy]-vFirst for rec in recs])
				jdats.append([rec[0] for rec in recs])  # julian days
				qss.append(qs)
	page = dict(menitms=buildMenu(srcs,src,quantities,selqs,ndays), grQuantIds="%s" % list(grQuantIds), evtData=json.dumps(evtData), **buildChart(jdats,ydats,qss,jdtill,ndays))
	logger.debug("frm redraw page:(t:%s)\n%s\n" % (time.perf_counter()-tm,page))
	return page

#fall back to static as last
@app.route('/<filepath:path>')
def server_static(filepath):
	return bottle.static_file(filepath, root='./static/')

def fssiteRun(cnfFname=CONFFILE, mpLock=None, mpQueue=None):
	""" running fssite webserver """
	global queue,lock
	queue = mpQueue
	lock = TimeoutLock(mpLock)
	config = devConfig(cnfFname)
	dbfile = config.getItem('dbFile',None)
	global dbStore
	try:
		dbStore = sqlLogger(dbfile)
		dbStore.writeTypes(SIsymb)
		dbStore.sources(minDaysBack=5)
		logger.info("frm fssiteRun :qsize:{} cnf:{}".format(mpQueue.qsize(),cnfFname))
		#logger.info("statistics:%s" %  dbStore.statistics(5)) # will get list of quantities and sources
		logger.info('frm quantities:%s' % dbStore.items)
		for qk in dbStore.items:
			rec = dbStore.fetchlast(qk)
			logger.info("frm qid:{}={}".format(qk,rec))
		if config.hasItem('tailScale'):
			ip = config.getItem('tailScale')  # ip accessible by world, issued by tailScale
		else: # ip of listening host
			ip=socket.gethostbyname(socket.gethostname())			
			ip =[l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
		logger.warning("frm running bottle on {} with {}".format(socket.gethostname(),ip))
		ip = '0.0.0.0'  # Pass 0.0.0.0 to listens on all interfaces including the external one
		port = int(os.environ.get('PORT', 8080))
		#logger.info('bottle req env:{} ip:{} port:{}'.format(bottle.request.environ, ip,port))
		app.run(host=ip, port=port, reloader=False, debug=DEBUG)
	except KeyboardInterrupt:
		pass
	finally:
		dbStore.close()	

if __name__ == '__main__':
	import multiprocessing
	logger = get_logger(__file__,logging.INFO, logging.DEBUG if DEBUG else logging.INFO)
	# create a process
	fssiteRun()
	
	exit()
	lock = multiprocessing.Lock()
	process = multiprocessing.Process(target=fssiteRun, args=(CONFFILE,lock))
	process.start()
	process.join()
	
	"""
	config = devConfig(CONFFILE)
	dbfile = config.getItem('dbFile',dbfile)
	try:
		dbStore = sqlLogger(dbfile)
		dbStore.writeTypes(SIsymb)
		dbStore.sources(minDaysBack=5)
		#logger.info("statistics:%s" %  dbStore.statistics(5)) # will get list of quantities and sources
		logger.info('quantities:%s' % dbStore.items)
		for qk in dbStore.items:
			rec = dbStore.fetchlast(qk)
			logger.info("qid:{}={}".format(qk,rec))
		if config.hasItem('tailScale'):
			ip = config.getItem('tailScale')  # ip accessible by world, issued by tailScale
		else: # ip of listening host
			ip=socket.gethostbyname(socket.gethostname())			
			ip =[l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
		logger.warning("running bottle on {} with {}".format(socket.gethostname(),ip))
		ip = '0.0.0.0'  # Pass 0.0.0.0 to listens on all interfaces including the external one
		port = int(os.environ.get('PORT', 8080))
		logger.info('req env:{}'.format(bottle.request.environ))
		app.run(host=ip, port=port, reloader=False, debug=DEBUG)
	finally:
		dbStore.close()
	"""
else:	# this is running as a module
	logger = get_logger()	# get logger from main program
