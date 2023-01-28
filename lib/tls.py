""" small general purpose helpers """

import datetime
import time
import logging
import os,re,sys
import threading
import hashlib, hmac
from pathlib import Path
from enum import Enum
if os.name=='nt':
	import msvcrt
else:
	import termios,select  # atexit

def bytes_to_int(data, endian='>', signed=True):
	"""Convert a bytearray into an integer, considering the first bit sign."""
	if endian=='<':
		data=bytearray(data)
		data.reverse()
	negative = signed and (data[0] & 0x80 > 0)
	if negative:
		inverted = bytearray(~d % 256 for d in data)
		return -bytes_to_int(inverted) - 1
	encoded = ''.join(format(x, '02x') for x in data) 
	return int(encoded, 16)

def bytes_to_hex(data, separ='', frmt='02x'):
	return separ.join(format(x, frmt) for x in data)

def load_lod(lod, csv_fp, fields=['id','name']):
	''' get list of dict from csv file
	'''
	rdr = csv.DictReader(csv_fp, fields)
	lod.extend(rdr)

def query_lod(lod, filter=None, sort_keys=None):
	''' get list of dict filtered from lod
	pprint(query_lod(lod, sort_keys=('Priority', 'Year')))
	print len(query_lod(lod, lambda r:1997 <= int(r['Year']) <= 2002))
	print len(query_lod(lod, lambda r:int(r['Year'])==1998 and int(r['Priority']) > 2))
	'''
	if filter is not None:
		lod = (r for r in lod if filter(r))
	if sort_keys is not None:
		lod = sorted(lod, key=lambda r: [r[k] for k in sort_keys])
	else:
		lod = list(lod)
	return lod

def lookup_lod(lod, **kw):
	''' get first dict from lod with key value
	pprint(lookup_lod(lod, Row=1))
	pprint(lookup_lod(lod, Name='Aardvark'))
	'''
	i=0
	for row in lod:
		for k,v in kw.items():
			if row[k] != v:   
				i += 1
				break #next row
		else:
			return row,i
	return None,-1

class clavier():
	""" 
	 https://simondlevy.academic.wlu.edu/files/software/kbhit.py 
	 https://stackoverflow.com/questions/13207678/whats-the-simplest-way-of-detecting-keyboard-input-in-a-script-from-the-termina/47197390#47197390 
	"""
	def __init__(self, fd=None):
		""" fs==0 : disabled """
		if fd is not None and fd<0:
			self.fd=None
		else:
			self.fd = sys.stdin.fileno()
		#logger.debug("new clavier, tty:{} ".format( os.isatty(self.fd) ))
	def __enter__(self):
		"""
		new_settings = termios.tcgetattr(sys.stdin)
		new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON) # lflags
		new_settings[6][termios.VMIN] = 0  # cc
		new_settings[6][termios.VTIME] = 0 # cc
		termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new_settings)
		"""
		if os.isatty(self.fd):
			#tty.setcbreak(self.fd)
			new_term = termios.tcgetattr(self.fd)
			self.old_term = termios.tcgetattr(self.fd)
			new_term[3] = (new_term[3] & ~termios.ICANON & ~termios.ECHO)
			termios.tcsetattr(self.fd, termios.TCSAFLUSH, new_term)
		return self
	def __exit__(self, exc_type, exc_value, traceback):
		#logger.debug("kbexit")
		if os.name == 'nt':
			pass
		elif os.isatty(self.fd):
			termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.old_term)
	def __repr__(self):
		return "clavier on:{} with fd:{}".format(os.name, self.fd)
	def kbhit(self):
		''' Returns True if keyboard character was hit, False otherwise.
		'''
		if os.name == 'nt':
			return msvcrt.kbhit()
		elif os.isatty(self.fd):
			dr,dw,de = select.select([sys.stdin], [], [], 0)
			return dr != []
		else:
			return False

	def getch(self):
		''' Returns a keyboard character after kbhit() has been called. Should not be called in the same program as getarrow().
		'''
		if os.name == 'nt':
			return msvcrt.getch().decode('utf-8')
		elif os.isatty(self.fd):
			return sys.stdin.read(1)
		return ""
	def getarrow(self):
		''' Returns an arrow-key code after kbhit() has been called. Codes are
        0 : up
        1 : right
        2 : down
        3 : left
        Should not be called in the same program as getch().
		'''
		if os.name == 'nt':
			msvcrt.getch() # skip 0xE0
			c = msvcrt.getch()
			vals = [72, 77, 80, 75]
		elif os.isatty(self.fd):
			c = sys.stdin.read(3)[2]
			vals = [65, 67, 66, 68]
		return vals.index(ord(c.decode('utf-8')))
	"""
	def getkey(self, timeout=1):
		self.resp=None
		p = multiprocessing.Process(target=self.waitkey)
		p.start()
		p.join(timeout)
		if p.is_alive():
			p.terminate()
			p.join()
			logger.debug("no keys")
		return self.resp
	def waitkey(self):
		buf=[]
		#if select.select([sys.stdin, ], [], [], 0.0)[0]:
		#b = os.read(self.fd, 1) #.decode()  # keyboard.read_key()
		if self.isData():
			b = sys.stdin.read(1)
			while b and len(b)>0:
				buf.append(b[0])
				#b = os.read(self.fd, 1)
				#b = sys.stdin.read(1)
				b = None
		if len(buf)>0:
			if len(buf) == 3:
				logger.debug("kb3:{}".format(buf))
				self.resp= ord(buf[2])
			elif len(buf)>0:
				logger.debug("kbn:{}".format(buf))
				self.resp= ord(buf[0])
		return self.resp
	"""	

