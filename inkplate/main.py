"""
https://inkplate.readthedocs.io/en/latest/micropython.html
"""

from inkplate import Inkplate
import time,sys
import urequests as requests
import ujson as json
import network
import machine
import ntptime
from secret import SSID,PASSWORD,IP
from grtls import julianday,prettydate

import onewire, ds18x20

class dsTemperatureSens:
	def __init__(self,pinnr=13):
		pin = machine.Pin(pinnr)  #, machine.Pin.IN, machine.Pin.PULL_UP)
		self._ds =  ds18x20.DS18X20(onewire.OneWire(pin))
		time.sleep_ms(50)
		roms = self._ds.scan()
		if roms:
			self.rom = roms.pop()
		else:
			self.rom = None	
		print('Found DS devices: ', len(roms))

	@property
	def active(self):
		return self.rom is not None
		
	def readSens(self):
		if self.active:
			self._ds.convert_temp()  # function to initiate a temperature reading
			time.sleep_ms(750)
			T = self._ds.read_temp(self.rom)
			#print(T, end=' ')
			return T

# display text fields txtsize:(width,height)
qFLDS = {	3 : (200, 24),  # dd
				4 : (180, 32),  # lbl
				10: (360, 80),  # rest
				12: (360, 100)
			}
# quantity definition: qkey:[x,y,lbl,unit,scale]
qUNTS = { 	231 : (20,70, 'Tin','°C',  1),
				574 : (20,220,'Tout','C',  1),
				403 : (420,70, 'CO2','ppm',0.01),
				402 : (420,220,'hum','%',  1)
			}
grKEY  = 403
grxPOS = 100
gryPOS = 350
grxWDTH= 600
gryHGTH= 200

def showText(txt,x,y,size=None,frm='{:>4}'):
	if size:
		display.setTextSize(size)
	else:
		size=4
	if frm:
		txt = frm.format(txt.upper())
	#wd = 20*size*len(txt)
	wd = qFLDS[size][0] # 240
	if x+wd>display.width():
		wd = display.width()-x-1
	#ht = size*6
	ht = qFLDS[size][1] #100
	
	print("disp txt:{} size={} wd:{} ht:{}".format(txt,size,wd,ht))
	display.fillRect(x,y,wd,ht,display.WHITE)  # clear area
	display.drawRect(x,y,wd,ht,display.BLACK)
	#display.partialUpdate()
	display.printText(x,y, txt)  # Default font has only upper case letters
	
def showNumber(num,x=100,y=100, size=4, frmt='{:5.1f}', lbl=''):
	display.setTextSize(size)
	cmd = frmt.format(num)
	showText(lbl+cmd,x,y,size)

def showRest(qk, qrec):
	lbl = qUNTS[qk][2]
	scale = qUNTS[qk][4]
	print("get rest val:{}:{}".format(qk,qrec))
	showNumber(qrec*scale, x=qUNTS[qk][0],y=qUNTS[qk][1], size=12)
	showText(lbl, qUNTS[qk][0],qUNTS[qk][1]-44, 4)

