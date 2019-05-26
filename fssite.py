#!/usr/bin/env python3.5
""" 
application to display measured quantities graphically and interactively
uses bottle web-framework: https://github.com/bottlepy/bottle
and sqlite database
get values and picklists from a database which was filled by fsmain.py et al.
"""

import os
import sys
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

__copyright__="<p>Copyright &copy; 2019, hjva</p>"
TITLE=r"fshome quantity viewer"
CONFFILE = "./fs20.json"
dbfile = '~/fs20store.sqlite'
TPL='static/fsapp.tpl'
COOKIE="FSSITE"
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
   1:(u'1day',15,0.25,'#j4'),  #'%H:%M'), 
	5:(u'5days',20,1,'%a'),
	30.44:(u'1mnth',6*60,7,'wk%V'), 
	182.6:(u'6mnth',24*60,30.44,'%b'), 
	365.25:(u'1yr',2*24*60,30.44,'%b') }
app =bottle.Bottle()

def typnames(devTyps):
	''' convert DEVT id numbers to their name '''
	return [dnm for dnm,tp in DEVT.items() if tp in devTyps or tp+100 in devTyps]

@app.route("/")
@bottle.view(TPL)
def index(name=TITLE):
	''' standard opening page (having only menu i.e. no data )'''
	srcs=list(dbStore.sources())
	src=srcs[0]
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
	if len(selqs)==0 or len(selqs)>5:
		selqs=['temperature']
	page = dict(menitms=buildMenu(srcs,src,typnames(dbStore.quantities(prop=2)),selqs,ndays))
	#page = redraw(src,selqs,julianday())
	page.update( dict(title=name, footer=__copyright__))
	return bottle.template(TPL, page)

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
		if x-xprv>100:
			crvs.append(crv)
			crv = ""
			#crv += " %.3g,%.3g" % (xprv, plYMARG+plHEIGHT)
			#crv += " %.3g,%.3g" % (x, plYMARG+plHEIGHT)
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
	for i in range(0,len(xdat)):
		crv += " M%.3g %d V%.3g" % (xdat[i]*xscl+xofs,plYMARG+plHEIGHT, ydat[i]*yscl+yofs)
	crv += " Z"
	return crv
	
def buildLbls(vmin,vmax, nr):
	''' axis labels '''
	lst = [vmin+i*(vmax-vmin)/(nr-1) for i in range(nr)]
	return [SiNumForm(x) for x in lst]  #   ["{:5.2g}".format(lbl) for lbl in lst]

def bld_dy_lbls(jdats, form="%a"):
	''' date interval labels '''
	if len(jdats)==0:
		return [""]
	return [prettydate(jd, form) for jd in jdats]
	
def buildChart(jdats, ydats,selqs, jdnow, ndays):
	''' build data for svg chart including axes,labels,gridlines,curves,histogram'''
	data=[]
	subtitle=[]
	#strokes=("#1084e9","#a430e9","#90e090","#c060d0","#c040f0","#f040d0","#f060d0")
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
				crv = buildHistogram(jdat,ydat, ndays,vmax, jdnow-ndays,vmin)
				qtyp=1
			else:
				crv = buildCurve(jdat,ydat, ndays,vmax-vmin, jdnow-ndays,vmin)
				qtyp=0
			ylbls=buildLbls(vmin,vmax,4)
			logger.debug("selq:%s,len:%d,col:%s,ylbls:%s" % (selq,len(jdat),stroke,ylbls))
			curve=dict(crv=crv, stroke=stroke, ylbls=ylbls, selq=selq, qtyp=qtyp, legend=selq)
			data.append(curve)
	if len(data)==0:
		logger.warning('missing data:jd:%d yd:%d q:%d' % (len(jdats),len(ydats),len(selqs)))
		return dict (title=TITLE, subtitle=" , ".join(subtitle), curves=[])
	
	xlbltup = tmBACKs[ndays]
	lblformat=xlbltup[3]
	gridstep=xlbltup[2]
	barwdt=xlbltup[1]
	xscl=plWIDTH/ndays
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
	
	xgrid =[plXMARG+plWIDTH-(jdnow-jd)*xscl for jd in gridlocs]
	xlbls=bld_dy_lbls([jd+gridstep/2 for jd in gridlocs[:-1]],lblformat)

	logger.info("ndays=%.4g xlbls=%s xgrid=%s" % (ndays,xlbls,xgrid))
	return dict( title=TITLE+"   dd:%s" % prettydate(jdnow), subtitle=" , ".join(subtitle), curves=data, xgrid=xgrid, xlbls=xlbls)

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

