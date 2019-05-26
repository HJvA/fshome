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

if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	from lib.serComm import serComm
else:
	from lib.serComm import serComm
	logger = logging.getLogger(__name__)	# get logger from main program
from lib.devConst import DEVT
from lib.dbLogger import julianday,prettydate
from lib.sampleCollector import DBsampleCollector,forever

# Serial Device
DEVICE = '/dev/ttyUSB0'
BAUDRATE = 115200

reOBIS = r"^(\d)\-(\d)\:(\d+\.\d+\.\d+)"

__author__ = "Henk Jan van Aalderen"
__version__ = "1.0.0"
__email__ = "hjva@notmail.nl"
__status__ = "Development"

# definition of quantities to be parsed from the telegram
# <keytelegram>:(<nameapp>,<factor>,<DEVT quantity type>)
p1QDEF={
	#'1.0.0':('tstamp',1),
	'1.7.0' :('PowerTotal'   ,1000,DEVT['power']), 	#W
	'21.7.0':('PowerL1'      ,1000,DEVT['power']),	#W
	'41.7.0':('PowerL2'      ,1000,DEVT['power']),
	'61.7.0':('PowerL3'      ,1000,DEVT['power']),
	'2.7.0' :('receivedPower',1000,DEVT['power']),
	'32.7.0':('VoltageL1'    ,1,DEVT['voltage']),	
	'52.7.0':('VoltageL2'    ,1,DEVT['voltage']),
	'72.7.0':('VoltageL3'    ,1,DEVT['voltage']),
	'31.7.0':('CurrentL1'    ,1,DEVT['current']),
	'51.7.0':('CurrentL2'    ,1,DEVT['current']),
	'71.7.0':('CurrentL3'    ,1,DEVT['current']),
	'24.2.1':('gasVolume'    ,1,DEVT['gasVolume']),
	'1.8.1' :('EnergyElectrLow',1,DEVT['energy']),	#Wh low tarif
	'1.8.2' :('EnergyElectrNorm',1,DEVT['energy'])	#Wh normal tarif
	}

class p1DSMR(DBsampleCollector):
	""" add DSMR specific methods to sampler class """
	manufacturer="netbeheernederland"
	def __init__(self,serdev=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if serdev is None:
			serdev=serComm(DEVICE,BAUDRATE)
		self.serdev = serdev
		self.tstamp = None
		self.minqid = 300
	
	def servicesmap(self,quantities):
		''' compute dict of recognised services from quantities config '''
		qtts=quantities.copy()
		for qid,rec in quantities.items():
			if 'name' in rec and not 'devadr' in rec:
				qtts[qid]['devadr']=next(adr for adr,tp in p1QDEF.items() if tp[0]==rec['name'])
			if 'devadr' in rec and not 'typ' in rec:
				qtts[qid]['typ']=p1QDEF[rec['devadr']][2]  # get typ from const
		return super().servicesmap(qtts)

		
	async def receive_message(self):
		line = await self.serdev.asyRead(timeout=0.1, termin=b'\r\n')	# msg is send every 1s
		remi = self.serdev.remaining()
		if line and len(line)>0:
			m = re.search(reOBIS, line)
			val = re.search(r"\((.*)\)", line)
			if m and val and len(val.groups())==1:
				val = val.group(1)
				#logger.debug('grps:%s val:%s' % (m.groups(),val))
				try:
					qkey = m.group(3)
					if qkey in p1QDEF and self.tstamp is not None:
						fval=float(val.split('*')[0])
						qid = self.qCheck(None,qkey,name=p1QDEF[qkey][0])	# create when not there
						self.qCheck(qid,qkey,typ=p1QDEF[qkey][2])	# define also typ
						self.check_quantity(self.tstamp, quantity=qid, val=fval*p1QDEF[qkey][1])
					elif qkey=='1.0.0':   #  tstamp
						dst=0 if val[-1]=='W' else 1 if val[-1]=='S' else None
						self.tstamp=time.mktime(time.strptime(val[:-1], "%y%m%d%H%M%S"))
						tz = timezone(timedelta(seconds=-time.timezone))
						#self.tstamp = tz.localize(tstamp)
						#logger.debug('tm:%s dst:%s tz:%s' % (prettydate(julianday(self.tstamp)),dst,tz))
						if not remi:
							remi=-1
				except ValueError as e:
					logger.error("bad num format in:%s for %s having:%s" % (val,qkey,e))
			elif line[0]=='/':
				identific = line
				self.actual={}
			elif line[0]=='!':
				crc = line[1:]
			else:
				logger.info('bad line:%s val:%s' % (line,val))
		return remi
	
if __name__ == "__main__":
	import asyncio
	logger = logging.getLogger()
	hand=logging.StreamHandler()
	hand.setLevel(logging.INFO)
	logger.addHandler(hand)	# use console
	logger.addHandler(logging.FileHandler(filename='smart.log', mode='w', encoding='utf-8')) #details to log file
	logger.setLevel(logging.DEBUG)
	logger.warning("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S")))
	
	QCONF = {  # example default configuration
	"300": {
     "typ": 20,
     "name": "PowerTotal",
     "source": "huis" },
	"302": {
     "typ": 22,
     "name": "VoltageL1",
     "source": "huis" },
	"303": {
     "typ": 23,
     "name": "CurrentL1",
     "source": "huis" },
	"310": {
     "typ": 21,
     "aid": 30,
     "name": "EnergyElectrLow",
     "source": "huis" },
	"311": {
     "typ": 21,
     "name": "EnergyElectrNorm",
     "source": "huis" },
	"320": {
     "typ": 31,
     "name": "gasVolume",
     "source": "huis" },
   "321": {
     "name":"receivedPower",
      "typ":98
     },
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
