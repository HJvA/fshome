#!/usr/bin/env python3.5
""" 
application to display measured quantities graphically and interactively
uses bottle web-framework: https://github.com/bottlepy/bottle
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
from lib.dbLogger import sqlLogger,julianday,unixsecond,prettydate,SiNumForm
from lib.devConst import DEVT,qCOUNTING,strokes,SIsymb
from lib.tls import get_logger

__copyright__="<p>Copyright &copy; 2019,2020, hjva</p>"
TITLE=r"fshome quantity viewer"
CONFFILE = "./fs20.json"
dbfile = '~/fs20store.sqlite'
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
tmBACKs={ 5:(u'\u251C 5days \u2524',20,1,'%a'), 
	30.44:(u'\u251C 1mnth \u2524',6*60,7,'%V'), 
	182.6:(u'\u251C 6mnth \u2524',24*60,30.44,'%b'), 
	365.25:(u'\u251C 1yr \u2524',2*24*60,30.44,'%b') }
tmBACKs={0.2:(u'5hr',5,0.0417,'%H'),
   1.0:(u'1day',15,0.25,'#j4'),  #'%H:%M'), 
	5.0:(u'5days',20,1,'%a'),
	30.44:(u'1mnth',6*60,7,'wk%V'), 
	182.6:(u'6mnth',24*60,30.44,'%b'), 
	365.25:(u'1yr',2*24*60,30.44,'%b') }
app =bottle.Bottle()
dbStore=None

def typnames(devTyps):
	''' convert DEVT id numbers to their name '''
	return [dnm for dnm,tp in DEVT.items() if tp in devTyps or tp+100 in devTyps]

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
	logger.info("===== index request:%s from %s=====" % (bottle.request.body.read(),ip)) 

	if bottle.request.query.title:
		bottle.redirect('/menu')
	
	srcs=list(dbStore.sources())
	src=srcs[0]
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
	logger.info("src:%s,selqs:%s len:%d" % (src,selqs,len(selqs)))
	if len(selqs)==0 or len(selqs)>15:
		selqs=['temperature']
	#page = dict(menitms=buildMenu(srcs,src,typnames(dbStore.quantities(prop=2)),selqs,ndays))
	#page = redraw(src,selqs,julianday())
	jdtill = julianday()
	page = redraw(src, selqs, jdtill, ndays)
	page.update( dict(title=name, footer=__copyright__)) #jdtill=julianday(),ndays=ndays,grQuantIds=quantIds))
	logger.debug("index page:(t:%s)\n%s\n" % (time.perf_counter()-tm,page))
	return bottle.template(TPL, page)

@app.post('/cursor', method="POST")
def cursorhandler():
	''' handle end of cursor movement
	receive data send by dragger.js->finalise->senddata '''
	logger.info("cursor posted:%s" % bottle.request.body.read()) 
	rec = bottle.request.json
	jd = float(rec['jdtill']) - (900 -float(rec['cursorPos']))/800*float(rec['ndays']);
	qids = rec['grQuantIds']
	logger.info("cursor %s at %s " % (rec,prettydate(jd)))
	#logger.info("curs post:%s" % bottle.request.body.read()) 
	return dict(dd=prettydate(jd),jdtill=jd,evtDescr='curs')

@app.post('/menu', method="POST")
def formhandler():
	''' Handle form submission '''
	tm=time.perf_counter()
	logger.info("menu posted:%s" % bottle.request.body.read()) 
	selqs = bottle.request.forms.getall('quantities')
	src=bottle.request.forms.get('source')
	tbcknm=bottle.request.forms.get('tmback')
	cursXpos=bottle.request.forms.get('cursorPos')
	jdtill=bottle.request.forms.get('jdtill')
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
		logger.info('received event descr %s at jd:%s' % (evtDescr,jdcursor))
		
		dbStore.setEvtDescription(jdcursor,evtDescr,root=root)
	else:  # place right side at cursor
		jdtill = jdcursor

	if abs(jdtill-julianday())<ndays/5.0:
		jdtill=julianday()  # adjust to now when close
	else:
		logger.info("adjusting jd %f with ofs:%f evt:%s" % (jdtill,jdofs,evtDescr))
	statbar=bottle.request.forms.get('statbar')
	logger.info("statbar=%s" % statbar)
	
	logger.info("menu response(t:%s):qtt=%s src=%s jd=%s ndys=%s cPos=%s evtData=%s" % (time.perf_counter()-tm, selqs, src, prettydate(jdtill), tbcknm,cursXpos,evtData))
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
	
def buildLbls(vmin,vmax, nr):
	''' axis labels '''
	if nr:
		lst = [vmin+i*(vmax-vmin)/(nr-1) for i in range(nr)]
		return [SiNumForm(x) for x in lst]  #   ["{:5.2g}".format(lbl) for lbl in lst]
	return []

def bld_dy_lbls(jdats, form="%a"):
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
		logger.debug("frac in 1hrs %s utcofs=%s now=%s" % (gridofs,utcoff,prettydate(jdnow)))
	elif gridstep==0.25:   # 6hrs
		gridofs= (jdnow+utcoff) % 0.25  #[d]
		gridofs *= 4.0	#[6h]
		logger.debug("frac in 6hrs %s utcofs=%s now=%s" % (gridofs,utcoff,prettydate(jdnow)))
	elif gridstep==7:  # a week
		gridofs = (jdnow+1.5+utcoff) % 7  #[d]
		logger.debug("day of week:%s" % gridofs)
		gridofs /= 7	#[w]
	elif int(gridstep)==30:  # a month
		gridofs = datetime.datetime.fromtimestamp(unixsecond(jdnow))
		logger.debug("date %s hour %s" % (gridofs.day,gridofs.hour))
		gridofs = gridofs.day + gridofs.hour/24.0  #[d]
		gridofs /= 30.44	#[m]
	else:
		gridofs = jdnow-0.5+utcoff  #noon utc to midnight this tz
		gridofs = gridofs/gridstep - int(gridofs/gridstep)

	gridlocs = [jdnow-(f+gridofs)*gridstep for f in range(int(ndays/gridstep+0.1))]
	gridlocs.reverse()
	logger.debug("jdnow=%s gridlocs=%s" % (jdnow,gridlocs))
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
			logger.debug("selq %s not in strokes:%s" % (selq,strokes))
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
			ylbls=buildLbls(vmin,vmax,4)
			logger.debug("selq:%s,len:%d,col:%s,ylbls:%s" % (selq,len(jdat),stroke,ylbls))
			curve=dict(crv=crv, stroke=stroke, ylbls=ylbls, selq=selq, qtyp=qtyp, legend=selq)
			data.append(curve)
	ret['subtitle']='' #" , ".join(subtitle)
	ret['statbar'] =[ " dd:%s , %s" % (prettydate(jdtill), " , ".join(subtitle)) ]
	if len(data)==0:
		logger.warning('missing chart data:jd:%d yd:%d q:%d' % (len(jdats),len(ydats),len(selqs)))
		ret.update(dict(curves=[],xgrid=[]))
		return ret
	
	xlbltup = tmBACKs[ndays]
	lblformat=xlbltup[3]
	gridstep=xlbltup[2]
	barwdt=xlbltup[1]
	xscl=plWIDTH/ndays

	gridlocs= tax_grid(jdtill,ndays,gridstep)
	xgrid = [round(plXMARG+plWIDTH-(jdtill-jd)*xscl,1) for jd in gridlocs]
	xlbls=bld_dy_lbls([jd+gridstep/2 for jd in gridlocs[:-1]],lblformat)

	logger.info("chart upd: ndays=%.4g xlbls=%s xgrid=%s" % (ndays,xlbls,xgrid))
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
			qkey = dbStore.quantity(src,typ)
			if qkey is not None:
				grQuantIds.add(qkey)
				if qs=='energy':
					recs = dbStore.fetchiiavg(310,311,tstep=avgminutes,daysback=ndays,jdend=jdtill)
				else:
					recs = dbStore.fetchiavg(qkey,tstep=avgminutes,daysback=ndays,jdend=jdtill)
				if recs is None or len(recs)==0:
					logger.info('no samples for %s at %s with %s' % (qkey,qs,src))
					continue
				if typ in qCOUNTING:
					iy=2	# counting quantity
				else:
					iy=1
				logger.info("redraw src:%s,qs:%s,iy:%d,typ:%d,qkey:%d" % (src,qs,iy,typ,qkey))
				ydats.append([rec[iy] for rec in recs])
				jdats.append([rec[0] for rec in recs])  # julian days
				qss.append(qs)
	page = dict(menitms=buildMenu(srcs,src,quantities,selqs,ndays), grQuantIds="%s" % list(grQuantIds), evtData=json.dumps(evtData), **buildChart(jdats,ydats,qss,jdtill,ndays))
	logger.debug("redraw page:(t:%s)\n%s\n" % (time.perf_counter()-tm,page))
	return page

#fall back to static as last
@app.route('/<filepath:path>')
def server_static(filepath):
	return bottle.static_file(filepath, root='./static/')


if __name__ == '__main__':
	import socket
	logger = get_logger(__file__)
	
	config = devConfig(CONFFILE)
	dbfile = config.getItem('dbFile',dbfile)
	try:
		dbStore = sqlLogger(dbfile)
		logger.info("statistics:%s" %  dbStore.statistics(5)) # will get list of quantities and sources
		logger.info('quantities:%s' % dbStore.items)
		if config.hasItem('tailScale'):
			ip = config.getItem('tailScale')  # ip accessible by world
		else: # ip of localhost
			ip=socket.gethostbyname(socket.gethostname())
			ip =[l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
		port = int(os.environ.get('PORT', 8080))
		app.run(host=ip, port=port, debug=True, reloader=False)
	finally:
		dbStore.close()
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
