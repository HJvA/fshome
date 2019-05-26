#!/usr/bin/env python3.5
""" interface to fs20 family of devices
"""
import time
import logging,re
from datetime import datetime

if __name__ == "__main__":
	import sys,os,signal
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))
	import fstls
else:
	import accessories.fs20.fstls as fstls
from lib.serComm import serComm
from lib.sampleCollector import DBsampleCollector,forever
#from lib.fsHapper import HAP_sampler
#from fs20_cul import fs20commands
from lib.devConst import DEVT

DEVICE='/dev/ttyACM0'
BAUDRATE=9600

class fs20Sampler(DBsampleCollector):
	''' collects fs20 messages and filters and stores results'''
	manufacturer="elv.de"
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.serdev = serComm(DEVICE, BAUDRATE)
		quantities=kwargs['quantities']
		self.hausc = quantities['hausc']  # not realy a quantity !!
		self.serdev.send_message("X21")  # prepare to receive known msg with RSSI
		self.minqid=100
		#self.qtyp = super().quantitymap(quantities,'typ')
	
	def exit(self):
		super().exit()
		self.serdev.send_message("X00")
		self.serdev.exit()
		
	async def receive_message(self,timeout=2, minlen=8, termin='\r\n'):
		''' get sensors msg from the cul device and check for updates and process recu when new '''
		msg = await self.serdev.asyRead(timeout, minlen, bytes(termin,'ascii'))
		if msg:
			tstamp = time.time()  #datetime.now()
			rec = fstls.parseS300(msg)
			if rec and 'devadr' in rec:
				dbid = self.qCheck(None,rec['devadr'],DEVT['humidity']) 
				self.check_quantity(tstamp, dbid, rec['humidity'])
				dbid = self.qCheck(None,rec['devadr'],DEVT['temperature'])
				self.check_quantity(tstamp, dbid, rec['temperature'])
				return -2
			else:
				rec = fstls.parseFS20(msg)
				if rec and 'devadr' in rec:
					if 'typ' in rec and rec['typ']!=DEVT['fs20']:
						dbid = self.qCheck(None,rec['devadr'],rec['typ'])
					else:
						dbid = self.qCheck(None,rec['devadr'])
					if dbid is not None and 'cmd' in rec:	
						cmd = rec['cmd']
						val=None
						if cmd[:2]=='on':
							val=1
						elif cmd[:3]=='dim':
							mtch=re.search(r'[-\d.]+',cmd)
							if mtch:
								val=float(mtch[0])
						elif cmd=='toggle':
							val=1
						else:
							logger.info("ignoring fs20 cmd:%s" % cmd)
						self.check_quantity(tstamp, dbid, val)
						return -1
					else:
						logger.info("unknown quantity in:%s" % rec)
						return -3
		return self.serdev.remaining()
		
	def set_state(self, quantity, state, prop=None, dur=None):
		''' setting state to actuator '''
		typ=self.qtype(quantity)
		devadr=self.servmap[quantity][0]
		logger.info("setting state of:%s to adr:%s of typ:%s with:%s" % (quantity,devadr,typ,state))
		cmd=None
		if typ==DEVT['outlet'] or typ==DEVT['switch'] or prop=='on':
			if state:
				if dur:
					cmd='on-old-for-timer'
					#dur=60
				else:
					cmd='on'
			else:
				cmd='off'
		elif typ==DEVT['dimmer']:
			state *= (16/100) # scale to dim command
			self.level = int(state)
			if self.level>0:
				cmd = fstls.fs20commands[self.level]
			else:
				cmd ='off'
		else:
			cmd = state
		if cmd:
			cmd= fstls.FS20_command(self.hausc, devadr, cmd=cmd, dur=prop)
			self.serdev.send_message(cmd)


if __name__ == "__main__":  # for testing and discovering devices
	import asyncio
	logger = logging.getLogger()
	hand=logging.StreamHandler()
	hand.setLevel(logging.DEBUG)
	logger.addHandler(hand)	# use console
	logger.addHandler(logging.FileHandler(filename='fsSmp.log', mode='w', encoding='utf-8'))
	logger.setLevel(logging.DEBUG)
	logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S")))
	conf={	# to be loaded from json file
		#"dbFile": "/mnt/extssd/storage/fs20store.sqlite"
		"dbFile": '~/fs20store.sqlite',
		"hausc":"1212",
		"100":{
			"typ":0,
			"devadr":"1",
			"source":"zolder"
			},
		"101":{
			"typ":1,
			"devadr":"1",
			"source":"zolder"
			},		
		"102":{
			"typ":0,
			"devadr":"5",
			"source":"terras"
			},		
		"103":{
			"typ":1,
			"devadr":"5",
			"source":"terras"
			},		
		"104":{
			"typ":0,
			"devadr":"8",
			"source":"kgb"
			},		
		"105":{
			"typ":1,
			"devadr":"8",
			"source":"kgb"
			},		
		"106":{
			"typ":0,
			"devadr":"4",
			"source":"woon"
			},		
		"107":{
			"typ":1,
			"devadr":"4",
			"source":"woon"
			},		
		"109":{
			"typ":11,
			"devadr":"10",
			"source":"gang"
			},		
		"110":{
			"typ":11,
			"devadr":"33",
			"source":"traplicht"
			},		
		"112":{
			"typ":14,
			"devadr":"72",	# dimmer
			"source":"zolder"
			},		
		"116":{
			"typ":10,	# ringer
			"source":"entree",    
			"devadr": "00",
    		"hausc": "4CFA"	
			}
	}

	loop = asyncio.get_event_loop()

	try:
		fsSampler = fs20Sampler(dbFile=conf['dbFile'], quantities=conf, minNr=1, maxNr=2, minDevPerc=0)
		
		loop.run_until_complete(forever(fsSampler.receive_message))									
	except KeyboardInterrupt:
		logger.warning("terminated by ctrl c")
	fsSampler.exit()
	logger.critical("bye")
	
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
