""" some   Accessories
	defines  
	"""
import time
import logging

if __name__ == "__main__":
	import sys,os,signal
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))
else:
	logger = logging.getLogger(__name__)	# get logger from main program

from lib.devConst import DEVT
from lib.serComm import serComm,DEVICE,forever

class serDevice(object):
	commPort=None
	quantities=None
	def __init__(self, ComPort=DEVICE, quantityConf=None):
		if serDevice.commPort is None:
			serDevice.commPort = serComm(ComPort)
		if quantityConf:
			serDevice.quantities=quantityConf
			
	def exit(self):
		serDevice.commPort.exit()
		
	def parse_message(self,data):
		''' virtual : to be enhanced to convert string to dict of items'''
		return {"msg":data.strip(' \r\n'),"len":len(data)}
		
	async def receive_message(self, timeout=2, minlen=8, termin='\r\n', signkeys=('typ','devadr')):
		'''receive dict of items from a (any) device
			recognises device from signkeys in parsed/received items
			tries to add unknown devices to config'''
		msg = await serDevice.commPort.asyRead(timeout, minlen, bytes(termin,'ascii'))
		if msg is None or len(msg)==0:
			#logger.debug("nothing received this time %s" % time.time())
			rec={}
		else:
			rec = self.parse_message(msg)
		return rec
		
			signature={}
			if self.quantities:
				for devk in signkeys:  # build device signature from message
					if devk in rec:
						if devk!='typ' or rec[devk]!=DEVT['fs20']: # don't have typ in signature if no sens
							signature[devk]=rec[devk]  # add this key to the signature
			if len(signature)>0:
				devkey = serDevice.quantities.checkItem(signature) # lookup dev by signature and store it if not there
				if devkey is None or len(devkey)==0:
					logger.error("no name in config for %s with msg:%s" % (signature,msg))
				else:
					#if devkey[0]=='_' or len(signature) < len(signkeys):
					if 'typ' in rec:
						typ =rec['typ']
					else:
						typ = None
					if typ==DEVT['fs20']:
						typ = serDevice.quantities[devkey]['typ']  #serDevice.getConfigItem(devkey,'typ')
						if not typ is None:
							rec.update(typ=typ)
					if typ is None:
						logger.error("receiving unknown device(%s) dd:%s msg:%s having:%s %d<%d" % (devkey,time.strftime("%y%m%d %H:%M:%S"), msg,rec,len(signature),len(signkeys)))
					if typ==DEVT['secluded']:
						logger.info("%s ignored" % rec)
					else:
						rec.update({'new':1,'name':devkey})
						newdev = not devkey in serDevice.devdat
						serDevice.devdat[devkey] = rec
					if newdev:
						logger.warning("new device received:%s with:%s now having:%s" % (devkey,signature, serDevice.devdat.keys()))
			else:
				logger.error("unknown device:%s config:%s" % (msg,serDevice.quantities))
			logger.debug("rec:%s" % rec)
		return rec
		
	def send_message(self, msg, termin='\r\n'):
		""" sends a terminated string to the device """
		data = bytes(msg+termin, 'ascii')
		logger.debug("cmd:%s" % data)
		serDevice.commPort.write(data)

