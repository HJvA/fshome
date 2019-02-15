#!/usr/bin/env python3.5
""" classes for serial transceiver devices
	run this to discover fs20 devices around
like the CUL from http://busware.de/tiki-index.php?page=CUL
firmware: culfw.de
info: https://wiki.fhem.de/wiki/CUL
"""

import time
import logging
import os,sys
if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../../lib'))
	from serComm import serComm,serDevice,DEVT,forever,DEVICE
else:
	from lib.serComm import serComm,serDevice,DEVT,forever,DEVICE

__author__ = "Henk Jan van Aalderen"
__email__ = "hjva@notmail.nl"

"""  https://github.com/hobbyquaker/cul  """
fs20commands = [
  "off",   
  "dim06%", "dim12%", "dim18%", "dim25%", "dim31%", "dim37%", "dim43%", "dim50%", "dim56%",
  "dim62%",  "dim68%","dim75%", "dim81%", "dim87%", "dim93%", "dim100%",   
  "on",		# Set to previous dim value (before switching it off)
  "toggle",	# between off and previous dim val
  "dimup",   "dimdown",   "dimupdown",
  "timer",
  "sendstate",
  "off-for-timer",   "on-for-timer",   "on-old-for-timer",
  "reset",
  "ramp-on-time",      #time to reach the desired dim value on dimmers
  "ramp-off-time",     #time to reach the off state on dimmers
  "on-old-for-timer-prev", # old val for timer, then go to prev. state
  "on-100-for-timer-prev" # 100% for timer, then go to previous state
]
  
fs20sender=[
         "fs20fms","fs20hgs","fs20irl","fs20kse","fs20ls",
         "fs20pira","fs20piri","fs20piru","fs20s16","fs20s20","fs20s4 ","fs20s4a","fs20s4m",
         "fs20s4u","fs20s4ub","fs20s8","fs20s8m","fs20sd ","fs20sn ","fs20sr","fs20ss",
         "fs20str","fs20tc1","fs20tc6","fs20tfk","fs20tk ","fs20uts","fs20ze","fs20bf","fs20si3" ]
fs20dimmer=[
         "fs20di ","fs20di10","fs20du" ]
fs20actor=[
         "fs20as1","fs20as4","fs20ms2","fs20rgbsa","fs20rst",
         "fs20rsu","fs20sa","fs20sig","fs20sm4","fs20sm8","fs20st","fs20su","fs20sv","fs20ue1",
         "fs20usr","fs20ws1" ]

"""
sub
hex2four($)
{
  my $v = shift;
  my $r = "";
  foreach my $x (split("", $v)) {
    $r .= sprintf("%d%d", (hex($x)/4)+1, (hex($x)%4)+1);
  }
  return $r;
}

#############################
sub
four2hex($$)
{
  my ($v,$len) = @_;
  my $r = 0;
  foreach my $x (split("", $v)) {
    $r = $r*4+($x-1);
  }
  return sprintf("%0*x", $len,$r);
}
"""
def hex2four(hexnr):
	''' translate received nr to elv code where only first 2 bits mean '''
	if type(hexnr) is str:
		hexnr = int(hexnr,16)
	m=1
	cif=0
	while hexnr>0:
		cif += m*((hexnr & 3) -1)
		hexnr = hexnr >> 2
		m *= 16
	return cif

class devS300TH(serDevice):
	""" communicator class for S300TH temperature and humidity sensor
		and base class for other CUL clients
		culfw.de		
	"""
	def __init__(self, devkey=None, transceiver=None):
		''' constructor : setup receiver 
		'''
		super(devS300TH, self).__init__(transceiver)
		self.devkey = devkey
		self.send_message("X21")  # prepare to receive known msg with RSSI

	def exit(self):
		self.send_message("X00")
		super(devS300TH, self).exit()
		
	def parse_message(self,msg):
		''' convert msg string to dict of items
		'''
		rec={}
		if len(msg)>2 and msg[0] in 'AFTKEHRStZrib':	# known cul messages
			msg = msg.strip('\r\n')
			rssi=int(msg[-2:],16)
			if rssi>128: rssi -= 256
			rssi = rssi/2 -74
			rec={"rssi":rssi}
		if msg[0]=='K':
			if len(msg)>=15:
				logger.error("KS300 not implemented")
			elif len(msg)>8:
				fb = int(msg[1],16)
				sgn = fb & 8 
				cde = (fb & 7) + 1
				typ = int(msg[2])	# will be 1
				temperature= float(msg[6] + msg[3] + "." + msg[4])
				if sgn!=0:
					temperature *= -1
				humidity = float(msg[7] + msg[8] + "." + msg[5])
				rec.update({"typ":typ,"devadr":"%d" % cde,"Tmp":temperature,"Hum":humidity})
			logger.debug("s300 rec:%s" % rec)
		return rec
		

