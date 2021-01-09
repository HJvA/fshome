#!/usr/bin/env python3.5
""" class for dutch utility meters
	with DSMR P1 telegram serial protocol
	https://www.netbeheernederland.nl/_upload/Files/Slimme_meter_15_a727fce1f1.pdf
		
	OBIS IEC 62056
	The code consists of (up to) 6 group sub-identifiers marked by letters A to F. All these may or may not be present in the identifier (e.g. groups A and B are often omitted). In order to decide to which group the sub-identifier belongs, the groups are separated by unique separators:
A-B:C.D.E*F
- The A group specifies the medium (0=abstract objects, 1=electricity, 6=heat, 7=gas, 8=water ...)
- The B group specifies the channel. Each device with multiple channels generating measurement results, can separate the results into the channels.
- The C group specifies the physical value (current, voltage, energy, level, temperature, ...)
- The D group specifies the quantity computation result of specific algorythm
- The E group specifies the measurement type defined by groups A to D into individual measurements (e.g. switching ranges)
- The F group separates the results partly defined by groups A to E. The typical usage is the specification of individual time ranges.
"""

import logging,time,sys,os
from datetime import timezone,timedelta,datetime
import re
import asyncio

if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	from lib.serComm import serComm
	from lib.tls import get_logger
	logger = get_logger(__file__, logging.DEBUG, logging.DEBUG)
else:
	from lib.serComm import serComm
	logger = logging.getLogger(__name__)	# get logger from main program
from lib.devConst import DEVT,QID
from lib.dbLogger import julianday,prettydate
from lib.sampleCollector import DBsampleCollector,forever

# Serial Device
DEVICE = '/dev/ttyUSB0'
BAUDRATE = 115200

reOBIS = r"^(\d)\-(\d)\:(\d+\.\d+\.\d+)\((.*)\)"  # parses: "1-0:1.8.2(000754.925*kWh)"
reOBIS = r"^(\d)\-(\d)\:(\d+\.\d+\.\d+)(\(([\d\.]+[^()]+)\))+"  # parses: "1-0:1.8.2(000754.925*kWh)"


__author__ = "Henk Jan van Aalderen"
__version__ = "1.0.1"
__email__ = "hjva@notmail.nl"
__status__ = "Development"

# definition of quantities to be parsed from the telegram
# <keytelegram>:(<nameapp>,<factor>,<DEVT quantity type>)
p1QDEF={
	#'1.0.0':('tstamp',1),
	'1.7.0' :('PowerTotal'   ,1000,DEVT['power']),	#W
	'21.7.0':('PowerL1'      ,1000,DEVT['power']),	#W
	'41.7.0':('PowerL2'      ,1000,DEVT['power']),
	'61.7.0':('PowerL3'      ,1000,DEVT['power']),
	'2.7.0' :('receivedPower',1000,DEVT['power']),
	'32.7.0':('VoltageL1'    ,1   ,DEVT['voltage']),
	'52.7.0':('VoltageL2'    ,1   ,DEVT['voltage']),
	'72.7.0':('VoltageL3'    ,1   ,DEVT['voltage']),
	'31.7.0':('CurrentL1'    ,1   ,DEVT['current']),
	'51.7.0':('CurrentL2'    ,1   ,DEVT['current']),
	'71.7.0':('CurrentL3'    ,1   ,DEVT['current']),
	'24.2.1':('gasVolume'    ,1   ,DEVT['gasVolume']),
	'1.8.1' :('EnergyElectrLow' ,1,DEVT['energy']),	#Wh low tarif
	'1.8.2' :('EnergyElectrNorm',1,DEVT['energy'])	#Wh normal tarif
	}


"""
dsmr:"/Ene5\XS210 ESMR 5.0" => ('idf', '/Ene5\\XS210 ESMR 5.0')
dsmr:"0-0:1.0.0(200601220401S)" => ('1.0.0', 1591041841.0, '200601220401S')
dsmr:"1-0:1.8.1(001088.889*kWh)" => ('1.8.1', 1088.889)
dsmr:"1-0:1.8.2(001110.138*kWh)" => ('1.8.2', 1110.138)
dsmr:"1-0:1.7.0(00.089*kW)" => ('1.7.0', 0.089)
dsmr:"1-0:2.7.0(00.000*kW)" => ('2.7.0', 0.0)
dsmr:"1-0:32.7.0(233.0*V)" => ('32.7.0', 233.0)
dsmr:"1-0:31.7.0(000*A)" => ('31.7.0', 0.0)
dsmr:"1-0:21.7.0(00.089*kW)" => ('21.7.0', 0.089)
dsmr:"!F1FE" => ('crc', 'F1FE')
"""

