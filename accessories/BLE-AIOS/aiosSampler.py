#!/usr/bin/env python3.5
""" logs hue sensor values to a database """

import sys,os,time,logging,asyncio
if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../..'))
	from aiosAPI import aiosDelegate
else:
	from accessories.BLE-AIOS.aiosAPI import aiosDelegate
from lib.sampleCollector import DBsampleCollector
from lib.devConst import DEVT
from lib.tls import get_logger


class aiosSampler(DBsampleCollector):
	devdat = {}	# dict of hue devices (either lights or sensors)
	manufacturer="AdaFruit"
	minqid=600
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		aios = aiosDelegate()
		aios.startServiceNotifyers(dev.getServiceByUUID(btle.UUID(ENV_SVR))) # activate environamental service
		#aios.startChIdNotifyer(chDIGI, dev)
		aios.startChIdNotifyer(chANA1ST+3, dev)  # activate 3rd analog channel
		
	async def receive_message(self):
		''' get sensors state from hue bridge and check for updates and process recu when new '''
		n=0
		dat = await self.receiveCharValue()
		await asyncio.sleep(1)
		return n
		
	def set_state(self, quantity, state, prop='bri'):
		''' stateSetter for HAP to set hue device '''
		super().set_state(quantity, state, prop=prop)


if __name__ == "__main__":
	import asyncio
	logger = get_logger(__file__)  #logging.getLogger()
