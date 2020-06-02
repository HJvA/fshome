""" linking HAP-python  Accessories to fshome sampler class
"""
import time,asyncio
import logging
logger = logging.getLogger(__name__)	# get logger from main program

from lib.devConst import DEVT
from pyhap.accessory import Accessory,Bridge
from pyhap.const import CATEGORY_SENSOR,CATEGORY_SWITCH,CATEGORY_PROGRAMMABLE_SWITCH,CATEGORY_LIGHTBULB

RUNINTERVAL=1.0

class fsBridge(Bridge):
	_samplers={}		# static dict of unique samplers
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		logger.critical("pincode=%s" % self.driver.state.pincode.decode())
		logger.info("samplers in bridge :%s" % [nm for nm,smp in fsBridge._samplers.items()])

	@Accessory.run_at_interval(RUNINTERVAL)  
	async def run(self):
		''' called by HAP accessorie_driver class servicing all samplers '''
		for nm,sampler in fsBridge._samplers.items():
			remi = 1
			while remi>0:
				remi = await sampler.receive_message()
			if remi:
				logger.debug("running sampler :%s having %s" % (nm,remi))
		await super().run()  # getting accessories
		await asyncio.sleep(RUNINTERVAL/10.0)
			
	
	def add_sampler(self, sampler, quantities):
		''' add a sampler to the HAP bridge '''
		logger.info("adding %s with %s to fsBridge" % (sampler.name,quantities))
		qaid={}
		fsBridge._samplers[sampler.name] = sampler
		for quantity,rec in quantities.items():
			if 'typ' in rec:
				typ=rec['typ']
			else:
				typ=DEVT['unknown']
			if typ<90 and quantity.isnumeric():
				if 'aid' in rec:	# it is an apple HAP item
					if rec['aid'] in qaid:
						qaid[rec['aid']].append(int(quantity))
					else:
						qaid[rec['aid']] = [int(quantity)]
		for aid,qs in qaid.items():
			acce = sampler.create_accessory(self.driver, quantities=qs, aid=aid)
			self.add_accessory(acce)
			
	async def stop(self):
		for nm,samp in fsBridge._samplers.items():
			samp.exit()
		await super().stop()	
			
class sampler_accessory(Accessory):
	""" HAP accessory for fs sampler """
	def __init__(self, *args, sampler, **kwargs):
		super().__init__(*args, **kwargs)
		self.receiver = sampler.name
			
	#@Accessory.run_at_interval(RUNINTERVAL)  # allready called explicit in bridge runner
	async def run(self):
		''' called by HAP accessorie_driver class '''
		#logger.debug("checking %s in %s nm:%s" % (self.quantity,self.receiver,self.display_name))
		if self.check_status() is None:
			#logger.debug("no more items for %s" % self.quantity)
			await asyncio.sleep(RUNINTERVAL/10.0)
		else:
			await asyncio.sleep(RUNINTERVAL/10.0)

	def qtype(self, qkey):
		''' quantity DEVT type '''
		sampler = fsBridge._samplers[self.receiver]  #sampler_accessory.receivers[self.receiver]
		return sampler.qtype(qkey)

	def check_status(self):
		""" checks last received state of a device and notify HAP when something has changed """
		val=None
		sampler = fsBridge._samplers[self.receiver]
		for qtt in self._chars:  #,rec in sampler.servmap.items():
			if sampler.isUpdated(qtt):
				val = sampler.get_last(qtt)
				typ = sampler.qtype(qtt)
				if typ==DEVT['motion'] or typ==DEVT['button']:
					self.sendValue(True if val else False,qtt)
				elif typ==DEVT['doorbell']:
					self.sendValue(True if val else False,qtt)
				else:
					self.sendValue(val,qtt)
				#logger.warning("sending %s to hap %s" % (qtt,val))			
		return val	
		
