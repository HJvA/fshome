#!/usr/bin/env python3.5
""" fshome viewer for inkplate in peripheral mode """

import socket,aiohttp,re
import datetime,time
import logging
import json

if __name__ == "__main__":
	import sys,os
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
	
from lib.devConfig import devConfig
#from lib.dbLogger import sqlLogger,julianday,unixsecond,prettydate,SiNumForm
#from lib.devConst import DEVT,qCOUNTING,strokes,SIsymb
import lib.tls as tls # get_logger
from lib.grtls import julianday
from lib.serComm import serComm
from openweather import openweather,veldhoven

__copyright__="<p>Copyright &copy; 2019,2021, hjva</p>"
TITLE=r"fshome inkplate shower"
CONFFILE = "./fs20.json"
# Serial Device
DEVICE = '/dev/ttyUSB0'
BAUDRATE = 115200
# inkplate commands
NR = '\n\r'
OK = '#?*'
CLS = '#K(1)*'
PON = '#Q(1)*'  # is powered
DISP = '#L(1)*'
PUPD = '#M({:0>3d},{:0>3d},{:0>3d})*' # partial update Y1,X2,Y2
MODE1 = '#I(1)*'
MODE3 = '#I(3)*'
TEMP = '#N(?)*'  # getTemperature
TCHP = '#O(n)*'
BATT = '#P(?)*'
TXTSZ = '#D({:0>2d})*'  # set text size
TXTPOS = '#E({:0>3d},{:0>3d})*'
DRTXT  = '#C("{}")*'  # draw text
DRRECT = '#4({:0>3d},{:0>3d},{:0>3d},{:0>3d},{:0>2d})*'   # #4(XXX,YYY,WWW,HHH,CC)*
DRLIN  = '#T({:0>3d},{:0>3d},{:0>3d},{:0>3d},{:0>2d},{:0>2d})*'   #1(XXX,YYY,III,JJJ,TT,CC)*
FLRCT  = '#8({:0>3d},{:0>3d},{:0>3d},{:0>3d},{:0>2d})*' # fill rect x,y,w,h,c

# quantity definition: qkey:[x,y,lbl,unit]
qunts = { 	401 : [100,80, 'Tin','°C'],
				574 : [100,200,'Tout','C'] }


async def restGet(ipadr,port=8080, qkey=401, ssl=False, timeout=2):
	''' gets quantity values from restfull fshome api '''
	url='https://' if ssl else 'http://'
	url += ipadr
	if port:
		url += ':%d' % port
	url += '/quantity' 
	headers = {'content-type': 'application/json'}
	stuff={}
	try:
		async with aiohttp.ClientSession() as session:
			async with session.get( url=url, timeout=timeout, ssl=ssl, params={'qkey':'%d' % qkey}) as response:
				logger.info('(%d)getting=%s' % (response.status,response.url))
				if response.status==200:
					try:
						stuff = await response.json()
						logger.debug('got:%s:%s' % (qkey,stuff))
					except aiohttp.client_exceptions.ContentTypeError as ex:
						stuff = await response.text()
						logger.warning('bad json:%s:%s' % (qkey,stuff))
						stuff=None
				else:
					logger.warning('bad response :%s on %s' % (response.status,url))
					await session.close()
					await asyncio.sleep(0.2)
	except asyncio.TimeoutError as te:
		logger.warning("hueAPI timeouterror %s :on:%s" % (te,url))
		await asyncio.sleep(10)
	except Exception as e:
		logger.exception("hueAPI unknown exception!!! %s :on:%s" % (e,url))
	#logger.debug('hueGET resource:%s with %s ret:%d' % (resource,r.url,r.status_code))
	return stuff
	
class inkplate(serComm):
	""" controler for inkplate display in peripheral mode """
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)	# serdev=DEVICE, baud=BAUDRATE, parity=PARITY
		self.txtSize = 8
		self.x=0
		self.y=0
		self.send_message(OK, termin=None)
		logger.info('resp:%s' % self.read(minlen=2,timeout=1, termin=None))
		
		time.sleep(0.2)
		
		self.send_message(PON, termin=NR)
		self.send_message(CLS, termin=NR)
		self.send_message(MODE1, termin=NR)
		self.send_message(DISP, termin=None)
		time.sleep(0.2)
	
	def showText(self,txt,x,y,size=None):
		if size:
			if size != self.txtSize:
				cmd = TXTSZ.format(size)
				self.send_message(cmd, termin=NR)
				self.txtSize=size
				time.sleep(1)
		self.send_message(FLRCT.format(x,y,100*len(txt),size*10,0))  # clear area
		cmd = TXTPOS.format(x,y)
		self.send_message(cmd, termin=NR)
		self.x=x
		self.y=y
		cmd = DRTXT.format(tls.bytes_to_hex(bytes(txt,'utf-8')))
		self.send_message(cmd.upper(), termin=NR)
		self.display()
		
	def showNumber(self,num,x=100,y=100, size=4, frmt='{:.1f}'):
		cmd = frmt.format(num)
		self.showText(cmd,x,y,size)
		
	def display(self,partuphght=40):
		""" update changes to be displayed """
		if partuphght:
			self.send_message(PUPD.format(self.y,self.x,self.y+partuphght))  # partial update
		else:
			self.send_message(DISP, termin=None)	# entire screen
		
	def _getNum(self,qv,decimals=1):
		""" get number from returned string """
		outer = re.compile("\((.+)\)")
		m = outer.search(qv)
		if m:
			return round(float( m.group(1)),decimals)
		return float('NaN')
		
	def readTemperature(self):
		self.send_message(TEMP, termin=NR)
		qv = self.readText(minlen=7,timeout=4, termin='\n')
		return self._getNum(qv)
		
	def readBattery(self):
		self.send_message(BATT, termin=NR)
		qv = self.readText(minlen=9,timeout=4, termin='\n')
		return self._getNum(qv,2)
		
