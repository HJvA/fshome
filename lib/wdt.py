#
# https://superfastpython.com/watchdog-thread-in-python/
# https://stackoverflow.com/questions/16148735/how-to-implement-a-watchdog-timer-in-python
from threading import Timer,Lock,Thread
import asyncio
import signal
from datetime import datetime,timedelta
from contextlib import contextmanager


class TimeoutLock(object):
	""" lock with timeout """
	def __init__(self):
		self._lock = Lock()

	def acquire(self, blocking=True, timeout=-1):
		return self._lock.acquire(blocking, timeout)

	@contextmanager
	def acquire_timeout(self, timeout):
		result = self._lock.acquire(timeout=timeout)
		yield result
		if result:
			self._lock.release()

	def release(self):
		self._lock.release()

class thrdLock():
	def __init__(self, blocking=True, timeout=-1):
		self.blocking=blocking
		self.timeout=timeout
		self._lock = Lock()
	def __enter__(self):
		return self._lock
		if self.blocking:
			self.acquired = self._lock.acquire(self.blocking, self.timeout)
		else:
			self.acquired = self._lock.acquire()
		yield self.acquired
		return self.acquired
	def __exit__(self, exc_type, exc_value, exc_traceback):
		if self.acquired:
			self._lock.release()
		else:
			logger.warning("lock not aquired")

class wWatchdog(Exception):
	def __init__(self, timeout, userHandler=None):  # timeout in seconds
		self.timeout = timeout
		self.handler = userHandler if userHandler is not None else self.defaultHandler
		self.timer = Timer(self.timeout, self.handler)
		self.timer.start()
	
	def __enter__(self):
		self.timer = Timer(self.timeout, self.handler)
		self.timer.start()
		return self.timer
	
	def __exit__(self):
		self.timer.cancel()

	def reset(self):
		""" starting new Timer """
		self.timer.cancel()
		self.timer = Timer(self.timeout, self.handler)
		self.timer.start()

	def stop(self):
		self.timer.cancel()

	def defaultHandler(self):
		raise self


class watchdog(Exception):
	""" only for Unix """
	def __init__(self, timeout=-1, handler=None):
		self._timo = timeout
		self._handler = self.handler if handler is None else self.handler
	def __enter__(self):
		signal.signal(signal.SIGALRM, self._handler)
		signal.alarm(self._timo)
	def __exit__(self, type, value, traceback):
		signal.alarm(0)
	def handler(self, signum, frame):
		logger.debug("watchdog expired ({} {})".format(signum,frame))
		raise self
	def __str__(self):
		return "The code you executed took more than %ds to complete" % self._timo

# https://stackoverflow.com/questions/15018519/python-timeout-context-manager-with-threads
class TimeoutSignaller(Thread):
	def __init__(self, limit, handler):
		Thread.__init__(self)
		self.limit = limit
		self.running = True
		self.handler = handler
		assert callable(handler), "Timeout Handler needs to be a method"

	def run(self):
		timeout_limit = datetime.now() + timedelta(seconds=self.limit)
		while self.running:
			if datetime.now() >= timeout_limit:
				self.handler()
				self.stop_run()
				break

	def stop_run(self):
		self.running = False

class ProcessContextManager:
	"""
	with ProcessContextManager(myproc, seconds=3) as p:
		p.execute()
	"""
	def __init__(self, process, seconds=3):
		#self.seconds = seconds
		self.process = process
		self.signal = TimeoutSignaller(seconds, self.signal_handler)

	def __enter__(self):
		self.signal.start()
		return self.process

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.signal.stop_run()

	def signal_handler(self):
		# Make process terminate however you like
		# using self.process reference
		if True: #self.process is asyncio.Task:
			self.process.cancel("timeout occurred")
		else:
			raise TimeoutError("Process took too long to execute")

			

if __name__ == '__main__':	# just testing  
	import tls,time,random,logging
	logger = tls.get_logger(__file__, levelConsole=logging.INFO, levelLogfile=logging.DEBUG)
	def myHandler():
		logger.info("Watchdog expired")

	async def myworker():
		for i in range(10):
			print("working:{}".format(i))
			await asyncio.sleep(2)
		print("all done")
		
	async def runtask(worker=myworker, timeout=4):
		mytask = asyncio.create_task(worker())
		with ProcessContextManager(mytask, timeout) as aqc:
			try:
				await mytask
			except asyncio.exceptions.CancelledError as ex:
				print("timeout->canceled")	
	
	async def myWork(lock, id):
		now = datetime.now()
		logger.info("myWork{} started {}".format(id, now))
		await asyncio.sleep(0.01)  # have other task also started
		async with lock as acq:
			await asyncio.sleep(1.01+random.random())
			logger.info("myWork{} done {}".format(id, datetime.now()-now))

	async def doWork(mxtime = 3.8):
		lock = asyncio.Lock()  # tmoLock(timeout=mxtime)
		await asyncio.gather(*[myWork(lock,1), myWork(lock,2), myWork(lock,3)])
	
	_loop = asyncio.get_event_loop()
	asyncio.run(runtask())
	
	for i in range(6):
		_loop.run_until_complete(doWork())

	for i in range(6):
		try:
			strt = datetime.now()
			with watchdog(2, myHandler):
				time.sleep(1.3+random.random())
				logger.info("working {}".format( datetime.now()-strt))
		except watchdog as ex:
			logger.info("watchdog runout {} after {}".format(ex, datetime.now()-strt))

	wdt = wWatchdog(2, myHandler)
	try: # do something that might take too long
		for i in range(6):
			time.sleep(1.3+random.random())
			wdt.reset()
			logger.info("tWork done {}".format(datetime.now()))
	except wWatchdog:	# handle watchdog error
		wdt.stop()
		
