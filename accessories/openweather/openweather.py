
import aiohttp,asyncio
import datetime,time
import logging
import json

if __name__ == "__main__":
	import sys,os
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))

from lib.devConfig import devConfig
#from lib.dbLogger import sqlLogger,julianday,unixsecond,prettydate,SiNumForm
#from lib.devConst import DEVT,qCOUNTING,strokes,SIsymb
import lib.tls as tls # get_logger
from lib.grtls import julianday

__copyright__="<p>Copyright &copy; 2019,2021, hjva</p>"
TITLE=r"fshome weather fetcher"
CONFFILE = "./config/openweather.json"

url_timezone = 'http://worldtimeapi.org/api/timezone/{area}/{location}'   #[/:region]'
url_city = 'https://api.openweathermap.org/data/2.5/{collect}?id={cityId}&appid={APIkey}'
url_coord  = 'https://api.openweathermap.org/data/2.5/{collect}?lat={lat}&lon={lon}&appid={APIkey}'
url_airquality = 'http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API key}'

#APIkey = 'inscribe at https://openweathermap.org'
veldhoven = 2745706
pezenas = 6432584

async def restGet(url, params={}, timeout=2):
	""" queries json device with restfull api over ethernet """
	headers = {'content-type': 'application/json'}
	stuff={}
	try:
		async with aiohttp.ClientSession() as session:
			async with session.get( url=url, timeout=timeout, params=params) as response:
				logger.info('{%d}getting=%s' % (response.status,response.url))
				if response.status==200:
					try:
						stuff = await response.json()
						#logger.debug('got:%s:%s' % (cityId,stuff))
					except aiohttp.client_exceptions.ContentTypeError as ex:
						stuff = await response.text()
						logger.warning('bad json:%s' % (stuff,))
						stuff=None
				else:
					logger.warning('bad response :%s on %s' % (response.status,url))
					await session.close()
					await asyncio.sleep(0.2)
	except asyncio.TimeoutError as te:
		logger.warning("openweather timeouterror %s :on:%s" % (te,url))
		await asyncio.sleep(10)
	except Exception as e:
		logger.exception("openweather unknown exception!!! %s :on:%s" % (e,url))
	#logger.debug('hueGET resource:%s with %s ret:%d' % (resource,r.url,r.status_code))
	return stuff

async def getIcon(weathercode):
	url = 'http://openweathermap.org/img/wn/{}@2x.png'.format(weathercode)
	stuff = None
	async with aiohttp.ClientSession() as session:
		async with session.get( url=url ) as response:
			logger.info('{%d}getting=%s' % (response.status,response.url))
			if response.status==200:
				try:
					stuff = await response.read()
					logger.debug('icon:%s:%s' % (weathercode,stuff))
				except aiohttp.client_exceptions.ContentTypeError as ex:
					stuff = await response.text()
					logger.warning('bad icon:%s:%s' % (weathercode,stuff))
					stuff=None
	return stuff
	
async def get_timezone(area='Europe', location='Paris'):
	TZF ="%Y-%m-%dT%H:%M:%S.%f%z"
	url = url_timezone.format(area=area, location=location)
	tz = await restGet(url, timeout=20)
	if not tz:
		url = 'http://worldtimeapi.org/api/ip'   #timezone/{area}/{location}'   #[/:region]'
		tz = await restGet(url, timeout=10)
	if tz:
		dt = tz['datetime']
	else:
		dt = datetime.datetime.now().isoformat()+"+02:00"
	dto = datetime.datetime.strptime(dt, TZF)  # '2021-06-19T18:09:14.896810+00:00'
	tzo = dto.tzinfo  #datetime.datetime.strptime(dt['utc_offset'],"%z")   # 
	logger.info('dto:{} tz:{}'.format(dto,tzo))
	#tz = await restGet(url)
	#logger.info('tz:{}'.format(tz))
	return tz

