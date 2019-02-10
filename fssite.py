import os
import sys
import datetime
import logging
import json
try:
	import bottle.bottle as bottle
except ImportError:
	import bottle
	
#sys.path.append(r"accessories/fs20")	# search path for imports
from lib.devConfig import devConfig
from lib.dbLogger import sqlLogger,julianday,prettydate

__copyright__="<p>Copyright &copy; 2019, hjva</p>"
TITLE=r"graphing temperature monitor"
CONFFILE = "./fs20.json"
dbfile = '~/fs20store.sqlite'
TPL='static/fsapp.tpl'
COOKIE="FSSITE"
AN1=60*60*24*365.25  # one year
plWIDTH = 800
plHEIGHT = 400
plMARG=50
# ndays, lbl, bar minutes
tmBACKs={5:('5d back',5),30:('1mnth back',60),180:('6mnth back',1440),365:('1yr back',1440)}
app =bottle.Bottle()

@app.route("/")
@bottle.view(TPL)
def index(name=TITLE):
	srcs=list(dbStore.sources())
	src=srcs[0]
	cookie = bottle.request.get_cookie(COOKIE)
	if cookie:
		logger.info('using cookie :"%s"' % cookie)
		cookie = list(json.loads(cookie))
		cookie.extend([None,None,None])
		src,selqs,ndays = tuple(cookie[:3])
	else:
		selqs=list(dbStore.quantities([src]))[:2]
		ndays=4
		bottle.response.set_cookie(COOKIE, json.dumps((src,selqs,ndays)), max_age=AN1)
	logger.info("src:%s,selqs:%s len:%d" % (src,selqs,len(selqs)))
	if len(selqs)==0 or len(selqs)>5:
		selqs=['temperature']
	page = dict(menitms=buildMenu(srcs,src,dbStore.quantities(),selqs,ndays))
	#page = redraw(src,selqs,julianday())
	page.update( dict(title=name, footer=__copyright__))
	return bottle.template(TPL, page)
	
def buildPath(xdat, ydat, xofs, ybas):
	''' build svg path from xy data '''
	crv="M%g,%g" % (xdat[0]-xofs, ybas)
	for i in range(0,len(xdat)):
		crv += " L%.3g,%.3g" % (xdat[i]-xofs,ydat[i])
	crv += " L%g,%gZ" % (max(xdat)-xofs,ybas)
	return crv
	
def buildCurve(xdat, ydat, xofs, ybas):
	crv=""
	for i in range(0,len(xdat)):
		crv += " %.3g,%.3g" % (xdat[i]-xofs,ydat[i])	
	return crv

def buildLbls(dat, nr):
	''' axis labels '''
	if len(dat)==0:
		return [float(i) for i in range(nr)]
	vmin=min(dat)
	vmax=max(dat)
	return [vmin+i*(vmax-vmin)/(nr-1) for i in range(nr)]

def bld_dy_lbls(jdats, form="%a"):
	''' date interval labels '''
	if len(jdats)==0:
		return [""]
	return [prettydate(jd, form) for jd in jdats]
	
def buildChart(jdats, ydats, jdnow):
	''' build data for svg chart '''
	data=[]
	ndays=1
	stroke="#0074d9"
	for jdat,ydat in zip(jdats,ydats):
		if len(ydat)>0:
			vmax = max(ydat)
			vmin = min(ydat)
			if vmax<=vmin:
				vmin = vmax-1
		
		if len(jdat)>0:
			nd =jdnow-min(jdat)
			if nd>ndays:
				ndays = nd
				xscl=plWIDTH/ndays
			height = vmax-vmin
			yscl=plHEIGHT/(height)
			yofs=plHEIGHT+plMARG + yscl*vmin  # bottom of chart viewport		
			scale="%.4g,%.4g" % (xscl,-yscl)
			crv = buildCurve(jdat,ydat,jdnow-ndays,vmin)
			curve=dict(crv=crv,yofs=yofs,scale=scale,stroke=stroke, ylbls=buildLbls(ydat,4))
			data.append(curve)
			stroke="#9420d9"
	if len(data)==0:
		return dict (title=TITLE, curves=[])
	
	xlbls=bld_dy_lbls([jdnow-ndays+d+1 for d in range(int(ndays)+1)])
	
	fracd = jdnow-0.5  #noon to midnight
	fracd = fracd - int(fracd)
	xgrid =[(i-fracd+1)*xscl+100 for i in range(int(ndays+0.1))]
	
	logger.info("ndays=%.4g scl='%s' yofs=%.4g xlbls=%s xgrid=%s" % (ndays,scale,yofs,xlbls,xgrid))
	return dict( title=TITLE+"   dd:%s" % prettydate(jdnow), curves=data, scale=scale ,yofs="%.4g" % yofs, xgrid=xgrid, xlbls=xlbls)

