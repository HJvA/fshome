
class Accessory:
    """A representation of a HAP accessory.

    Inherit from this class to build your own accessories.
    """

	def __init__(self, driver, display_name, aid=None):
		self.aid = aid
		self.driver = driver
		
	def add_preload_service(self, service, chars=None):
		return service
		
	@staticmethod
	def run_at_interval(seconds):
        """Decorator that runs decorated method every x seconds, until stopped.

        Can be used with normal and async methods.

        .. code-block:: python

            @Accessory.run_at_interval(3)
            def run(self):
                print("Hello again world!")

        :param seconds: The amount of seconds to wait for the event to be set.
            Determines the interval on which the decorated method will be called.
        :type seconds: float
        """

        def _repeat(func):
            async def _wrapper(self, *args):
                while True:
                    await self.driver.async_add_job(func, self, *args)
                    if await util.event_wait(self.driver.aio_stop_event, seconds):
                        break

            return _wrapper

        return _repeat
		
class Bridge(Accessory):
	
	def __init__(self, driver, display_name):
        super().__init__(driver, display_name, aid=STANDALONE_AID)
        self.accessories = {}  # aid: acc
		  
	def add_accessory(self, acc):
		self.accessories[acc.aid] = acc
		
	async def run(self):
        """Schedule tasks for each of the accessories' run method."""
        for acc in self.accessories.values():
            self.driver.async_add_job(acc.run)

    async def stop(self):
        """Calls stop() on all contained accessories."""
        await self.driver.async_add_job(super().stop)
        for acc in self.accessories.values():
			  await self.driver.async_add_job(acc.stop)

			  