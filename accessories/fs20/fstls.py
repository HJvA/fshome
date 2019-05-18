from lib.devConst import DEVT
import logging
logger = logging.getLogger(__name__)	# get logger from main program

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

def parseS300(msg):
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
			rec.update({"typ":typ,"devadr":"%d" % cde,"temperature":temperature,"humidity":humidity})
		logger.debug("s300 rec:%s" % rec)
	return rec


def parseFS20(msg):
	if len(msg)>8 and msg[0]=='F':
		hauscode = msg[1:5]
		devadr = msg[5:7]
		cde =int(msg[7:9],16)
		dur=None
		typ=DEVT['fs20']  # device is recognised
		if cde & 0x20:	# extension bit
			ee=int(msg[9:11],16)
			i = (ee & 0xf0) / 16
			j = (ee & 0xf)
			dur = (2**i)*j*0.25
			cde &= 0xdf	# remove extensionbit
		logger.debug("fs20 msg:hc:%s(%0x) adr:%s(%0x) cde:%s dur:%s" % (hauscode,hex2four(hauscode),devadr,hex2four(devadr),cde,dur))
		rec={"typ":typ,"devadr":devadr,"hausc":hauscode,"cmd":fs20commands[cde],"dur":dur}
		return rec
	else:
		return {}
	
def FS20_command(hausc, devadr, cmd="toggle", dur=None):
	''' send message in fs20 format
	'''
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
	logger.info("sending cmd:%s (%x) dur:%s to hc:%s adr:%s" % (cmd,cde,ee,hausc,devadr))
	cmd = "%0.2X" % cde
	return 'F'+hausc+devadr+cmd+ee
	
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