class openweather(object):
	def __init__(self, APIkey, cityId=None,lat=None,lon=None, tRefreshMinutes=240):
		""" query openweather for weather data for a specific location """
		self.appkey=APIkey
		if cityId:
			self.lat=None
			self.lon=None
			self.cityid=cityId
			#self.current()  # get lat lon
		elif lat and lon:
			self.lat=lat
			self.lon=lon
		self.weathercode=None
		self.data = {}
		self.tRefresh = 60 * tRefreshMinutes  # to seconds
		self.tMark = datetime.datetime.now() 
		logger.info('openweather:{}'.format(self))
	
	def _url(self, item):
		if self.lat and self.lon:
			return url_coord.format(collect=item, lat=self.lat,lon=self.lon,APIkey=self.appkey)
		elif self.cityid:
			return url_city.format(collect=item, cityId=self.cityid,APIkey=self.appkey)
	
	async def _collect(self, item, params={}, take=False):
		take = take or (item not in self.data) or (datetime.datetime.now() - self.tMark).total_seconds() > self.tRefresh
		if take:
			self.data[item] = await restGet(self._url(item), params=params, timeout=10) 
			self.tMark = datetime.datetime.now()
			logger.debug('%s collected %s openweather:%s ' % (self.tMark,item,self.data[item]))
		else:
			self.data[item]['old']=True
			logger.debug('returning ancient WeaMap data')
		return self.data[item]
	
	async def getCurrent(self, item='weather'):
		""" fetch lat,lon of cityid required for onecall """
		stuff = await self._collect(item=item) 
		self.lat = stuff['coord']['lat']
		self.lon = stuff['coord']['lon']
		self.weathercode = stuff['weather'][0]['id']
		self.weatherdescr =stuff['weather'][0]['description']
		logger.info('got lat:{}, lon:{} with {}'.format(self.lat,self.lon,item))
		return stuff
		
	async def getAirQuality(self):
		if not (self.lat) or not (self.lon):
			await self.getCurrent() # get lat lon from cityid
		stuff = await self._collect(item='air_pollution')
		if isinstance(stuff,dict):
			dt = stuff['list'][0]['dt']
			aqi = stuff['list'][0]['main']['aqi']  # 1 = Good, 2 = Fair, 3 = Moderate, 4 = Poor, 5 = Very Poor.
			airq = stuff['list'][0]['components']
			airq['dt'] = dt
			#airq['jd'] = julianday(dt)
			airq['aqi'] = aqi  # air quality index
			airq['wci'] = self.weathercode
			logger.debug('air quality ={}=>\n{}'.format(aqi,airq))
			return airq
		
	async def getRainForecast(self):
		forec = await self._collect('forecast')
		if 'list' in forec:
			xdat = [julianday(rec['dt']) for rec in forec['list'] if 'rain' in rec]
			ydat = [rec['rain']['3h'] for rec in forec['list'] if 'rain' in rec]
			#rain  ={rec['dt']:rec['rain']['3h'] for rec in forec['list'] if 'rain' in rec}
			return xdat,ydat
		
	async def getMainForecast(self, item='pressure'):
		""" item = temp | feels_like | temp_min | temp_max | pressure | sea_level | grnd_level | humidity | temp_kf """
		forec = await self._collect('forecast')
		if 'list' in forec:
			xdat = [julianday(rec['dt']) for rec in forec['list']]
			ydat = [rec['main'][item] for rec in forec['list']]
			#logger.info('got %d pressure dd from %s to %s' % (len(pressure),next(iter(pressure)),list(pressure.keys())[-1]))
			logger.info('got %d %s dd from %s to %s' % (len(xdat),item,xdat[0],xdat[-1]))
			return xdat,ydat
		else:
			logger.warning('no forecast from openweather')
			return [],[]

	async def getCoudsForecast(self, item='all'):
		forec = await self._collect('forecast')
		if 'list' in forec:
			xdat = [julianday(rec['dt']) for rec in forec['list']]
			ydat = [rec['clouds'][item] for rec in forec['list']]
			logger.info('got %d %s dd from %s to %s' % (len(xdat),item,xdat[0],xdat[-1]))
			return xdat,ydat
		else:
			logger.warning('no forecast from openweather')
			return [],[]
			
	async def getWeatherForecast(self, item='id', cnt=5):
		""" item = id | main | descrption | icon """
		forec = await self._collect('forecast', {'cnt':cnt})
		if 'list' in forec:
			xdat = [julianday(rec['dt']) for rec in forec['list']]
			logger.debug('weather lst:{}'.format(forec['list']))
			ydat = [rec['weather'][0][item] for rec in forec['list']]
			logger.info('got %d %s dd from %s to %s' % (len(xdat),item,xdat[0],xdat[-1]))
			return xdat,ydat
		else:
			logger.warning('no forecast from openweather')
			return [],[]
			
	async def getHistory(self, qname='pressure', ndays=1):
		""" https://api.openweathermap.org/data/2.5/onecall/timemachine?lat={lat}&lon={lon}&dt={time}&appid={API key} """
		utcnow=datetime.datetime.utcnow()
		tdiff = datetime.timedelta(days=ndays-1)
		logger.info('getting history from:%s diff:%s = %s' % (utcnow.timestamp(), tdiff, tdiff.total_seconds()))
		xdat=[] 
		ydat=[]
		while tdiff >= datetime.timedelta(days=0):
			utcfrom = utcnow - tdiff
			tdiff -= datetime.timedelta(days=1)
			hist = await self._collect('onecall/timemachine',{'dt':int(utcfrom.timestamp())},take=True)
			if 'hourly' in hist:
				hourly = hist['hourly']
				xdat.extend([julianday(rec['dt']) for rec in hourly])
				ydat.extend([rec[qname] for rec in hourly])
				#qvals  = {rec['dt']:rec[qname] for rec in hourly}
				current = hist['current']
				logger.info('got %d %s dd from %s to %s' % (len(xdat),qname,xdat[0],xdat[-1]))
			else:
				xdat=[]
				ydat=[]
		return xdat,ydat

