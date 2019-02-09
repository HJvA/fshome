#!/usr/bin/env python3
"""
"""
import json
import logging
import os

__author__ = "Henk Jan van Aalderen"
__credits__ = ["Henk Jan van Aalderen", "Ivan Kalchev"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Henk Jan van Aalderen"
__email__ = "hjva@homail.nl"
__status__ = "Development"

class devConfig(object):
	""" maintains/persists configuration items
		may ask user a key name for unknown/new items
	"""
	def __init__(self, fname, newItemPrompt="Please enter a name for it:"):
		''' loads item store from disk '''
		self.itstore = {}
		self.prompt=newItemPrompt
		self.fname=os.path.expanduser(fname)
		if os.path.isfile(self.fname):
			with open(self.fname, 'r') as fl:
				self.itstore = json.load(fl)
		logger.debug("loading config:%s \n" % (self.fname,))
	
	def prettyValStr(self, items=None):
		if items is None:
			items=self.itstore
		return json.dumps(items, ensure_ascii=False, indent=2, sort_keys=True)
		
	def updateConfig(self, config):
		''' updates item store with config items (kvp) '''
		for devkey,itms in config.items():
			self.updateItems(devkey, itms)
			#self.itstore.update(config)
		
	def updateItems(self, devkey, items):
		if devkey in self.itstore:
			self.itstore[devkey].update(items)
		else:
			self.itstore[devkey] = items
		
	def askNameDialog(self, signature):
		'''ask user to enter a name for an item '''
		logger.critical("*** get name for unknown item ***:\n%s" % self.prettyValStr(signature))	# both console and error.log file
		if self.prompt is None: # not asking but making best guess
			name = '_'+'_'.join(str(signature[x]) for x in sorted(signature))  # join values to string
		else:
			name = input(prompt)
		return name
		
	def checkItem(self, signature):
		'''find signature in item store returns key if found
			otherwise adds signature to item store under entered key
		'''
		#if name is None or len(name)==0:
		name=self.findKey(signature)
		if not name is None:
			return name	# known name for signature
		if name is None or len(name)==0:
			name = self.askNameDialog(signature)
		if not name is None and len(name)>0:		
			self.itstore[name] = signature	# add or update
		return name
	
	def getItem(self, iname, default=None):
		if not iname in self.itstore:
			self.itstore[iname]=default
			logger.info("adding '%s' to [%s] in config" % (default,iname))
		return self.itstore[iname]
		
	def findKey(self, partItem):
		''' find (partial) item dict in config
			returns key (name of item) when found
		'''
		#logger.debug("finding %s \nin %s" % (partItem,self.config))
		for nm,itm in self.itstore.items():
			fnd=True
			for ik,iv in partItem.items():
				fnd = fnd and ik in itm and iv==itm[ik]
			if fnd:
				return nm
		return None
			
	def save(self,fname=None):
		''' saves itemstore to disc '''
		if fname is None:
			fname=self.fname
		with open(os.path.expanduser(fname), 'w') as fl:
			json.dump(self.itstore, fl, ensure_ascii=False, indent=2, sort_keys=False)
		logger.debug("config saved to:%s" % fname)
			
	
if __name__ == "__main__":		# for testing
	logger = logging.getLogger()
	logger.addHandler(logging.StreamHandler())	# use console
	logger.setLevel(logging.DEBUG)

	try:
		cnf = devConfig("test.json")
		cnf.updateConfig({"hjva":{"name":"henkjan","age":57}})
		name=cnf.checkItem({"name":"zent","age":55})
		print("%s found in %s" % (cnf.findKey({"name":"henkjan"}),cnf.itstore))
		cnf.save()
		
	except KeyboardInterrupt:
		logger.warning("terminated by ctrl c")
	
	logger.critical('bye')
else:
	logger = logging.getLogger(__name__)	# get logger from main program
