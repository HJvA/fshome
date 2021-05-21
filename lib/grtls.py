""" small general purpose helpers """

import sys,os
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

def localtime(julianday):
	""" time struct incl DST and TZ """
	return time.localtime(unixsecond(julianday))

def unixsecond(julianday):
	''' convert julianday (UTC) to seconds since actual unix epoch '''
	if sys.implementation.name == "micropython":
		return int((julianday - 2440587.5 - 10957) * 86400.0)
	else: 
		return (julianday - 2440587.5) * 86400.0

def julianday(tunix = None, MJD=False):
	''' convert unix time i.e.  to julianday i.e. days since noon on Monday, January 1 4713 BC '''
	if tunix is None:
		if sys.implementation.name == "micropython":
			tunix = machine.RTC().datetime() # tuple (Y,M,D,H,M,S,,,)
		else:
			tunix = time.time()   # float seconds since 00:00:00 Thursday, 1 January 1970
		return julianday(tunix)
	elif isinstance(tunix ,(tuple,list)):
		_io=1 if sys.implementation.name == "micropython" else 0
		print("tupnow={}".format(tunix))
		Y=tunix[0]
		M=tunix[1]
		D=tunix[2]
		JDN = float(0)
		if MJD:
			JDN -= 2400000.5
		JDN += (1461 * (Y + 4800 + (M -14)//12))//4 
		JDN += (367 *(M - 2 - 12 * ((M - 14)//12)))//12 
		JDN -= (3 * ((Y + 4900 + (M - 14)//12)//100))//4 
		JDN += D - 32075
		# tunix[3] is wday
		JDN += (tunix[3+_io]-12)/24
		JDN += tunix[4+_io]/1440
		JDN += tunix[5+_io]/86400
		return JDN 
	if MJD:
		return (tunix / 86400.0) + 40587.0
	return (tunix / 86400.0 ) + 2440587.5  # epoch 1-1-1970 float

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
		return("{} {}:{}:{}").format(tobj[2],tobj[4],tobj[5],tobj[6])
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
	#logger = logging.getLogger()
	#hand=logging.StreamHandler()
	#hand.setLevel(logging.DEBUG)
	#logger.addHandler(hand)	
	# logger = tls.get_logger(__file__,logging.DEBUG,logging.DEBUG)
	#print('seconds since epoch : %s' % seconds_since_epoch())
	nw = time.time() + _S_DELTA
	jdnow = julianday(nw)
	jdhj = julianday((1961,3,12,15,15,0))
	jdt= julianday()
	print('hj={} now={} jdnow={} jdt={} date={}'.format(jdhj,nw,jdnow,jdt,prettydate(None)))
	pass
else:
	pass
	#logger = logging.getLogger(__name__)	# get logger from main program
	