@app.post('/menu', method="POST")
def formhandler():
	''' Handle form submission '''
	logger.info("form post:%s" % bottle.request.body.read()) 
	selqs = bottle.request.forms.getall('quantities')
	src=bottle.request.forms.get('source')
	tnm=bottle.request.forms.get('tmback')
	jdnow=julianday()
	logger.info("form post:qtt=%s src=%s jd=%s ndys=%s" % (selqs, src, prettydate(jdnow), tnm))
	try:
		ndays=next(tb for tb,tup in tmBACKs.items() if tnm in tup[0])
	except StopIteration:
		ndays=5
	bottle.response.set_cookie(COOKIE, json.dumps((src,selqs,ndays)), max_age=AN1)
	return bottle.template(TPL, redraw(src, selqs, jdnow, ndays))
	
	
def redraw(src, selqs, jdnow, ndays=7):
	''' create data for main TPL page '''
	srcs=sorted(dbStore.sources())
	#quantities=sorted(dbStore.quantities())
	quantities=typnames(dbStore.quantities(prop=2))
	jdats=[]
	ydats=[]
	qss=[]
	xlbltup = tmBACKs[ndays]

	avgminutes = xlbltup[1]
	for qs in sorted(selqs):
		if qs in DEVT:
			typ=DEVT[qs]
			qkey = dbStore.quantity(src,typ)
			if qkey is not None:
				if qs=='energy':
					recs = dbStore.fetchiiavg(qkey-1,qkey,tstep=avgminutes,daysback=ndays)
				else:
					recs = dbStore.fetchiavg(qkey,tstep=avgminutes,daysback=ndays)
				if recs is None or len(recs)==0:
					continue
				if typ in qCOUNTING:
					iy=2	# counting quantity
				else:
					iy=1
				logger.info("redraw src:%s,qs:%s,iy:%d,typ:%d,qkey:%d" % (src,qs,iy,typ,qkey))
				ydats.append([rec[iy] for rec in recs])
				jdats.append([rec[0] for rec in recs])  # julian days
				qss.append(qs)
	page = dict(menitms=buildMenu(srcs,src,quantities,selqs,ndays),  **buildChart(jdats,ydats,qss,jdnow,ndays))
	return page
	

#fall back to static as last
@app.route('/<filepath:path>')
def server_static(filepath):
    return bottle.static_file(filepath, root='./static/')


if __name__ == '__main__':
	import socket
	logger = logging.getLogger()
	hand=logging.StreamHandler()
	hand.setLevel(logging.INFO)
	logger.addHandler(hand)	# use console
	logger.addHandler(logging.FileHandler(filename='fsbot.log', mode='w')) #details to log file
	logger.setLevel(logging.DEBUG)
	logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S")))

	
	config = devConfig(CONFFILE)
	dbfile = config.getItem('dbFile',dbfile)
	try:
		dbStore = sqlLogger(dbfile)
		logger.info("statistics:%s" %  dbStore.statistics(30)) # will get list of quantities and sources
		logger.info('quantities:%s' % dbStore.items)
	
		ip=socket.gethostbyname(socket.gethostname())
		ip =[l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
		port = int(os.environ.get('PORT', 8080))
		app.run(host=ip, port=port, debug=True, reloader=False)
	finally:
		dbStore.close()
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