class RepeatTimer(object):
	''' runs a function in backgroud at specified interval '''
	def __init__(self, interval, function, *args, **kwargs):
		logging.info('setting up interval timer to run %s every %f seconds' % (function,interval))
		self._timer     = None
		self.interval   = interval
		self.function   = function
		self.args       = args
		self.kwargs     = kwargs
		self.is_running = False
		self.start()

	def _run(self):
		''' calling this at each interval '''
		self.is_running = False
		self.start()
		self.function(*self.args, **self.kwargs)

	def start(self):
		if not self.is_running:
			self._timer = threading.Timer(self.interval, self._run)
			self._timer.start()
			self.is_running = True

	def stop(self):
		self._timer.cancel()
		self._timer.join() # hold main tread till realy finished
		self.is_running = False	

class logFormatter(logging.Formatter):
	""" https://en.m.wikipedia.org/wiki/ANSI_escape_code 
	"""
	etyp = Enum('etyp', 'ANSI MARKDOWN EMOJI')
	#Colors = Enum('Colors', 'BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE')
	BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = [x+30 for x in range(8)]
	RESET, BOLD, UNDERL,BLINK, INVERS,CONCEALED = (0,1,4,5,7,8)
	def __init__(self, formatType=etyp.ANSI):
		self.frmtyp = formatType
	def fmt(self, clr=RED, stl=BOLD, on=True):
		if on:
			return "\033[{};{}m".format(stl,clr)
		return "\033[{};{}m".format(stl+20, WHITE)
	
	EMOJI = {  #  https://github.com/ikatyang/emoji-cheat-sheet
		logging.WARNING: '⚠️',
		logging.INFO:'💡', # ℹ️
		logging.DEBUG:'🔅', #  '✳️',
		logging.CRITICAL:'❌',
		logging.ERROR:'‼️'
	}
	MRKDWN = {
		logging.WARNING: '<span style="color:yellow">',
		logging.INFO: '<span style="color:pink">',
		logging.DEBUG: '<span style="color:blue">',
		logging.CRITICAL: '<span style="color:red">',
		logging.ERROR: '<span style="color:orange">'
		}
	
	#levelname_color = COLOR_SEQ % (30 + COLORS[levelname]) + levelname + RESET_SEQ
	#record.levelname = levelname_color
	

	def format(self, record):
		#_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
		_format = " %(message)s "
		if record.levelno>=logging.WARNING:
			_format += " [%(filename)s:%(lineno)d]"
			if record.levelno>=logging.ERROR:
				_format = "%(asctime)s" + _format
				if record.levelno==logging.ERROR:
					_format += " %(stack_info)s "
		tim_fmt ="%d %H:%M:%S"
		if self.frmtyp == logFormatter.etyp.ANSI:
			grey = "\x1b[38;20m"
			yellow = "\x1b[33;20m"
			red = "\x1b[31;20m"
			bold_red = "\x1b[31;1m"
			reset = "\x1b[0m"
			FORMATS = {
				logging.DEBUG: grey + _format + reset,
				logging.INFO: grey + _format + reset,
				logging.WARNING: yellow + _format + reset,
				logging.ERROR: red + _format + reset,
				logging.CRITICAL: bold_red + _format + reset
				}
			log_fmt = FORMATS.get(record.levelno)
		elif self.frmtyp == logFormatter.etyp.EMOJI:
			log_fmt =  logFormatter.EMOJI.get(record.levelno) + _format
			#time.strftime("%d %H:%M:%S", datetime.fromtimestamp(record.created))
		elif self.frmtyp == logFormatter.etyp.MARKDOWN:
			_reset = "</span>"
			log_fmt = logFormatter.MRKDWN.get(record.levelno)+_format+_reset+"  "
		formatter = logging.Formatter(log_fmt, tim_fmt)
		return formatter.format(record)

