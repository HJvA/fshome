"""
micropython for inkplate 6 device showing fshome data
https://inkplate.readthedocs.io/en/latest/micropython.html
"""
from micropython import const,mem_info
from inkplate6 import Inkplate
import time,sys
import urequests as requests
import ujson as json
import network
import ntptime
from secret import SSID,PASSWORD,IP
from grtls import julianday,prettydate,JulianTime
import inktls
#import klok

import machine 
#import neopixel
import onewire, ds18x20, esp32

qkOWT = const(801)  # fshome db key

class dsTemperatureSens:
	""" onewire temperature sensor """
	def __init__(self,pinnr=13):
		pin = machine.Pin(pinnr)  #, machine.Pin.IN, machine.Pin.PULL_UP)
		self._ds = ds18x20.DS18X20(onewire.OneWire(pin))
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

#class un(enum.IntFlag):  # qUNTS tuple idx
unxP=0	# 
unyP=1	#
unSZ=2	#
unLBL=3	# 
unUNIT=4	# 
unSCL=5	# scale

# quantity definition: qkey:[x,y,size,lbl,unit,scale]
qUNTS ={	231  : (20,70,  12,'T buro','°C',  1),
			qkOWT: (20,70,  12,'T pin','°C',  1),
			574  : (20,220, 12,'T terras','°C',  1),
			403  : (420,70, 12,'CO2', 'ppm',0.01),
			915  : (420,220,12,'ozo', 'ppm',0.1),
			
			912  : (619,360, 5,'aqi', '',   1),
			402  : (619,440, 5,'hum', '%',  1),
			300  : (619,520, 5,'pow', 'W',  1)
		  }

qkSHOW = (402,574,403,912,915,300)  # for FLDS
grKEY  = 403

def showRest(qk, qval):
	if qk in qUNTS:
		lbl = qUNTS[qk][unLBL]
		scale = qUNTS[qk][unSCL]
		size = qUNTS[qk][unSZ]
		height = inktls.qFLDS[size][1]
		print("show rest:{}={} size:{},hght:{}".format(qk,qval,size,height))
		x=qUNTS[qk][unxP]
		y=qUNTS[qk][unyP]
		inktls.showNumber(qval*scale, x,y, size=size)						#value
		size=size -8 #min(max(height//7,2),12)
		y = y- int(max(height//2,20))
		#size = next(sz for sz,tp in inktls.qFLDS.items() if sz<=size)
		print("show lbl:{}={} x:{},y:{},sz:{}".format(qk,lbl,x,y,size))
		inktls.showText(lbl, x=x,y=y, size=size)	#label
	else:
		print('qk{} not in qUNTS'.format(qk))

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
	if qkeys:
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
	rq = None
	try:
		rq = requests.put(url)
	except Exception as ex:
		print("http_put exception:{}".format(ex))
	if rq:
		rq.close()

def setTime():
	jd0 = julianday()
	time.sleep(0.4)
	ntptime.settime()
	url = "http://worldtimeapi.org/api/ip"
	tm = http_get(url)
	if tm:
		dt = tm['datetime']
		utcofs = tm['utc_offset']  # '+02:00'
		tz = tm['abbreviation']		# 'CEST'
		dst = tm['dst']
	jd = julianday()
	print("jd0:{}, jd:{}, RTC:{} ".format(jd0,jd, machine.RTC().datetime()))
	
	
if __name__ == "__main__":	
	inktls.display = Inkplate(Inkplate.INKPLATE_1BIT)
	nic = nic_connect()
	inktls.display.begin()
	#kl = klok.horloge()
	print("fshome ink display:{} x {} battery:{} T:{}°C".format( inktls.display.width(),inktls.display.height(),inktls.display.readBattery(), (esp32.raw_temperature()-32)/1.8))
	setTime()
	#display.clean()
	inktls.display.clearDisplay()
	inktls.display.display()
	dsT=None
	cnt=0
	mem_info()
	try:
		while True:
			lbl = prettydate(None)
			#print("starting jd:{}={}".format(jd,lbl))
			inktls.showText(lbl,600,20,3)
			if not nic.active():
				nic_connect(nic)
			if dsT and dsT.active: 
				T = dsT.readSens()
				showRest(qkOWT, T)
				fsRestPut(IP,qkey=qkOWT,qval=T)
			else:
				dsT = dsTemperatureSens()   # try to connect
			
			inktls.showNumber(inktls.display.readBattery(),200,20,3, lbl='Vbatt:',frmt='{:5.2f}')
			rests = fsRestGet(IP,qkeys=qkSHOW)
			if rests:
				for qk in rests.keys():  #qUNTS.keys():
					showRest(qk, rests[qk])
					if qk == grKEY:
						rec = fsRestGet(IP,qkeys=[qk],path='/somevals')
						if rec:
							ydat=rec[qk]
							xdat=rec[qk*10]
							inktls.showGraph(xdat,ydat, title='{} [{}]'.format(qUNTS[qk][unLBL], qUNTS[qk][unUNIT]))
				if cnt % 6 == 0:
					inktls.display.clean()
					inktls.display.display()
				else:
					inktls.display.partialUpdate()
				cnt+=1
				#display.display()
			else:
				print("got no rest")
				#break
			#display.partialUpdate()
			nic.active(False)
			machine.lightsleep(180000)
	except Exception as ex:
		print("main error:",ex)
		#exc_type, exc_obj, exc_tb = sys.exc_info()
		#print("exec:{}in{}".format(exc_type,exc_tb))
		if nic.active():
			print("nics:{}".format(nic.scan()))
		#raise RuntimeError('Failed to continue') from ex
	finally:
		if nic and nic.active():
			nic.disconnect()
			print("nic disconnected")
		