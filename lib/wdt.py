#
# https://superfastpython.com/watchdog-thread-in-python/
# https://stackoverflow.com/questions/16148735/how-to-implement-a-watchdog-timer-in-python
# https://copyprogramming.com/howto/python-timer-with-asyncio-coroutine?utm_content=cmp-true
from threading import Timer,Lock,Thread
import asyncio
import signal
from datetime import datetime,timedelta
from contextlib import contextmanager
import inspect


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
		self._start = datetime.now()
		self.process = process
		self.signal = TimeoutSignaller(seconds, self.signal_handler)

	def __enter__(self):
		logger.info("starting process:{} dt:{}".format(self.process, datetime.now()-self._start))
		self.signal.start()
		return self.process

	def __exit__(self, exc_type, exc_val, exc_tb):
		logger.info("exit process:{} dt:{}".format(self.process, datetime.now()-self._start))
		self.signal.stop_run()

	def signal_handler(self):
		# Make process terminate however you like
		# using self.process reference
		if asyncio.iscoroutine(self.process):
			self.process.cancel("timeout occurred")
		else:  #inspect.isawaitable():
			logger.error("timeout for process")
			self.process.cancel("timeout occurred dt:{}".format(datetime.now()-self._start))
			raise TimeoutError("Process took too long to execute")

class asyWatch:
	def __init__(self, worker, timeout, loop=None):
		self._timeout = timeout
		self._loop = loop
		#self._tmo = asyncio.timeout(timeout)
		logger.info("asyWatch set tmo:{}".format(timeout))
		#
		if inspect.isawaitable(worker):
			logger.debug("job is awaitable")
			self._job = asyncio.create_task(worker())# worker
		elif asyncio.iscoroutine(worker):
			logger.debug("job is coro")
			self._job = worker
		else:
			logger.debug("job is callable")
			self._job = asyncio.coroutine(worker)
			#self._job = asyncio.create_task(worker())  
		
	def __enter__(self):
		self._start = datetime.now()
		logger.info("start:{}".format(self._start))
		#self.timer = self._loop.call_later(self._timeout, lambda: asyncio.ensure_future(self._job()))
		self._wtm = asynio.timeout(self.timeout)
		async with self._wtm:
			await self._job()

	def __exit__(self, exc_type, exc_val, exc_tb):
		logger.info("exit asy:{} dt:{}".format(exc_type, datetime.now()-self._start))

	def alive(self):
		nwto = self._loop.time() + self._timeout
		logger.info("reschedule".format(nwto))
		self._wtm.reschedule(nwto)
		#self.timer.cancel() # cancels the timer, but not the job, if it's already started
		#self.__enter__()
				
		
if __name__ == '__main__':	# just testing  
	import time,random,logging,os
	import submod.pyCommon.tls as tls
	logger = tls.get_logger(__file__, levelConsole=logging.INFO, levelLogfile=logging.DEBUG)
	def myHandler():
		logger.info("Watchdog expired")

	async def myworker():
		key = None
		logger.info("working.. press ESC to stop")
		with tls.clavier(-1 if os.getgid()<100 else None) as kb:
			while True:
				if kb.kbhit():
					key = kb.getch()
					if ord(key)==27:  # Ctrl-[
						break
					print("key hit: key={}".format(key))
				await asyncio.sleep(1.6+random.random())
			print("all done")
		
	async def runtask(worker=myworker, timeout=2):
		mytask = asyncio.create_task(worker())
		logger.info("running task:{}".format(mytask))
		with ProcessContextManager(mytask, timeout) as aqc:
			try:
				await mytask
			except asyncio.exceptions.CancelledError as ex:
				print("timeout->canceled")	
	
	async def myWork(lock, id, timeout=2):
		now = datetime.now()
		await asyncio.sleep(0.01)  # have other task also started
		try:
			await asyncio.wait_for(lock.acquire(), timeout)
		except asyncio.TimeoutError:
			dt = datetime.now()-now
			dt = dt.total_seconds()
			logger.warning(f"I'm {id} timedout to lock after {dt}")
		else:
			dt = datetime.now()-now
			dt = dt.total_seconds()
			logger.info(f"I'm {id} and started working after {dt}")
			await asyncio.sleep(0.6+random.random())
			dt = datetime.now()-now
			dt = dt.total_seconds()
			logger.info(f"I'm {id} and I'm working for {dt}")
			if lock.locked():
				lock.release()
				logger.info("releasing lock for {}".format(id))
		#logger.info("myWork{} started {}".format(id, now))
		#async with lock as acq:
			#await asyncio.sleep(1.01+random.random())
			#logger.info("myWork{} done {} lck:{}".format(id, datetime.now()-now, acq))

	async def doWork(mxtime = 2):
		lock = asyncio.Lock()  # tmoLock(timeout=mxtime)
		await asyncio.gather(*[myWork(lock,1,mxtime), myWork(lock,2,mxtime), myWork(lock,3,mxtime)])
	
	_loop = asyncio.get_event_loop()
	logger.info("\n asyWatch")
	strt = datetime.now()
	asyw = asyWatch(myworker, 2, _loop)
	with asyw:
		time.sleep(2.4+random.random())
		dt = datetime.now()-strt
		logger.info("worked dt:{}".format( dt.total_seconds()))
	

	for i in range(4):
		asyncio.run(runtask())
	
	logger.info("\n asyncio locking parralel tasks")
	for i in range(4):
		_loop.run_until_complete(doWork())

	logger.info("\n watchdog")
	for i in range(4):
		try:
			strt = datetime.now()
			wd = watchdog(2, myHandler)
			with wd:
				time.sleep(1.4+random.random())
				dt = datetime.now()-strt
				logger.info("worked {} dt:{}".format(i, dt.total_seconds()))
		except watchdog as ex:
			logger.info("watchdog runout {} {} after {}".format(i, ex, datetime.now()-strt))

	logger.info("\n windows watchdog")	
	wdt = wWatchdog(2, myHandler)
	try: # do something that might take too long
		for i in range(4):
			time.sleep(1.3+random.random())
			wdt.reset()
			logger.info("tWork done {}".format(datetime.now()))
	except wWatchdog:	# handle watchdog error
		wdt.stop()
		
