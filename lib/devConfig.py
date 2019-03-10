#!/usr/bin/env python3
""" general purpose configuration settings handler
"""
import json
import logging
import os

__author__ = "Henk Jan van Aalderen"
__email__ = "hjva@notmail.nl"
__status__ = "Development"

class devConfig(object):
	""" maintains/persists configuration items
		may ask user a key name for unknown/new items
	"""
	def __init__(self, fname, newItemPrompt="Please enter a name for it:"):
		''' loads item store from disk '''
		self.itstore = {}
		self.prompt=newItemPrompt
		self.fname=fname
		fname=os.path.expanduser(fname)
		if os.path.isfile(fname):
			with open(fname, 'r') as fl:
				self.itstore = json.load(fl)
		logger.debug("loading config:%s isfile:%s len:%d\n" % (fname, os.path.isfile(fname), len(self.itstore)))
		
	def __repr__(self):
		return json.dumps((self.fname,self.itstore,), ensure_ascii=False, sort_keys=False)
		
	def __str__(self, items=None):
		''' pretty str repr '''
		if items is None:
			items=self.itstore
		return json.dumps(items, ensure_ascii=False, indent=2, sort_keys=True)
		
	def updateConfig(self, config):
		''' updates item store with config dict  '''
		logger.info("updateConfig %s with %d" % (self.fname,len(config)))
		for devkey,itms in config.items():
			self.setItem(devkey, itms)
			#self.itstore.update(config)
				
	def askNameDialog(self, signature):
		'''ask user to enter a name for an item '''
		logger.critical("*** get name for unknown item ***:\n%s" % self.__str__(signature))	# both console and error.log file
		if self.prompt is None: # not asking but making best guess
			name = '_'+'_'.join(str(signature[x]) for x in sorted(signature))  # join values to string
		else:
			name = input(self.prompt)
		return name
		
	def checkItem(self, signature):
		'''find signature in item store returns key if found
			otherwise adds signature to item store under entered key
		'''
		#if name is None or len(name)==0:
		ikey=self.findKey(signature)
		if not ikey is None:
			return ikey	# known name for signature
		if ikey is None or len(name)==0:
			ikey = self.askNameDialog(signature)
		if not ikey is None and len(ikey)>0:		
			self.itstore[ikey] = signature	# add or update
		return ikey
	
	def setItem(self, ikey, ivals):
		if ikey in self.itstore and isinstance(self.itstore[ikey], dict):
			self.itstore[ikey].update(ivals)
		else:
			self.itstore[ikey] = ivals
			
	def __setitem__(self, ikey, val):
		self.setItem(ikey, val)
	
	def getItem(self, ikey, default=None):
		if not ikey in self.itstore:
			self.itstore[ikey]=default
			logger.info("adding '%s' to [%s] in config" % (default,ikey))
		return self.itstore[ikey]
	
	def __getitem__(self, ikey):
		return self.getItem(ikey)
		
	def findKey(self, partItem):
		''' find (partial) item dict in config
			returns key (name of item) when found
		'''
		#logger.debug("finding %s \nin %s" % (partItem,self.config))
		for ikey,itm in self.itstore.items():
			fnd=True
			for ik,iv in partItem.items():
				fnd = fnd and ik in itm and iv==itm[ik]
			if fnd:
				return ikey
		return None
			
	def save(self,fname=None):
		''' saves itemstore to disc '''
		if fname is None:
			fname=self.fname
		fname = os.path.expanduser(fname)
		logger.debug("config saving to:%s" % fname)
		with open(fname, 'w') as fl:
			json.dump(self.itstore, fl, ensure_ascii=False, indent=2, sort_keys=False)

if __name__ == "__main__":		# for testing
	logger = logging.getLogger()
	[logger.removeHandler(h) for h in logger.handlers[::-1]] # handlers persist between calls
	logger.addHandler(logging.StreamHandler())	# use console
	logger.setLevel(logging.DEBUG)
	os.remove(os.path.expanduser("~/test.json"))
	
	try:
		cnf = devConfig("~/test.json")
		cnf.updateConfig({"hjva":{"name":"henkjan","age":57}})
		name=cnf.checkItem({"name":"zent","age":55})
		print("%s found in %s" % (cnf.findKey({"name":"henkjan"}),cnf.itstore))
		print(cnf)
		cnf.save()
		
	except KeyboardInterrupt:
		logger.warning("terminated by ctrl c")
	
	logger.critical('bye')
else:
	logger = logging.getLogger(__name__)	# get logger from main program
