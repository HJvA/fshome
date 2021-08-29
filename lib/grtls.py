""" small general purpose helpers """

import sys,os,math
#import logging
import re

if sys.implementation.name == "micropython":
	import utime as time
	import machine
	_S_DELTA = 946681200  # 2000-1-1  to 1970-1-1	=10957 days
else:
	import datetime
	import time
	_S_DELTA = 0

	def seconds_since_epoch(epoch = datetime.datetime.utcfromtimestamp(0), utcnow=datetime.datetime.utcnow()):
		''' time in s since 1970-1-1 midnight utc'''
		return (utcnow - epoch).total_seconds()

_MJD = float(2400000.5)

def localtime(julianday):
	""" time struct incl DST and TZ """
	return time.localtime(unixsecond(julianday))

def unixsecond(julianday):
	''' convert julianday (UTC) to seconds since actual unix epoch '''
	if sys.implementation.name == "micropython":
		return int((julianday - 2440587.5 - 10957.5) * 86400.0)  #  (2000-1970)*365.25
	else: 
		return (julianday - 2440587.5) * 86400.0

def julianday(tunix = None, isMJD=False):
	''' convert unix time i.e.  to julianday i.e. days since noon on Monday, January 1 4713 BC
		tunix can be either a float as returned by time.time() or a tuple as returned by 	'''
	if tunix is None:
		if sys.implementation.name == "micropython":
			tunix = list(machine.RTC().datetime()) # tuple (Y,M,D,H,M,S,,,)
			del tunix[3]
		else:
			tunix = time.time()   # float seconds since 00:00:00 Thursday, 1 January 1970
		#return julianday(tunix, isMJD)
	if isinstance(tunix ,(tuple,list)):
		#_io=1 if sys.implementation.name == "micropython" else 0
		#print("tupjd={}".format(tunix))
		Y,M,D = tunix[0:3]
		JDN = -_MJD if isMJD else 0.0
		mm = -1 if M<=2 else 0  #  math.trunc((M-14)/12)  # 0 or -1
		JDN += (1461 * (Y + 4800 + mm))//4 
		#if isMJD:
		#	JDN -= _MJD
		JDN += (367 *(M - 2 - 12 * mm)) //12 
		JDN -= (3 * ((Y + 4900 + mm)//100))//4 
		JDN += D - 32075
		#H,MM,S=tunix[4:7] if sys.implementation.name == "micropython" else tunix[3:6]
		H,MM,S=tunix[3:6]
		#if isMJD:
		#	JDN += (H)/24
		#else:
		JDN += (H-12)/24
		JDN += MM/1440
		JDN += S/86400
		print('Y-M-D H:M:S {}-{}-{} {}:{}:{}'.format(Y,M,D,H,MM,S))
		return JDN 
	elif _S_DELTA:
		tunix += _S_DELTA
	if isMJD:
		return (tunix / 86400.0) + 40587.0  # epoch midnight on November 17, 1858.
	return (tunix / 86400.0 ) + 2440587.5  # epoch noon on Monday, January 1 4713 BC

"""

"""
	
def JulianTime(jdn, isMJD=False):
	""" get (Y M D H M S) from julianday number see https://quasar.as.utexas.edu/BillInfo/JulianDatesG.html """
	if isMJD:
		F, I = math.modf(jdn)
		A = math.trunc((I + 532784.25)/36524.25)  # 2400000.5 - 1867216.25 = 532784.25
		I += 2400001
		#if F>0.5:
		#	I+=1
	else:
		jdn+=0.5 # => midnight
		F, I = math.modf(jdn)
		A = math.trunc((I - 1867216.25)/36524.25)
	if I > 2299160:
		B = I + 1 + A - math.trunc(A / 4.)
	else:
		B = I
	C = B + 1524
	D = math.trunc((C - 122.1) / 365.25)
	E = math.trunc(365.25 * D)
	G = math.trunc((C - E) / 30.6001)
	day = C - E + F - math.trunc(30.6001 * G)
	if G < 13.5:
		month = G - 1
	else:
		month = G - 13
	if month > 2.5:
		year = D - 4716
	else:
		year = D - 4715	
	hour = F % 1 *24
	minute = hour % 1 * 60
	second = minute % 1 * 60	
	return year,month,int(day),int(hour),int(minute),second
	
	
	
def weekday(jd, isMJD=False):
	""" 0=Sunday """
	if isMJD:
		return (jd+3) % 7
	return (jd+1.5) % 7
	
def prettydate(JulianDay, format="{:%d %H:%M:%S}"):
	''' generates string representation of julianday '''
	if not JulianDay:
		JulianDay=julianday()
		if sys.implementation.name == "micropython":
			tobj = machine.RTC().datetime()
		else:
			tobj = datetime.datetime.now() #  time.gmtime()
	else:
		if sys.implementation.name == "micropython":
			tobj = time.gmtime(unixsecond(JulianDay))
		else:
			tobj = datetime.datetime.fromtimestamp(unixsecond(JulianDay))
		#print("tobj={}".format(tobj.hour))
	if format=="#j4":
		fd = int(4*(JulianDay % 1))
		return ('after noon','evening','night','morning')[fd]	
	#print("tobj:{}".format(tobj))
	if sys.implementation.name == "micropython":
		return("{} {:02d}:{:02d}:{:02d}").format(tobj[2],tobj[4],tobj[5],tobj[6])
	return format.format(tobj)
	return ("{} {}:{}:{}").format(tobj.tm_mday,tobj.tm_hour,tobj.tm_min,tobj.tm_sec)
	return time.strftime(format, tobj)

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
		#logger.error("no data to graph")	
		return
	if vmax is None: 
		vmax = max(data)
	if vmin is None: 
		vmin = min(data)
	if vmax==vmin:
		sf=1.0
	else:
		sf = (height-1)/(vmax-vmin)
	#logger.info("curve min=%f max=%f sf=%f" % (vmin,vmax,sf))
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

if __name__ == "__main__":
	NAIS = (1961,3,12, 15,10,0,0)
	jdhj = julianday(NAIS)
	print(' JD: hj={} = jt:{} on wd:{}'.format(jdhj,JulianTime(jdhj),weekday(jdhj)))
	jdhj = julianday(NAIS,isMJD=True)
	print('MJD: hj={} = jt:{} on wd:{}'.format(jdhj,JulianTime(jdhj,isMJD=True),weekday(jdhj,True)))
	
	nw = time.time() 
	jdnow = julianday(nw)
	jdt = julianday()
	print('unixnow={} jdnow={} jdt={} wd={} prdate={}'.format(nw,jdnow,jdt,weekday(jdt),prettydate(None)))
	
	jdnow = julianday(nw,True)
	jdt = julianday(isMJD=True)
	print('MJDnow= jdnow={} jdt={} wd={} jt={}'.format(jdnow,jdt,weekday(jdt,True),JulianTime(jdt,True)))
	
else:
	pass
	#logger = logging.getLogger(__name__)	# get logger from main program
	