_tstamp=None
def parseDSMR(line):
	global _tstamp
	if line and len(line)>0:
		m = re.search(reOBIS, line)
		if m and len(m.groups())==5: # and val and len(val.groups())==1:
			#logger.debug('grps:%s val:%s' % (m.groups(),m.group(4)))
			try:
				qkey = m.group(3)
				val = m.group(5)
				if qkey in p1QDEF and _tstamp is not None:
					fval=float(val.split('*')[0].replace('\x00',''))
					return (qkey,fval)
				elif qkey=='1.0.0':   #  tstamp
					dst=0 if val[-1]=='W' else 1 if val[-1]=='S' else None	# winter or summer time
					_tstamp=time.mktime(time.strptime(val[:-1], "%y%m%d%H%M%S"))
					#logger.debug('tstamp:%s dst:%s line:%s' % (_tstamp,dst,line))
					tz = timezone(timedelta(seconds=-time.timezone))
					return (qkey,_tstamp,val)
			except ValueError as e:
				if qkey in p1QDEF:
					logger.error("bad num format in:%s for %s having:%s" % (line,qkey,e))
		elif line.find(r'/')>=0:  # first in group
			identific = line
			return ('idf',line)
		elif line[0]=='!':  # last in group
			crc = line[1:]
			return ('crc',crc)
		elif m and m.groups():
			logger.info('bad dsmr line:%s: n.grp:%s:' % (line, len(m.groups()) if m else None))
		else:
			logger.debug('unreconised dsmr line:%s' % line)
	return None

class p1DSMR(DBsampleCollector):
	""" add DSMR specific methods to sampler class """
	manufacturer="netbeheernederland"
	def __init__(self,serdev=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if serdev is None:
			serdev=serComm(DEVICE,BAUDRATE)
		self.serdev = serdev
		self.tstamp = None
		self.minqid = QID['DSMR']
		self.defSignaller()
	
	def defServices(self,quantities):
		''' compute dict of recognised services from quantities config '''
		qtts=quantities.copy()
		for qid,rec in quantities.items():
			if 'name' in rec and not 'devadr' in rec:
				qtts[qid]['devadr']=next(adr for adr,tp in p1QDEF.items() if tp[0]==rec['name'])
			if 'devadr' in rec and not 'typ' in rec:
				qtts[qid]['typ']=p1QDEF[rec['devadr']][2]  # get typ from const
		return super().defServices(qtts)

	async def receive_message(self):
		dt = datetime.now()
		n=0  # max nr of lines to read
		remain = 0
		while n<333:  # must be large to catch up when behind
			n+=1
			line = await self.serdev.asyRead(timeout=0.01, termin=b'\r\n')	# msg is send every 1s
			remain = self.serdev.remaining()
			rec = parseDSMR(line)
			if rec:
				if rec[0] in p1QDEF:  # known quantity
					qkey=rec[0]
					fval=rec[1]
					qid = self.qCheck(None,qkey,name=p1QDEF[qkey][0])	# create when not there
					self.qCheck(qid,qkey,typ=p1QDEF[qkey][2])	# define also typ
					logger.debug('dsmr:"%s" => %s @ sinceAccept=%.6g' % (line, rec, self.sinceAccept(qid)))
					self.check_quantity(self.tstamp, quantity=qid, val=fval*p1QDEF[qkey][1])
				elif rec[0]=='1.0.0':
					self.tstamp=rec[1]
					val=rec[2]
					dst=0 if val[-1]=='W' else 1 if val[-1]=='S' else None
					self.tstamp=time.mktime(time.strptime(val[:-1], "%y%m%d%H%M%S"))
					tz = timezone(timedelta(seconds=-time.timezone))
					logger.debug('dsmr tstamp:%s dst:%s tz:%s val:%s:' % (prettydate(julianday(self.tstamp)), dst, tz, val))
				elif rec[0]=='idf':
					self.actual={}
				elif rec[0]=='crc':
					pass
				else:
					logger.warning('unknown dsmr:%s' % (rec,))
				await asyncio.sleep(0.001)  # give other coroos some time but not too much
			elif remain<18:
				break  # no rec and no remains
			if remain<=0:
				break  # all fetched
		if remain>99:
			logger.warning('dsmr remaining data in ser buffer flushed:%d tries:%d' % (remain,n))
			self.serdev.flush()
			await asyncio.sleep(0.1)
		return remain,await super().receive_message(dt)


if __name__ == "__main__":
	import asyncio
	
	QCONF = {  # example default configuration
	"300": {
     "devadr":"1.7.0",
     "name": "PowerTotal",
     "source": "huis" },
	"302": {
     "devadr":"32.7.0",
     "name": "VoltageL1",
     "source": "huis" },
	"303": {
     "devadr":"31.7.0",
     "typ":98,
     "name": "CurrentL1",
     "source": "huis" },
	"310": {
     "devadr":"1.8.1",
     "naid": 30,
     "name": "EnergyElectrLow",
     "source": "huis" },
	"311": {
     "devadr":"1.8.2",
     "name": "EnergyElectrNorm",
     "source": "huis" },
	"320": {
     "devadr":"24.2.1",
     "name": "gasVolume",
     "source": "huis" },
    "321": {
     "devadr":"2.7.0",
     "typ":98 }, 
    "322": {
     "name":"PowerL1",
     "typ":98 },
   #"dbFile": "/mnt/extssd/storage/fs20store.sqlite"
	"dbFile": '~/fs20store.sqlite'
   }
   
	loop = asyncio.get_event_loop()
	try:
		p1ser = serComm(DEVICE,BAUDRATE)
		p1obj = p1DSMR(p1ser, QCONF['dbFile'],maxNr=20, quantities=QCONF)

		loop.run_until_complete(forever(p1obj.receive_message))
	except KeyboardInterrupt:
		logger.exception("terminated by ctrl c")
	p1obj.exit()
	p1ser.exit()
	logger.critical("bye")
