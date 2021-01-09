import pygame

import sys,os,time,logging,asyncio,datetime
if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
else:
	pass
from lib.sampleCollector import DBsampleCollector
from lib.devConst import DEVT,QID
from lib.tls import get_logger
from lib.fsHapper import HAP_accessory,fsBridge
from lib.devConfig import devConfig


class sounder(DBsampleCollector):
	@property
	def manufacturer(self):
		return "RaspBerry default sound card"

	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.minqid=QID['SND']
		pygame.mixer.init()
		self.defSignaller()
	
	async def eventListener(self, signaller):
		''' activates signaller to other instrum when an event occurs '''
		#logger.info('%s eventListener %d sounds:%s' % (self.name,len(hueSampler.devdat),self.deCONZ))
		if 1:
			mcnt=0
			msg = None # await dev.eventListener()
			if msg:
				qid = self.qCheck(quantity=None,devadr=msg['id'])
				if qid and 'state' in msg:
					val = msg['state']
					logger.info('%s event on %s=>%s cnt:%s' % (devName,qid,val,mcnt))
					signaller.signal(qid, val)
					await asyncio.sleep(4)
					mcnt=0
				else:
					mcnt +=1
			else:
				await asyncio.sleep(0.01)
		logger.warning('no eventListener in %s, ' % (self,))
	
	async def setState(self, quantity, state, prop='bri'):
		if quantity in hueSampler.devdat:
			return await hueSampler.devdat[quantity].setState(prop, state)
		else:
			logger.warning('no such quantity:%s' % quantity)
	
	def set_state(self, quantity, state, prop="zounds/37.wav", dur=None):
		''' stateSetter for HAP to set device; set as callback for signaller 
			return True to ackknowledge event '''
		if not super().set_state(quantity, state, prop=prop):
			return None
		if quantity == self.minqid:   #in hueSampler.devdat:
			logger.info('playing:%s at vol:%s' % (prop,state))
			sound = pygame.mixer.Sound(prop)
			sound.set_volume(float(state))
			sound.play()
			#pygame.mixer.music.load(prop)
			#pygame.mixer.music.play()
			return True
		else:
			logger.warning('no such quantity:%s %d' % (quantity,self.minqid))
	
	def create_accessory(self, HAPdriver, quantities, aid):
		aname="-".join([self.qname(q) for q in quantities])
		return SND_accessory(HAPdriver, aname, quantities=quantities, stateSetter=self.set_state, aid=aid, sampler=self)


class SND_accessory(HAP_accessory):
	""" adding Sound to HAP accessory """
	def addService(self, quantity, typ):
		super().addService(quantity, typ)

def add_SND_to_bridge(bridge, config="sound.json"):
	conf = devConfig(config)
	conf.updateConfig({QID['SND']:{'typ':17,'name':'earamp'}})
	sampler = sounder(dbFile=None, quantities=conf.itstore, minNr=1, maxNr=2, minDevPerc=0)
	#sampler.minqid=None  # do not auto create
	bridge.add_sampler(sampler, conf.itstore)	


if __name__ == "__main__":
	import asyncio
	logger = get_logger(__file__,logging.INFO,logging.DEBUG) 
	conf={	# to be loaded from json file
		#"dbFile": "/mnt/extssd/storage/fs20store.sqlite"
		"dbFile": '~/fs20store.sqlite'
	}
	player = sounder(dbFile=conf['dbFile'], quantities={QID['SND']:{'typ':17,'name':'earamp'}})
	
	player.set_state(QID['SND'],0.5)

	#pygame.mixer.init()
	#pygame.mixer.music.load("zounds/37.wav")
	#pygame.mixer.music.play()
	while pygame.mixer.get_busy() == True:
		continue
else:	# this is running as a module
	logger = get_logger()  # get logger from main program