#!/usr/bin/env python3.5
""" some HAP-python FS20 Accessories
	defines homekit accessory classes for fs20 type products like 
	thermo hygro meters; outlet switches; doorbutton; displays 
	fs20 is a domotica system which can/could be bought/found here: 
	https://www.elv.de/fs20-funkschaltsystem.html
	https://wiki.fhem.de/wiki/FS20_Allgemein
"""
import time
import random
import logging

from pyhap.accessory import Accessory,Bridge
from pyhap.const import CATEGORY_SENSOR,CATEGORY_SWITCH,CATEGORY_PROGRAMMABLE_SWITCH,CATEGORY_LIGHTBULB

from fs20_cul import devFS20,fs20commands
from lib.serComm import DEVT,serDevice
from lib.dbLogger import sqlLogger

__author__ = "Henk Jan van Aalderen"
__credits__ = ["Henk Jan van Aalderen", "Ivan Kalchev"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Henk Jan van Aalderen"
__email__ = "hjva@homail.nl"
__status__ = "Development"

logger = logging.getLogger(__name__)	# get logger from main program

def map_accessoryIds(driver):
	""" get map of device config to accessories using the HAP aid """
	config={}
	accs= driver.get_accessories()
	for acc in accs['accessories']:
		aid=acc['aid']
		#logger.info("aid=%s" % (acc['aid'],))
		for serv in acc['services']:
			#logger.debug("serv %s" % serv)
			for char in serv["characteristics"]:
				#logger.debug("char %s" % char)
				if char["description"]=="Name":
					devkey=char["value"]
					logger.info("charnm=%s aid=%s" % (devkey,aid))
					config[devkey] ={"aid":aid}
					#serDevice.config.setItem(devkey,{"aid":aid})
	return config

def persist_FS20_config(driver):	
	""" update device configuration with HAP aid assignments """
	serDevice.config.updateConfig(map_accessoryIds(driver))
	
def get_FS20_bridge(driver,config="fs20.json"):
	""" creates a HAP bridge which combines a number of fs20 accessories according to config"""
	serDevice.setConfig(config, newItemPrompt=None)

	bridge = FS20_Bridge(driver, 'breeBridge')
	bridge.dbStore=None
	logger.critical("pincode=%s" % driver.state.pincode.decode())
	for name,rec in serDevice.getConfig():
		acce=None
		if 'typ' in rec:
			aid=None
			if 'aid' in rec:
				aid=rec['aid']
			if rec['typ']==DEVT['temp/hum']:
				acce = S300_TmpHumSensor(driver, name, aid=aid)
			elif rec['typ']==DEVT['switch']: 
				acce = FS20_Switch(driver, name, aid=aid)
			elif rec['typ']==DEVT['motion']:
				acce = FS20_MotionSensor(driver, name, aid=aid)
			elif rec['typ']==DEVT['doorbell']:
				acce = FS20_Doorbell(driver, name, aid=aid)	
			elif rec['typ']==DEVT['dimmer']:
				acce = FS20_Dimmer(driver, name, aid=aid)			
			elif rec['typ']==DEVT['fs20']:
				acce = FS20_Accessory(driver, name, aid=aid)	# generic type
		if acce is None:
			logger.warning("not an accessory %s : %s" % (name,rec))
		else:
			if acce.aid is None:
				logger.error("assign unique name,aid and typ to %s in config:%s" % (name,config))
				# todo find max aid +1
			else:
				bridge.add_accessory(acce)
			logger.debug("adding %s (aid:%s) typ:%s to bridge " % (name,acce.aid,rec['typ']))
	return bridge


class FS20_Bridge(Bridge):
	""" is a HAP bridge which combines a number of fs20 accessories """	
	async def run(self):
		''' called by HAP accessorie_driver class
			receive message from serial port, update device states, store results
		'''
		#super().run()  # run bridge accessoiries
		
		dbfile = serDevice.config.getItem('dbFile','~/fs20store.sqlite')
		self.dbStore = sqlLogger(dbfile)	# must be created in same thread
		
		try:
			while not self.driver.loop.is_closed():  # run forever until stopped
			#while self.driver.loop.is_running():  # run forever until stopped
				for acc in self.accessories.values():
					await acc.device.receive_message() # check if some device has send a message
					rec = acc.check_status(self.dbStore)	
		finally:
			if not self.dbStore is None:
				self.dbStore.close()
				self.dbStore=None
			if not serDevice.config is None:
				serDevice.config.save()	# persist newly found devices
		
	async def stop(self):
		persist_FS20_config(self.driver)
		await super().stop()
		#self.dbStore.close()   must be in same thread!!
		#self.dbStore=None		
		
class FS20_Accessory(Accessory):
	""" base class for a fs20 accessory """
	category = CATEGORY_SENSOR

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		devkey = args[1] # display_name
		logger.info("setting up fs20 accessory %s aid:%s" % (devkey,self.aid))
		self.device = devFS20(devkey)		# used by bridge
		
	def check_status(self,store):
		""" checks last received state of a device """
		rec = self.device.device_status()
		if rec is None:
			logger.info("%s not received yet" % self.display_name)
		elif 'new' in rec:
			if rec['new']>=0:  # only send sample once
				if 'cmd' in rec:
					logger.warning("%s(%s) beeing set to %s externally" % (rec['name'],rec['typ'],rec['cmd']))	
		return rec
		
	def __getstate__(self):
		state = super().__getstate__()
		state['device'] = None
		return state

	def __setstate__(self, state):
		self.__dict__.update(state)
		logger.info("loading accessory state from %s with %s" % (self.display_name,state))
		self.device = devFS20(self.display_name)
			
class FS20_MotionSensor(FS20_Accessory):
	""" accessory for fs20 PIR sensor """
	category = CATEGORY_PROGRAMMABLE_SWITCH

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		serv = self.add_preload_service('MotionSensor')
		self.char_detected = serv.configure_char('MotionDetected')
		self.set_info_service(firmware_revision=None, manufacturer="elv.de", model=None, serial_number=None)

	def check_status(self,store):
		rec = super().check_status(store)
		if not rec is None:
			tick = rec['new']
			if tick>=0:
				self.char_detected.set_value(True)
				store.log('motion',1,source=self.display_name)
			if tick==-2:
				self.char_detected.set_value(False)	# reset status after a while
			#self.detected(rec['new'])
		return rec

	
class FS20_Switch(FS20_Accessory):
	""" An accessory to operate a remote mains switch
	"""
	category = CATEGORY_SWITCH

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		serv = self.add_preload_service('Switch')
		self.char_state = serv.configure_char('On', setter_callback=self.HAPsetting)
		self.set_info_service(firmware_revision=None, manufacturer="elv.de", model=None, serial_number=None)
		self.stat=False

	def check_status(self,store):
		rec = super().check_status(store)
		if not rec is None and rec['new']>=0:  # only send sample once
			self.stat = not self.stat
			self.notifyHAP()  # toggle stat
			store.log('switch',self.stat,source=self.display_name)
		return rec
 
	def HAPsetting(self, value):
		''' HAP issues to set switch position '''
		logger.info("set %s from %d to %d " % (self.display_name,self.stat,value))
		if value:
			self.device.send_command(cmd='on-old-for-timer',dur=60)
		else:
			self.device.send_command(cmd='off')
		self.stat = value

	def notifyHAP(self):
		''' notify HAP when switch was changed externally '''
		logger.info("switch state changing to %s" % self.stat)
		if self.char_state.value != self.stat:
			self.char_state.value = self.stat
			self.char_state.notify()

class FS20_Dimmer(FS20_Accessory):
	""" An accessory to operate a remote mains dimmer
	"""
	category = CATEGORY_LIGHTBULB

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		serv = self.add_preload_service('Lightbulb', chars=['On','Brightness'])
		self.char_on = serv.configure_char('On', setter_callback=self.HAPonoff)
		self.char_lev = serv.configure_char('Brightness', setter_callback=self.HAPsetting)
		self.stat=True  # on off
		self.level=0

	def check_status(self,store):
		''' notify HAP on device changes '''
		rec = super().check_status(store)
		if not rec is None and rec['new']>=0:  # only send sample once
			cmd=fs20commands.index(rec['cmd'])#=int(rec['cmd'],16)
			if fs20commands[cmd] =='dimup':
				self.level+=1
			elif fs20commands[cmd] =='dimdown':
				self.level -=1
			elif fs20commands[cmd] =='off':
				self.stat = False
			elif fs20commands[cmd] =='on':
				self.stat = True
				if self.level<1:
					self.level=8
			elif cmd in range(1,16):
				self.level = cmd
			self.notifyHAP()  # toggle stat
			store.log('dimmer',self.level,source=self.display_name)
		return rec

	def HAPonoff(self, value):
		''' getting ev from HAP '''
		if value:
			self.device.send_command(cmd='on') # to level @ off
		else:
			self.device.send_command(cmd='off')

	def HAPsetting(self, value):
		''' HAP issues to set level '''
		value *= (16/100) # scale to dim command
		logger.info("set %s from %d to %d " % (self.display_name,self.level,value))
		self.level = int(value)
		if self.level>0:
			self.device.send_command(cmd=fs20commands[self.level])
		else:
			self.device.send_command(cmd='off')

	def notifyHAP(self):# toggle=True):
		''' notify HAP when device was changed externally '''
		perc=100.0/16.0*self.level
		logger.info("dimmer state changing to %s" % self.stat)
		if self.char_lev.value != perc:
			self.char_lev.value = perc
			self.char_lev.notify()
		if self.char_on.value!= self.stat:
			self.char_on.value = self.stat
			self.char_on.notify()


class FS20_Doorbell(FS20_Accessory):
	""" An accessory to react on doorbell presses
	"""
	category = CATEGORY_PROGRAMMABLE_SWITCH

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		serv = self.add_preload_service('StatelessProgrammableSwitch')
		self.char_state = serv.configure_char('ProgrammableSwitchEvent', setter_callback=self.hapringing)
		#self.set_info_service(firmware_revision=None, manufacturer="elv.de", model=None, serial_number=None)
		
	def hapringing(self, presscount):
		logger.info("doorbell ringing :%d" % presscount)
		
	def check_status(self,store):
		rec = super().check_status(store)
		if not rec is None:
			tick = rec['new']
			if tick>=0:
				self.char_state.set_value(1)
				store.log('ringing',1,source=self.display_name)
			if tick==-2:
				self.char_state.set_value(0)	# reset status after a while
		return rec
 		

class S300_TmpHumSensor(FS20_Accessory):
	""" Accessory for S300TH temperature/humidity sensor """
	category = CATEGORY_SENSOR

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		serv_tmp = self.add_preload_service('TemperatureSensor')
		serv_hum = self.add_preload_service('HumiditySensor')
		self.char_temperature = serv_tmp.get_characteristic('CurrentTemperature')
		self.char_humidity = serv_hum.get_characteristic('CurrentRelativeHumidity')
		
	def check_status(self,store):
		rec = super().check_status(store)
		if not rec is None and rec['new']>=0:  # only send sample once
			self.char_temperature.set_value(rec["Tmp"])
			self.char_humidity.set_value(rec["Hum"])
			store.log('temperature',rec['Tmp'],source=self.display_name)
			store.log('humidity',rec['Hum'],source=self.display_name)		
		return rec

	
