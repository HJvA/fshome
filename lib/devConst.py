""" system constants
"""

# base id numbers for a specific device
QID={
	"fs20" : 100,
	"DSMR" : 300,
	"AIOS" : 400,
	"HUE"  : 200,
	"deCONZ" : 500,
	"WNDR" : 700,
	"SND"  : 600
}

# known device types enumeration
DEVT ={
	"temperature":0, # temperature sensor [°C]
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
	"signal":17,   # event signal
	"power":20,		# mains actual power usage [W]
	"energy":21,	# kWh
	"voltage":22,	# V
	"current":23,	# A
	"gasFlow":30,	# m3/h
	"gasVolume":31,# m3
	"ECO2":40,
	"TVOC":41,
	"DIGI":44,     # aios digital IO
	"bytesPs":50,  # bytes per sec
	"Mbytes":51,   # mega bytes 
	"duration":60,
	"julianDay":61,# days since 
	"secluded":98, # known device but to be ignored
	"unknown":99 } # unknown device
	
qCOUNTING = [10,11,12,15,44]  # quantity counting types
#colour for a quantity in graphs etc
strokes={0:"#1084e9",1:"#a430e9",5:"#90e090",10:"#c060d0",20:"#c080f0",21:"#a0d0f0", 22:"#f06040",11:"#f080d0",12:"#f0a0d0",13:"#f0c0d0",14:"#f0e0d0",15:"#d0e0d0",
   40:"#10b4fa",41:"#10f4e9",44:"#20a4e9"}

SIsymb = {  # symbols and units
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
	17:("off",""),
	20:("P","W"),
	21:("E","kWh"),
	22:("U","V"),
	23:("I","A"),
	30:("flow","m3/s"),
	31:("Vol","m3"),
	40:("Vol","%"),
	41:("Conc","ppm"),
	50:("bps","1/s"),
	51:("MB","1024"),
	60:("t","s"),
	61:("date","days")
	}
	
DVrng = {  # quantity normal range
	0:(-273,99), # temperature
	1:(0,100),   # hum
	2:(0,999),   # rain
	3:(-999,999),  # speed
	4:(-999,999), # pressure
	5:(-999,999), # illum
	6:(-999,999), # fire
	10:(-999,999),  # door bell
	11:(-999,999), # motion
	12:(-999,999),  # pressed
	13:(-999,999),   # light
	14:(-999,999),   # dimming
	15:(-999,999),  # mains
	16:(-999,999),    # switch
	17:(-999,999),
	20:(-999,999),    # power
	21:(-999,999),  # energy
	22:(-999,999),    # voltage
	23:(-999,999),    # current
	30:(-999,999),  # flow
	31:(-999,999),     # volume abs
	40:(-999,999),     # volume perc
	41:(-999,999),     # density
	50:(-999,9999999), # bps
	51:(-999,9999999), # n Mbytes
	60:(0,9e9),   # s
	61:(0,9e9)    # days
	}
