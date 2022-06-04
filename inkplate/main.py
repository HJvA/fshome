"""
micropython for inkplate 6 device showing fshome data
https://inkplate.readthedocs.io/en/latest/micropython.html
"""
from micropython import const,mem_info
try:
	from inkplate6 import Inkplate
except ImportError:
	from inkplate6_PLUS import Inkplate
import time,sys,os
import urequests as requests
import ujson as json
import network
import ntptime

from secret import SSID,PASSWORD,IP
from grtls import julianday,prettydate,JulianTime
import inktls
from  inktls import scrWDTH,scrHGTH,showText,showNumber,showGraph
#import klok

import machine 
#import neopixel
import lib.onewire, lib.ds18x20, esp32
from lib.tmp117 import tmp117
from lib.scd30 import SCD30
from lib.bme680 import BME680;


DEBUG = const(0)

qkOWT = const(801)  # fshome db key
qkHUM = const(802)
qkTBME= const(803)
TBMEofs =-2.0
qkCO2 = const(804)
#qkECO2= const(805)
qkPRS = const(806)
qkVOC = const(807)
qkT117 = const(808)
qknms = {
	qkOWT:"Tpin",
	qkTBME:"Tbme",
	qkT117:"T117",
	qkHUM:"humidity",
	qkCO2:"CO2",
	#qkECO2:"ECO2",
	qkPRS:"Pressure",
	qkVOC:"VolOrgCmp"	}


class dsTemperatureSens:
	""" onewire temperature sensor """
	def __init__(self,pinnr=13):
		pin = machine.Pin(pinnr)  #, machine.Pin.IN, machine.Pin.PULL_UP)
		self._ds = lib.ds18x20.DS18X20(lib.onewire.OneWire(pin))
		time.sleep_ms(50)
		roms = self._ds.scan()
		print('Found DS devices: ', len(roms))
		if roms:
			self.rom = roms.pop()
		else:
			self.rom = None	

	@property
	def active(self):
		return self.rom is not None
		
	def readSens(self):
		if self.active:
			self._ds.convert_temp()  # function to initiate a temperature reading
			time.sleep_ms(750)
			try:
				T = self._ds.read_temp(self.rom)
				#print(T, end=' ')
				return T
			except Exception as ex:
				print ("bad dsT:{}".format(ex))	

#class un(enum.IntFlag):  # qUNTS tuple idx
unxP=0	# 
unyP=1	#
unSZ=2	#
unLBL=3	# 
unUNIT=4	# 
unSCL=5	# scale

# quantity definition: qkey:[x,y,size,lbl,unit,scale]
qUNTS ={	231  : (20,70,  12,'T buro','°C',  1),
			qkOWT: (20,70,  12,'T pin', '°C',  1),
			qkTBME:(20,70,  12,'T bme', '°C',  1),
			qkT117:(20,70,  12,'T 117', '°C',  1),
			574  : (20,220, 12,'T terr','°C',  1),
			qkCO2: (scrWDTH-380,70, 12,'CO2',  'ppm',0.01),   # 403
			915  : (scrWDTH-380,220,12,'O3',   'ppm',0.1),
			
			912  : (scrWDTH-181,scrHGTH-240, 5,'aqi', '',   1),
			qkHUM: (scrWDTH-181,scrHGTH-160, 5,'hum', '%',  1),  # 402
			300  : (scrWDTH-181,scrHGTH-80 , 5,'pow', 'W',  1)
		  }

qkSHOW = (574,912,915,300)  # for FLDS
grKEY  = qkCO2   # 403

