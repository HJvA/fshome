

# known device types enumeration
DEVT ={
	"temperature":0, # temperature sensor
	"humidity":1,  # humidity sensor
	"rain":2,      # precipitation meter
	"wind":3,      # wind speed meter
	"pressure":4, # incl air pressure
	"brightness":5,# brightness meter
	"pyro":6,      # pyro detector
	"fs20":9,      # unknown fs20 device
	"doorbell":10, # doorbell button
	"motion":11,   # motion detector
	"button":12,   # button stateless
	"light":13,    # lamp
	"dimmer":14,   # mains (light) dimmer
	"switch":15,   # mains remote switch
	"secluded":98, # known device but to be ignored
	"unknown":99 } # unknown device
	
qCOUNTING = [10,11,12,15]  # quantity counting types