class inkChart(inkplate):
	def __init__(self, *args, xpos=100,ypos=350,height=200,width=600, **kwargs):
		super().__init__(*args,  **kwargs)
		self.xpos=xpos
		self.ypos=ypos
		self.width=width
		self.height=height
	
	def jdMark(jd,minx,xscale,thickn=1):
		xp = int(self.xpos + (jd-minx)*xscale)
		if xp>self.xpos and xp<self.xpos+self.width:  # now marker
			self.send_message(DRLIN.format(xp,self.ypos,xp,self.ypos+self.height,1,thickn))
		
	def showGraph(self,xdat,ydat,clr=True):
		minx=min(xdat)
		maxx=max(xdat)
		miny=min(ydat)
		maxy=max(ydat)
		xscale = self.width/(maxx-minx)
		yscale = self.height/(maxy-miny)
		if clr:
			self.x=self.xpos
			self.y=self.ypos
			self.send_message(FLRCT.format(self.xpos,self.ypos,self.width,self.height,0)) # clear area
		time.sleep(0.4)
		cmd = DRRECT.format(self.xpos,self.ypos,self.width,self.height,2)  # cadre
		self.send_message(cmd)
		utcnow=julianday()  #datetime.datetime.utcnow().timestamp()
		#itoday = next(i for i,x in enumerate(xdat) if x > utcnow)
		xp = int(self.xpos + (utcnow-minx)*xscale)
		if xp>self.xpos and xp<self.xpos+self.width:  # now marker
			self.send_message(DRLIN.format(xp,self.ypos,xp,self.ypos+self.height,1,4))
		logger.info('graph min:{} {} max:{} {} today@{}'.format(minx,miny,maxx,maxy,utcnow))
		
		for jd in range(int(minx),int(maxx),1): # day markers
			xp = int(self.xpos + (jd+0.5-minx)*xscale)
			self.send_message(DRLIN.format(xp,self.ypos,xp,self.ypos+self.height,1,1))
		x0=y0=None
		for x,y in zip(xdat,ydat):
			xp = int(self.xpos + (x-minx)*xscale)
			yp = int(self.ypos + (maxy-y)*yscale)
			if x0 and y0:
				cmd = DRLIN.format(x0,y0,xp,yp,1,4)
				self.send_message(cmd)
				time.sleep(0.1)
			x0=xp
			y0=yp
		self.display()
		

async def mainLoop(inkpl,weather):
	itemp = otemp = intemp = None
	if config.hasItem('tailScale'):
		ip = config.getItem('tailScale')  # ip accessible by world, issued by tailScale
	else: # ip of localhost
		ip=socket.gethostbyname(socket.gethostname())
	port = int(os.environ.get('PORT', 8080))
	await weather.getCurrent()  # get lat lon
	
	while 1:
		for qk,lst in qunts.items():	
			qv = await restGet(ip,port,qkey=qk)
			if qv:
				qv = qv['qval'][-1]
				x = lst[0]
				y = lst[1]
				inkpl.showNumber(qv,x,y,12)
				inkpl.showText('%s %s' % (lst[2],lst[3]), x+300,y,4)
				time.sleep(0.5)
		forec = await weather.getPressureForecast()
		time.sleep(0.01)
		hist  = await weather.getHistory('pressure',2)
		inkpl.showGraph(hist[0]+forec[0], hist[1]+forec[1], clr=True)
		"""	
		qv = await restGet(ip,port,qkey=401)
		if qv:
			qv = qv['qval'][-1]
			if qv!=itemp:
				itemp=qv
				inkpl.showNumber(itemp,100,80,12)
				await asyncio.sleep(1)
		qv = await restGet(ip,port,qkey=574)
		if qv:
			qv = qv['qval'][-1]
			if qv!=otemp:
				otemp=qv
				inkpl.showNumber(otemp,100,200,12)
		qv = inkpl.readTemperature()
		if qv:
			if qv!=intemp:
				intemp=qv
				inkpl.showNumber(intemp,100,320,12)
		"""
		await asyncio.sleep(300)
		
if __name__ == '__main__':
	import socket,asyncio
	_loop = asyncio.get_event_loop()
	logger = tls.get_logger(__file__,logging.DEBUG,logging.DEBUG)
	
	config = devConfig(CONFFILE)
	inkpl=inkChart(DEVICE,BAUDRATE,'N')
	inkpl.flush()
	appkey = config['openweatherkey']
	weather = openweather(appkey, veldhoven)
	
	time.sleep(1)
	try:
		T = inkpl.readTemperature()
		B = inkpl.readBattery()
		logger.info('temp:%s batt:%s' % (T,B))
		remain = inkpl.remaining()
		time.sleep(1)	
		
		_loop.run_until_complete(mainLoop(inkpl,weather))
	finally :
		inkpl.exit()
	
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
	