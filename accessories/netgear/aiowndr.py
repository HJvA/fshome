""" for reading traffic from netgear WNDR4300 router
"""

import asyncio, aiohttp

import sys,os,time,logging,re
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))
import lib.tls as tls


logger = tls.get_logger(__file__, logging.DEBUG)
RENUM=r'"([\d,\.]+)"'  #  regex for float number between "
rxdct = dict(
	txToday=re.compile(r'today_up='+RENUM),  #, re.MULTILINE | re.IGNORECASE | re.ASCII | re.VERBOSE ),
	rxToday=re.compile(r'today_down='+RENUM),
	txYestday=re.compile(r'yesterday_up='+RENUM),
	rxYestday=re.compile(r'yesterday_down='+RENUM)
)

async def traffic(session: aiohttp.ClientSession, user = 'admin',pwd=None, host = '192.168.1.1', semaphore=None):
	''' gets traffic.htm page from host, parses page looking for items in rxdct '''
	#url = 'http://' + host +'/traffic_meter_2nd.htm' 
	#url = 'http://' + host +'/RST_statistic.htm'
	url = 'http://' + host +'/traffic.htm'

	#if hasattr(session,'auth'):
	if pwd:
		auth = aiohttp.BasicAuth(user, pwd)
	else:
		auth = None
	if semaphore is None:
		semaphore = asyncio.Semaphore()
		logger.info('WNDR no synchronisation with other http requests')
		
	for i in range(2):  # try it twice
		try:
			async with semaphore, session.get(url=url, auth=auth, timeout=2.0) as response:
				stuff = await response.text()
				if len(stuff)>1 and response.status<400:
					break  # success
		except Exception as e:
			logger.warning('%d wndr HTTPerror : %s' % (i,e))
			stuff = ''
	resp={}
	try:
		for (itm,rx) in rxdct.items():
			mtch = rx.search(stuff)
			if mtch:
				grp = mtch.group(1)
				resp[itm] = float(grp.replace(',',''))
				logger.debug('%s mtch.grp=%s=%f spn=%s' % (itm,grp,resp[itm], mtch.span()))
			else:
				logger.warning('no match with %s in %s for %s' % (rx, len(stuff), itm))
		if len(resp)==0:
			logger.warning('wndr nothing found in stuff:%s:=>%s' % (stuff,rxdct))
	except Exception as er:
		logger.error('%d http parse:%s' % (i,er))
	return resp

async def get_traffic(interval=15, host='192.168.1.1', pwd=None, semaphore=None):
	""" get traffic from wndr router in Mbytes """
	await asyncio.sleep(interval)
	#if semaphore is None:
	#	semaphore = HueBaseDev.Semaphore
	async with aiohttp.ClientSession() as session:
		return await traffic(session, pwd=pwd, host=host, semaphore=semaphore)

if __name__ == "__main__":
	traf = asyncio.run(get_traffic(pwd='har'))
	logger.info('\ntraffic:\n%s' % traf)