if __name__ == '__main__':
	_loop = asyncio.get_event_loop()
	logger = tls.get_logger(__file__,logging.INFO,logging.DEBUG)
	logger.info('jdnow={}'.format(julianday()))
	
	config = devConfig(CONFFILE)
	appkey = config['apikey']
	weather = openweather(appkey, veldhoven)
	
	tz = _loop.run_until_complete(get_timezone() )
	logger.info('tz={}'.format(tz))
	
	stuff =_loop.run_until_complete( weather.getCurrent() )
	if stuff:
		code = stuff['weather'][0]['id']
		descr = stuff['weather'][0]['description']
		logger.debug('weather:code:%s\n actual:%s \n ' % (code,stuff))
		icon =_loop.run_until_complete( getIcon(stuff['weather'][0]['icon']))
	
	forecast = 	_loop.run_until_complete( weather.getWeatherForecast() )
	logger.info('forecast ={}'.format(forecast))
	
	airpolut =  _loop.run_until_complete( weather.getAirQuality() )
	#airq = airpolut['list'][0]
	logger.info('air quality ={}'.format(airpolut))
	
	onec = _loop.run_until_complete( weather._collect('onecall') )
	if onec:
		current = onec['current']
		minutely = onec['minutely']
		precep = {rec['dt']:rec['precipitation'] for rec in minutely}
		hourly = onec['hourly']
		temp = {rec['dt']:rec['temp']-273 for rec in hourly}
		icons =  {rec['dt']:rec['weather'][0]['icon'] for rec in hourly}
		pressure  ={rec['dt']:rec['pressure'] for rec in hourly}
		daily = onec['daily']
		weer = {rec['dt']:rec['weather'] for rec in daily}
		descr = {dt:rec[0]['description'] for dt,rec in weer.items()}
		
		logger.debug('onecall:%s\n precep:%s \n temp:%s \n pressure:%s  \n weather:%s \n descr:%s ' % (current,precep,temp,pressure,weer,descr))
		
	#forecast = _loop.run_until_complete( restGet(appkey,lat=lat,lon=lon, collect='forecast',timeout=10) )	
	
	rain = _loop.run_until_complete(weather.getRainForecast())
	temp = _loop.run_until_complete(weather.getMainForecast(item='temp'))
	logger.info('forecast: rain:%s \n temp:%s' % (rain[1],temp[1]))
	
	history =  _loop.run_until_complete(weather.getHistory(ndays=2))
	logger.debug('history:x:%s\n y:%s' % history)
	"""
	forec = _loop.run_until_complete(weather.collect('forecast'))
	if forec:
		pressure  ={rec['dt']:rec['main']['pressure'] for rec in forec['list']}
		rain  = {rec['dt']:rec['rain']['3h'] for rec in forec['list'] if 'rain' in rec}
		logger.info('rain:%s \n pressure:%s' % (rain,pressure))
	"""	
else:	# this is running as a module
	logger = logging.getLogger(__name__)	# get logger from main program
	
