

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
	"secluded":98, # known device but to be ignored
	"unknown":99 } # unknown device
	
qCOUNTING = [10,11,12,15]  # quantity counting types
#colour for a quantity in graphs etc
strokes={0:"#1084e9",1:"#a430e9",5:"#90e090",10:"#c060d0",20:"#c040f0",21:"#f040d0", 22:"#f060d0",11:"#f060d0",12:"#f060d0",13:"#f060d0",14:"#f060d0",15:"#f060d0"}

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
	21:("E","J"),
	22:("U","V"),
	23:("I","A"),
	30:("flow","m3/s"),
	31:("Vol","m3")
	}