def set_logger(logger, pyfile=None, levelConsole=logging.INFO, levelLogfile=logging.DEBUG, destDir='~/log/'):
	""" reset logger to desired config having several handlers :
	Console; logFile; errorLogFile"""
	[logger.removeHandler(h) for h in logger.handlers[::-1]] # handlers may persist between calls
	hand=logging.StreamHandler()
	hand.setLevel(levelConsole)
	hand.setFormatter(logFormatter(logFormatter.etyp.ANSI))
	logger.addHandler(hand)	# use console
	if destDir:
		destDir = os.path.expanduser(destDir)
		if not os.path.isdir(destDir):
			Path(destDir).mkdir(parents=False, exist_ok=False)
	# always save errors to a file
	hand = logging.FileHandler(filename=destDir+'error_fsHome.md', mode='a')
	hand.setLevel(logging.ERROR)	# error and critical
	hand.setFormatter(logFormatter(logFormatter.etyp.MARKDOWN))
	logger.addHandler(hand)
	
	reBASE=r"([^/]+)(\.\w+)$"
	base = re.search(reBASE,pyfile)
	if base:
		base=base.group(1)
	else:
		base=__name__
	hand = logging.FileHandler(filename=destDir+base+'.log', mode='w', encoding='utf-8')
	hand.setFormatter(logFormatter(logFormatter.etyp.EMOJI))
	logger.addHandler(hand)
	logger.setLevel(levelLogfile)
	if pyfile == "__main__":
		logger.critical("### running %s dd %s logging to %s ###" % (__name__,time.strftime("%y%m%d %H:%M:%S"),destDir+base+'.log'))
	return logger

def get_logger(pyfile=None, levelConsole=logging.INFO, levelLogfile=logging.DEBUG):
	''' creates a logger logging to both console and to a log file but with different levels
		pyfile=None   : called by package as sub module : logger from __main__ to be used
		pyfile=__file__ : called by main or testing module : create new logger
	  '''
	root = sys.modules['__main__'].__file__
	if pyfile is None or pyfile!=root:
		return logging.getLogger(__name__)	# get logger from main program
	logger = logging.getLogger()
	logger = set_logger(logger, pyfile, levelConsole, levelLogfile)
	logger.critical("starting %s dd %s" % (root, time.strftime("%d %H:%M:%S", time.localtime())))
	return logger

def hash_new_password(password: str, salt = None): # -> Tuple[bytes, bytes]:
	"""
    Hash the provided password with a randomly-generated salt and return the
    salt and hash to store in the database.
	"""
	if not salt:
		salt = os.urandom(16)
	pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
	return salt, pw_hash

def is_correct_password(salt: bytes, pw_hash: bytes, password: str): # -> bool:
	"""
    Given a previously-stored salt and hash, and a password provided by a user
    trying to log in, check whether the password is correct.
	"""
	return hmac.compare_digest(
		pw_hash, hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
	)
	
if __name__ == "__main__":
	#set_logger(level=logging.INFO)
	#logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
	logger = get_logger(__file__, logging.DEBUG)
	print('hand %d lev %s' % (len(logger.handlers), logger.handlers[0].flush()))
	#logger.handlers[0].setLevel(logging.DEBUG)
	#logger.setLevel(logging.DEBUG)
	logger.info('hallo wereld')
	logger.debug('debugging')
	logger.warning(os.getcwd())
	logger.error(os.getlogin())
	
	#while True:
	#with keybHit() as kb:
	with clavier(-1 if os.getgid()<100 else None) as kb:
		while True:
			if kb.kbhit():
				key = kb.getch()
				logger.info("key:{} ord:{}".format(key, ord(key)))
				if ord(key)==27:  #  C-[
					break
			else:
				time.sleep(0.4)
	print('(0xff,0xff,0x7f) bytes_to_int = %0x' % bytes_to_int((0xff,0xff,0xfe),'<'))
	logging.shutdown()
