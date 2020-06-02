if __name__ == "__main__":
	import sys,os
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))

import logging
from lib.devConst import DEVT


DEVICE='/dev/ttyACM0'
BAUDRATE=9600

"""  https://github.com/hobbyquaker/cul  """
fs20commands = [
  "off",		# 0 
  "dim06%", "dim12%", "dim18%", "dim25%", "dim31%", "dim37%", "dim43%", "dim50%", "dim56%",
  "dim62%",  "dim68%","dim75%", "dim81%", "dim87%", "dim93%", "dim100%",   
  "on",		# 17  Set to previous dim value (before switching it off)
  "toggle",	# between off and previous dim val
  "dimup",   "dimdown",   "dimupdown",
  "timer",
  "sendstate",
  "off-for-timer",		# 24
  "on-for-timer",   
  "on-old-for-timer",	# 26
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
	''' build message in fs20 format
	'''
	if type(cmd) is str:
		cde = fs20commands.index(cmd)
	else:
		cde = int(cmd)
		cmd = fs20commands[cde]
	ee=""
	if dur is not None:
		cde |= 0x20
		for i in range(0,12):
			if len(ee)==0:
				for j in range(0,15):
					val = (2**i)*j*0.25
					if val >= dur:
						ee = "%0.2X" % (i*16+j,)
						break
	logger.info("fs20 cmd:%s (%x) dur:%s to hc:%s adr:%s" % (cmd,cde,ee,hausc,devadr))
	cmd = "%0.2X" % cde
	return 'F'+hausc+devadr+cmd+ee
	
# hex  to pseudoquaternäre 
# 1212 => 12131213
def hex2four(hexnr):
	''' translate received hex (num or str) to elv code where only first 2 bits mean '''
	if type(hexnr) is str:
		hexnr = int(hexnr,16)
	m=1
	cif=0
	while hexnr>0:
		cif += m*((hexnr & 3) +1)
		hexnr = hexnr >> 2
		m *= 10
	return cif+m

	
def four2hex(fournr, formt="%02x"):
	if type(fournr) is str:
		fournr = int(fournr,10)
	m=1
	cif=0
	while fournr>0:
		cif += m*((fournr % 10) -1)
		fournr //= 10
		m *= 4
	if formt:
		return formt % cif
	return cif

if __name__ == "__main__":
	import sys,os,time
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))
	from lib.serComm import serComm
	import lib.tls as tls
	
	logger = tls.get_logger(__file__, logging.DEBUG)
	
	HAUSC = four2hex('12131213',"%04x")	# 0x1212
	
	codes = {
		"1414": {"name":'trapkast',	"cmd":26,"dur":60, "act":1},	# sound normaal & light
		"1311": {"name":'garage'  ,	"cmd":26,"dur":60, "act":0},	# sound uhahahaha & show
		"1313": {"name":'test1'   ,	"cmd":'off',"dur":None, "act":1},	# sound gr & show
		"1314": {"name":'test2'   ,	"cmd":'off',"dur":None, "act":1},	# sound tang & show

		"1111": {"name":'deurbel' ,	"cmd":'on',"dur":None, "hausc":'21414433', "act":0}, # sound normaal
		#"1111": {"name":'deurbel' ,	"cmd":'toggle',"dur":None, "hausc":'21414433', "act":1}, # sound up-up-up-up
		#"1111": {"name":'deurbel' ,	"cmd":'off',"dur":None, "hausc":'21414433', "act":1}, # sound
		#"1111": {"name":'deurbel' ,	"cmd":24,"dur":None, "hausc":'21414433', "act":1}, # none
		"1211": {"name":'gang'    ,	"cmd":26,"dur":None, "act":1},  # sound tjeu & show
		"4424": {"name":'lampen'  ,	"cmd":'off',"dur":None, "act":1}  # sound tring
		}
	
	serdev = serComm(DEVICE, BAUDRATE)
	serdev.send_message("X21")  # prepare to receive known msg with RSSI
	time.sleep(1)
	
	for adr,dct in codes.items():
		logger.info('%s with %s' % (adr,dct))
		if 'act' in dct and not dct['act']:
			continue
		devadr = four2hex(adr)  
		if 'hausc' in dct:
			hc = four2hex(dct['hausc'])
		else:
			hc = HAUSC
		cmd = FS20_command(hc, devadr, cmd=dct['cmd'], dur=dct['dur'])
		serdev.send_message(cmd)
		time.sleep(10)
	
	logger.info('listening to fs20')
	while True:
		msg = serdev.read(minlen=8,timeout=10,termin=bytes('\r\n','ascii'))
		if not msg:
			break
		rec = parseS300(msg)
		if rec and 'devadr' in rec:
			logger.info('tmp,hum =%s' % rec)
		else:
			logger.info('msg %s' % parseFS20(msg))
	
	serdev.exit()
else:
	logger = logging.getLogger(__name__)	# get logger from main program

