""" small general purpose helpers """

import datetime
import time
import logging
import os,re,sys
import lib.tls

def seconds_since_epoch(epoch = datetime.datetime.utcfromtimestamp(0), utcnow=datetime.datetime.utcnow()):
	''' time in s since 1970-1-1 midnight utc'''
	return (utcnow - epoch).total_seconds()

def julianday(tunix = None):
	''' convert unix time i.e. seconds since 00:00:00 Thursday, 1 January 1970 to julianday i.e. days since noon on Monday, January 1 4713 BC '''
	if tunix is None:
		tunix = time.time()
	return (tunix / 86400.0 ) + 2440587.5
	
def localtime(julianday):
	return time.localtime(unixsecond(julianday))

def unixsecond(julianday):
	''' convert  julianday to '''
	return (julianday - 2440587.5) * 86400.0

def prettydate(julianday, format="%d %H:%M:%S"):
	''' generates string representation of julianday '''
	if format=="#j4":
		fd = int(4*(julianday % 1))
		return ('after noon','evening','night','morning')[fd]	
	return time.strftime(format, time.localtime(unixsecond(julianday)))

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
		logger.error("no data to graph")	
		return
	if vmax is None: 
		vmax = max(data)
	if vmin is None: 
		vmin = min(data)
	if vmax==vmin:
		sf=1.0
	else:
		sf = (height-1)/(vmax-vmin)
	logger.info("curve min=%f max=%f sf=%f" % (vmin,vmax,sf))
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
	logger = tls.get_logger(__file__,logging.DEBUG,logging.DEBUG)
	print('seconds since epoch : %s' % seconds_since_epoch())
else:
	logger = logging.getLogger(__name__)	# get logger from main program
	