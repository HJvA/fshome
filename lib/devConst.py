import logging,re,time

# known device types enumeration
DEVT ={
	"temperature":0, # temperature sensor [C]
	"humidity":1,  # humidity sensor [%]
	"rain":2,      # precipitation meter
	"wind":3,      # wind speed meter
	"pressure":4,	# incl air pressure [kPa]
	"illuminance":5,# brightness meter [lux]
	"pyro":6,      # pyro detector
	"fs20":9,      # unknown fs20 device
	"doorbell":10, # doorbell button
	"motion":11,   # motion detector
	"button":12,   # button stateless [nPresses]
	"lamp":13,     # lamp
	"dimmer":14,   # mains (light) dimmer [%]
	"outlet":15,   # mains outlet 
	"switch":16,	# remote on/off switch
	"power":20,		# mains actual power usage [W]
	"energy":21,	# kWh
	"voltage":22,	# V
	"current":23,	# A
	"gasFlow":30,	# m3/h
	"gasVolume":31,# m3
	"ECO2":40,
	"TVOC":41,
	"DIGI":44,
	"secluded":98, # known device but to be ignored
	"unknown":99 } # unknown device
	
qCOUNTING = [10,11,12,15]  # quantity counting types
#colour for a quantity in graphs etc
strokes={0:"#1084e9",1:"#a430e9",5:"#90e090",10:"#c060d0",20:"#c080f0",21:"#a0d0f0", 22:"#f06040",11:"#f080d0",12:"#f0a0d0",13:"#f0c0d0",14:"#f0e0d0",15:"#d0e0d0",
   40:"#10b4fa",41:"#10f4e9",44:"#20a4e9"}

SIsymb = {
	0:("T","°C"),
	1:("Hum","%"),
	2:("Precip","mm"),
	3:("V","m/s"),
	4:("P","bar"),
	5:("E","lux"),
	6:("pyro",""),
	10:("bell",""),
	11:("motion",""),
	12:("press",""),
	13:("lmp","%"),
	14:("dim","%"),
	15:("mains",""),
	16:("on",""),
	20:("P","W"),
	21:("E","kWh"),
	22:("U","V"),
	23:("I","A"),
	30:("flow","m3/s"),
	31:("Vol","m3"),
	40:("Vol","%"),
	41:("Conc","ppm"),
	}
"""	
def get_logger(pyfile=None, levelConsole=logging.INFO, levelLogfile=logging.DEBUG):
	''' creates a logger logging to both console and to a log file but with different levels '''
	if pyfile is None:
		return logging.getLogger(__name__)	# get logger from main program
	logger = logging.getLogger()
	[logger.removeHandler(h) for h in logger.handlers[::-1]] # handlers may persist between calls
	hand=logging.StreamHandler()
	hand.setLevel(levelConsole)
	logger.addHandler(hand)	# use console
	
	reBASE=r"([^/]+)(\.\w+)$"
	base = re.search(reBASE,pyfile).group(1)
	logger.addHandler(logging.FileHandler(filename=base+'.log', mode='w', encoding='utf-8'))
	
	# always save errors to a file
	hand = logging.FileHandler(filename='error.log', mode='a')
	hand.setLevel(logging.ERROR)	# error and critical
	logger.addHandler(hand)

	logger.setLevel(levelLogfile)
	logger.critical("### running %s dd %s ###" % (pyfile,time.strftime("%y%m%d %H:%M:%S")))
	return logger
"""