class HAP_accessory(sampler_accessory):
	""" base class for a accessory """
	category = CATEGORY_SENSOR
	
	def __init__(self, *args, quantities, stateSetter, **kwargs):
		super().__init__(*args, **kwargs)
		#logger.info("adding HAP acce:%s typ:%d kw:%s" % (quantity,typ,kwargs))

		self.stateSetter = stateSetter
		self._chars={}

		for quantity in quantities:
			self.addService(quantity, self.qtype(quantity)) #quantities[quantity]['typ'])
			if 'lev' in self._chars[quantity]:
				val =fsBridge._samplers[self.receiver].get_state(quantity)
				if val is not None:
					self._chars[quantity]['lev'].set_value(val)
					logger.info("set val:%s to %s" % (val,quantity))
	
		self.set_info_service(firmware_revision=None, manufacturer=fsBridge._samplers[self.receiver].manufacturer, model=None, serial_number=None)
		#self.stat = None
		#devkey = args[1] # display_name
		logger.info("setting up HAP_accessory %s aid:%s manuf:%s" % (args[1],self.aid, fsBridge._samplers[self.receiver].manufacturer))
		
	def addService(self, quantity, typ):
		''' add HAP service to this accessory '''
		serv=None
		if typ==DEVT['switch']:
			self.level=None
			serv = self.add_preload_service('Switch')
			self._chars[quantity] = {'lev': serv.configure_char('On',setter_callback=self.HAPswitching)}
		elif typ==DEVT['outlet']:
			self.level=None
			serv = self.add_preload_service('Outlet')
			self._chars[quantity] = {'lev': serv.configure_char('On',setter_callback=self.HAPswitching)}
			self.char_inuse = serv.configure_char('OutletInUse')
		elif typ==DEVT['lamp']:	# special class for this use derived class : HUE_accessory
			self.level=None
		elif typ==DEVT['dimmer']:
			self.level=None
			serv = self.add_preload_service('Lightbulb', chars=['On','Brightness'])
			self._chars[quantity] = {'bri': serv.configure_char('Brightness',setter_callback=self.HAPsetlev)}
			self._chars[quantity].update({'on': serv.configure_char('On',setter_callback=self.HAPonoff)})
		elif typ==DEVT['doorbell']:
			serv = self.add_preload_service('StatelessProgrammableSwitch')
			self._chars[quantity] = {'lev': serv.configure_char('ProgrammableSwitchEvent',setter_callback=self.HAPringing)}
		elif typ==DEVT['motion']:
			serv = self.add_preload_service('MotionSensor')
			self._chars[quantity] = {'lev': serv.configure_char('MotionDetected')}
		elif typ==DEVT['temperature']:
			serv = self.add_preload_service('TemperatureSensor')
			self._chars[quantity] = {'lev': serv.get_characteristic('CurrentTemperature')}
		elif typ==DEVT['humidity']:
			serv = self.add_preload_service('HumiditySensor')
			self._chars[quantity] = {'lev': serv.get_characteristic('CurrentRelativeHumidity')}
		elif typ==DEVT['energy']:
			serv = self.add_preload_service('BatteryService')
			self._chars[quantity] = {'lev': serv.configure_char('BatteryLevel')}
			self._chars[quantity].update({'act': serv.configure_char('ChargingState')})
			self._chars[quantity].update({'stl': serv.configure_char('StatusLowBattery')})
		logger.info("adding HAP service:%s with typ:%d for quantity:%s to aid:%s" % (serv,typ,quantity,self.aid))
		
	def sendValue(self, value, quantity=None):
		''' send myvalue to HAP '''
		if quantity in self._chars:
			self._chars[quantity]['lev'].set_value(value)
			logger.info("send HAP val %s to %s quantity:%d" % (value,self.display_name,quantity))
		else:
			logger.warning("no hap quantity like:%s for:%s in %s" % (quantity,value,self._chars))
	
	def setValue(self, value, prop=None):
		''' send val to device '''
		for qtt in self._chars:
			#for prp in self._chars[qtt]:
			#	if prop is None or prp==prop:
			#		logger.info("setting %s to %s with %s" % (qtt,value,prp))
			logger.info("setting %s to %s with %s" % (qtt,value,prop))
			return self.stateSetter(qtt,value,prop)

	def HAPonoff(self, value):
		''' HAP issues to set something '''
		self.setValue(1 if value else 0, 'on')
		
	def HAPsetlev(self, value):
		''' HAP issues to set level for dimmer or lamp '''
		logger.warning("setting %s from %s to %d " % (self.display_name,self.level,value))
		for qtt in self._chars: 
			self.stateSetter(qtt, value)
			self.level=value

	def HAPswitching(self, value):
		''' HAP issues to operate an outlet '''
		logger.info("setting %s from %s to %s " % (self.display_name,self.level,value))
		for qtt in self._chars:
			self.stateSetter(qtt, value)
			self.level=value

	def HAPringing(self, presscount):
		logger.info("doorbell ringing :%d" % presscount)

	def __getstate__(self):
		state = super().__getstate__()
		logger.info("saving accessory state:%s" % state)
		self.stateSetter = None
		return state

	def __setstate__(self, state):
		self.__dict__.update(state)
		logger.info("loading accessory state from %s with %s" % (self.display_name,state))
		#self.device = devFS20(self.display_name)