def showRest(qk, qval):
	if qk in qUNTS:
		lbl = qUNTS[qk][unLBL]
		scale = qUNTS[qk][unSCL]
		size = qUNTS[qk][unSZ]
		height = inktls.qFLDS[size][1]
		if DEBUG:
			print("show rest:{}={} size:{},hght:{}".format(qk,qval,size,height))
		x=qUNTS[qk][unxP]
		y=qUNTS[qk][unyP]
		showNumber(qval*scale, x,y, size=size)						#value
		size=size -8 #min(max(height//7,2),12)
		y = y- int(max(height//2,20))
		#size = next(sz for sz,tp in qFLDS.items() if sz<=size)
		if DEBUG:
			print("show lbl:{}={} x:{},y:{},sz:{}".format(qk,lbl,x,y,size))
		showText(lbl, x=x,y=y, size=size)	#label
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
				time.sleep(0.5)
		except Exception as ex:
			print("nic status:{} error:{}".format(nic.status(),ex))
			nic.disconnect()
			nic.active(False)
	return nic

def http_get(url, timeout=10):
	""" basic GET request """
	try:
		jsd={}
		rq = requests.get(url)
		#print("req:{}".format(rq.content))
		jsd = rq.json()
		print("gotjsd:",jsd)
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
	jd0 = julianday() # before
	time.sleep(0.4)
	ntptime.settime()  # get time from ntp server
	url = "http://worldtimeapi.org/api/ip"
	tm = http_get(url) # just check
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
	tmp = tmp117.create(addr=0x48)
	scd = SCD30.create(addr=0x61)
	bme = BME680.create(addr=0x77)
	wdt = machine.WDT(timeout=300000)  # watchdog ms
	time.sleep(0)
	inktls.display.begin()
	#kl = klok.horloge()
	print("fshome {} display:{} x {} battery:{} T:{}°C ".format(os.uname().sysname, inktls.display.width(), inktls.display.height(), inktls.display.readBattery(), (esp32.raw_temperature()-32)/1.8 ))
	print("devs tmp:{}".format(tmp))
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
			showText(lbl, scrWDTH-200,20,3)
			if not nic.active():
				nic_connect(nic)
				time.sleep_ms(200)
			if scd is not None and scd.get_status_ready() == 1:
				time.sleep_ms(200)
				co2 = scd.read_measurement()
				if co2:
					fsRestPut(IP,qkey=qkCO2,qval=co2[0])
					showRest(qkCO2, co2[0])
					#fsRestPut(IP,qkey=qkOWT,qval=co2[1])
					#showRest(qkOWT, co2[1])
					fsRestPut(IP,qkey=qkHUM,qval=co2[2])
					showRest(qkHUM, co2[2])
				print("ppm,°C,H:{}".format(co2))
			if bme:
				#time.sleep_ms(200)
				T = bme.temperature+TBMEofs
				fsRestPut(IP,qkey=qkTBME,qval=T)
				showRest(qkTBME, T)
				P = bme.pressure
				fsRestPut(IP,qkey=qkPRS,qval=P)
				H = bme.humidity
				G = bme.gas
				fsRestPut(IP,qkey=qkVOC,qval=G)
				print("T:{} P:{} H:{} G:{}".format(T,P,H,G))
			if tmp:
				T = tmp.temperature
				showRest(qkT117, T)
				fsRestPut(IP,qkey=qkT117,qval=T)

			if dsT and dsT.active: 
				T = dsT.readSens()
				if T:
					#showRest(qkOWT, T)
					fsRestPut(IP,qkey=qkOWT,qval=T)
			else:
				dsT = dsTemperatureSens()   # try to connect
			
			showNumber(inktls.display.readBattery(),200,20,3, lbl='Vbatt:',frmt='{:5.2f}')
			rests = fsRestGet(IP,qkeys=qkSHOW)
			if rests:
				for qk in rests.keys():  #qUNTS.keys():
					showRest(qk, rests[qk])
				if grKEY:
					qk=grKEY
					rec = fsRestGet(IP,qkeys=[qk],path='/somevals')
					if rec:
						ydat=rec[qk]
						xdat=rec[qk*10]
						showGraph(xdat,ydat, title='{} [{}]'.format(qUNTS[qk][unLBL], qUNTS[qk][unUNIT]))
				if cnt % 10 == 0:
					print("dd:{}".format(prettydate(None)))
					inktls.display.clean()
					inktls.display.display()
				else:
					inktls.display.partialUpdate()
				cnt+=1
				#display.display();
			else:
				print("got no rest")
				#break
			#display.partialUpdate()
			nic.active(False)
			wdt.feed()
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
		