class devFS20(devS300TH):
	""" communicator class for fs20 devices
	"""	
	def parse_message(self, msg):
		''' convert msg string to dict of items
		'''
		rec = super().parse_message(msg)	# keep receiving S300
		if len(msg)>8 and msg[0]=='F':
			hauscode = msg[1:5]
			devadr = msg[5:7]
			cde =int(msg[7:9],16)
			dur=None
			#typ=self.getConfigItem('typ')
			#if typ is None:
			typ=DEVT['fs20']  # device is recognised
			if cde & 0x20:	# extension bit
				ee=int(msg[9:11],16)
				i = (ee & 0xf0) / 16
				j = (ee & 0xf)
				dur = (2**i)*j*0.25
				cde &= 0xdf	# remove extensionbit
			logger.debug("fs20 msg:%s(%0x) %s(%0x) %s %s" % (hauscode,hex2four(hauscode),devadr,hex2four(devadr),cde,dur))
			rec.update({"typ":typ,"devadr":devadr,"hausc":hauscode,"cmd":fs20commands[cde],"dur":dur})
		return rec
		
	def send_command(self, hausc=None, devadr=None, cmd="toggle", dur=None):
		''' send message in fs20 format
		'''
		if hausc is None:
			hausc=self.getRecordItem('hausc')
		if devadr is None:
			devadr=self.getRecordItem('devadr')
		cde = fs20commands.index(cmd)
		ee=""
		if not dur is None:
			cde |= 0x20
			for i in range(0,12):
				if len(ee)==0:
					for j in range(0,15):
						val = (2**i)*j*0.25
						if val >= dur:
							ee = "%0.2X" % (i*16+j,)
							break
		cmd = "%0.2X" % cde
		logger.info("sending cmd:%s (%x) dur:%s to hc:%s adr:%s" % (cmd,cde,ee,hausc,devadr))
		self.send_message('F'+hausc+devadr+cmd+ee)

if __name__ == "__main__":
	""" run this to fill the fs20.json file with devices that are in the air. you will be prompted if a message from an unknown device arrives, to enter a name
	"""
	import asyncio
	logger = logging.getLogger()
	logger.addHandler(logging.StreamHandler())	# use console
	logger.setLevel(logging.DEBUG)
	loop = asyncio.get_event_loop()

	try:
		serDevice.setConfig("fs200.json",newItemPrompt="Enter a name for it:")
		dbfile = serDevice.config.getItem('dbFile','~/fs20store.sqlite')
		ComPort = serDevice.config.getItem('ComPort',DEVICE)
		cul = serComm(ComPort)
		logger.info("cul version %s" % cul.get_info(b'V\r\n'))
	
		FS20 = devFS20(transceiver=cul)
		FS20.send_command("1212", "32", "on-old-for-timer", 60)
		
		logger.info("waiting forever for messages comming in (press Ctrl c to stop it)")
		loop.run_until_complete(forever(FS20.receive_message))

		# would run this when synchronous
		while True:
			time.sleep(2)
			data = FS20.receive_message() 
			if data is None:
				logger.warning(".")
					
	except KeyboardInterrupt:
		logger.warning("terminated by ctrl c")
	FS20.exit()
	loop.close()

	serDevice.config.save("fs200.json")
	logger.critical('bye')
else:
	logger = logging.getLogger(__name__)	# get logger from main program
	