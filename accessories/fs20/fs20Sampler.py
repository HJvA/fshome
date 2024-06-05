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
from submod.pyCommon.serComm import serComm
from lib.sampleCollector import DBsampleCollector,forever
from lib.devConst import DEVT,qSRC
from submod.pyCommon.tls import get_logger

class fs20Sampler(DBsampleCollector):
	''' collects fs20 messages and filters and stores results'''
	manufacturer="elv.de"
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.serdev = serComm(fstls.DEVICE, fstls.BAUDRATE)
		quantities=kwargs['quantities']
		self.hausc = quantities['hausc']  # not realy a quantity !!
		self.serdev.send_message("X21")  # prepare to receive known msg with RSSI
		self.minqid=qSRC['fs20']
		#self.qtyp = super().quantitymap(quantities,'typ')
		self.defSignaller()
	
	def exit(self):
		super().exit()
		self.serdev.send_message("X00")
		self.serdev.exit()
		
	async def receive_message(self,timeout=0.4, minlen=8, termin='\r\n'):
		''' get sensors msg from the cul device and check for updates and process recu when new '''
		dt = datetime.now()
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
							logger.info("ignoring fs20 cmd:%s in %s" % (rec,msg))
						self.check_quantity(tstamp, dbid, val)
						return -1
					else:
						logger.info("unknown quantity in:%s" % rec)
						return -3
		return self.serdev.remaining(),await super().receive_message(dt)
		
	def set_state(self, quantity, state, prop=None, dur=None):
		''' setting state to actuator '''
		if not super().set_state(quantity, state, prop):
			return None
		typ=self.qtype(quantity)
		devadr=self.qdevadr(quantity)
		logger.info("setting state of:%s to adr:%s of typ:%s with:%s prop:%s" % (quantity,devadr,typ,state,prop))
		hausc = self.hausc
		cmd=None
		if typ==DEVT['outlet'] or typ==DEVT['switch'] or typ==DEVT['signal'] or prop=='on':
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
		elif typ==DEVT['doorbell']: # simulate bell
			cmd = state
			hausc = '4cfa'  # fixed hauscode for doorbell button
			prop = None
		else:
			cmd = state
		if cmd:
			cmd= fstls.FS20_command(hausc, devadr, cmd=cmd, dur=prop)
			self.serdev.send_message(cmd)
		return cmd


if __name__ == "__main__":  # for testing and discovering devices
	import asyncio
	logger = get_logger(__file__)
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
	logger = get_logger()	# get logger from main program