def buildMenu(sources,selsrc,quantities,selqs,ndays,tmbacks=tmBACKs):
	''' data for menu.tpl '''
	logger.info("bldmenu: srcs:%s qtts:%s selqs:%s" % (sources,quantities,selqs))
	menu =[]
	menu.append({'rf':'/action/sel','nm':'source',
	'cls':[{'nm':src,'cls':'sel' if src==selsrc else ''} for src in sources]})
	menu.append({'rf':'/action/sel','nm':'quantities','typ':'multiple',
	'cls':[{'nm':qtt,'cls':'sel' if qtt in selqs else ''} for qtt in quantities]})
	menu.append({'rf':'/action/sel','nm':'tmback',
	'cls':[{'nm':tnm[0],'cls':'sel' if tm==ndays else ''} for tm,tnm in tmbacks.items()]})
	menu.append({'rf':'','nm':'ok','cls':'submit'})
	#logger.info("menu=%s" % menu)
	return menu

@app.post('/menu', method="POST")
def formhandler():
	''' Handle form submission '''
	logger.info("form post:%s" % bottle.request.body.read())   #.decode('utf-8'))
	selqs = bottle.request.forms.getall('quantities')
	src=bottle.request.forms.get('source')
	tnm=bottle.request.forms.get('tmback')
	jdnow=julianday()
	logger.info("form post:qtt=%s src=%s jd=%s ndys=%s" % (selqs, src, prettydate(jdnow), tnm))
	ndays=next(tb for tb,tup in tmBACKs.items() if tnm in tup[0])
	bottle.response.set_cookie(COOKIE, json.dumps((src,selqs,ndays)), max_age=AN1)
	return bottle.template(TPL, redraw(src, selqs, jdnow, ndays))
	
	
def redraw(src, selqs, jdnow, ndays=4):
	''' create data for main TPL page '''
	srcs=list(dbStore.sources())
	quantities=list(dbStore.quantities())
	logger.info("redraw src:%s,selqs:%s" % (src,selqs))
	
	jdats=[]
	ydats=[]
	avgminutes =60
	if ndays>10:
		avgminutes=3600
	if ndays>30:
		avgminutes *= 24
	for qs in selqs:
		recs = dbStore.fetchavg(qs,tstep=avgminutes,daysback=ndays,source=src)
		ydats.append([rec[1] for rec in recs])
		jdats.append([rec[0] for rec in recs])
	page = dict(menitms=buildMenu(srcs,src,quantities,selqs,ndays), **buildChart(jdats, ydats, jdnow))
	return page
	

#fall back to static as last
@app.route('/<filepath:path>')
def server_static(filepath):
    return bottle.static_file(filepath, root='./static/')


if __name__ == '__main__':
	import socket
	logger = logging.getLogger()
	logger.addHandler(logging.StreamHandler())	# use console
	logger.addHandler(logging.FileHandler(filename='fsbot.log', mode='w')) #details to log file
	logger.setLevel(logging.DEBUG)
	
	config = devConfig(CONFFILE)
	dbfile = config.getItem('dbFile',dbfile)
	dbStore = sqlLogger(dbfile)
	logger.info("statistics:%s" %  dbStore.statistics(30)) # will get list of quantities and sources
	
	ip=socket.gethostbyname(socket.gethostname())
	ip =[l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
	port = int(os.environ.get('PORT', 8080))
	app.run(host=ip, port=port, debug=True, reloader=True)
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