def showGraph(xdat,ydat,rad=3,clr=True):
	""" draw chart to grxPOS,gryPOS with xdat,ydat data and rad marker at each data point """
	if xdat and ydat:
		minx=min(xdat)
		maxx=max(xdat)
		miny=min(ydat)
		maxy=max(ydat)
	else: 
		return
	if minx>=maxx or miny>=maxy:
		return
	
	xscale = grxWDTH/(maxx-minx)
	yscale = gryHGTH/(maxy-miny)
	if clr:
		display.fillRect(grxPOS-rad, gryPOS-rad, grxWDTH+rad+rad, gryHGTH+rad+rad, display.WHITE)  # clear area
	display.drawRect(grxPOS, gryPOS, grxWDTH, gryHGTH, display.BLACK)
	
	utcnow=julianday(MJD=True)  #datetime.datetime.utcnow().timestamp()
	#itoday = next(i for i,x in enumerate(xdat) if x > utcnow)
	xp = int(grxPOS + (utcnow-minx)*xscale)
	if xp>grxPOS and xp<grxPOS+grxWDTH:  # now marker.
		display.drawLine(xp,gryPOS,xp,gryPOS+gryHGTH,4)
	
	if maxx-minx>9:
		xstp = 7 # a week
	elif maxx-minx>1:
		xstp=1  # a day
	else:
		xstp =1/24.0 # an hour
	nminx = (minx//xstp)*xstp  # normalise to multiples of xstp
	stps = [nminx+i*xstp+xstp for i in range(int((maxx-minx)//xstp))]
	print('graph min:{} {} max:{} {} xstp={} nstps={} today@{}'.format( nminx,miny,maxx,maxy, xstp,len(stps),utcnow))
	for jd in stps:
		xp = int(grxPOS + (jd-minx)*xscale)
		display.drawLine(xp,gryPOS,xp,gryPOS+gryHGTH,1)
	x0=y0=None
	for x,y in zip(xdat,ydat):
		xp = int(grxPOS + (x-minx)*xscale)
		yp = int(gryPOS + (maxy-y)*yscale)
		if x0 and y0:
			display.drawLine(x0,y0,xp,yp,4)
			time.sleep(0.1)
		if rad==2:
			display.drawCircle(xp,yp,rad,display.BLACK)
		elif rad==3:
			display.drawRect(xp-rad,yp-rad,rad+rad,rad+rad,display.BLACK)
		elif rad:
			display.fillCircle(xp,yp,rad,display.BLACK)
		x0=xp
		y0=yp
	#display.display()
		

# More info here: https://docs.micropython.org/en/latest/esp8266/tutorial/network_basics.html
def nic_connect(nic=None, ssid=SSID, password=PASSWORD):
	if nic is None:
		nic = network.WLAN(network.STA_IF) # either STA_IF OR AP_IF
	nic.active(True)
	if not nic.isconnected():
		print("connecting to network...")
		try:
			#nic.active(True)
			nic.connect(ssid, password)
			while not nic.isconnected():
				time.sleep(0.1)
		except Exception as ex:
			print("nic status:{} error:{}".format(nic.status(),ex))
			nic.disconnect()
			nic.active(False)
	return nic

def http_get(url):
	""" basic GET request """
	try:
		jsd={}
		rq = requests.get(url)
		#print("req:{}".format(rq.content))
		jsd = rq.json()
		print("jsd:",jsd)
		rq.close()
	except Exception as ex:
		print("http_get exception:{}".format(ex))
	return jsd

def fsRestGet(ipadr,port=8080, qkeys=[401,574], ssl=False, timeout=2, path='/lastval'):
	''' gets quantity values from restfull fshome api '''
	url='https://' if ssl else 'http://'
	url += ipadr
	if port:
		url += ':%d' % port
	url += path 
	url += '?qkeys=[{}]'.format(",".join(["{}".format(qk) for qk in qkeys]))
	print("fsRestGet:{}".format(url))
	resp = http_get(url)
	return resp
	
def fsRestPut(ipadr, qkey,qval, port=8080,ssl=False, timeout=2, path='/qsave'):
	''' puts quantity value to restfull fshome api '''
	url='https://' if ssl else 'http://'
	url += ipadr
	if port:
		url += ':%d' % port
	url += path 
	url += '?qkey={}&qval={}'.format(qkey,qval)
	print("fsRestPut:{}".format(url))
	rq = requests.put(url)
	return rq

def setTime():
	jd0 = julianday()
	time.sleep(0.4)
	ntptime.settime()
	jd = julianday()
	print("jd0:{}, jd:{}, RTC:{} ".format(jd0,jd, machine.RTC().datetime()))
	
	
if __name__ == "__main__":	
	display = Inkplate(Inkplate.INKPLATE_1BIT)
	nic = nic_connect()
	display.begin()
	print("fshome ink display:{} x {} battery:{} nic:{}".format( display.width(),display.height(),display.readBattery(),nic.ifconfig()))
	setTime()
	display.clean()
	dsT=None
	try:
		while True:
			lbl = prettydate(None)
			#print("starting jd:{}={}".format(jd,lbl))
			showText(lbl,600,20,3)
			if not nic.active():
				nic_connect(nic)
			if dsT and dsT.active: 
				T = dsT.readSens()
				showNumber(T,200,20,3,lbl='Tpin:')
				fsRestPut(IP,qkey=801,qval=T)
			else:
				dsT = dsTemperatureSens() 
			rests = fsRestGet(IP,qkeys=qUNTS.keys())
			if rests:
				for qk in rests.keys():  #qUNTS.keys():
					showRest(qk, rests[qk])
					if qk == grKEY:
						rec = fsRestGet(IP,qkeys=[qk],path='/somevals')
						if rec:
							ydat=rec[qk]
							xdat=rec[qk*10]
							#xdat=range(len(ydat))
							showGraph(xdat,ydat)
				display.display()
			else:
				print("got no rest")
				#break
			#display.partialUpdate()
			nic.active(False)
			machine.lightsleep(180000)
	except Exception as ex:
		print("main error:",ex)
		#print("exec:",sys.exc_info()[0])
		if nic.active():
			print("nics:{}".format(nic.scan()))
		#raise RuntimeError('Failed to continue') from ex
	finally:
		if nic and nic.active():
			nic.disconnect()
			print("nic disconnected")
		