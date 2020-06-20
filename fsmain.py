#!/usr/bin/env python3.5
""" application to receive fs20/hue/DSMR accessoire traffic and log results to sqlite and optionally to homekit.
	uses project HAP-python : https://github.com/ikalchev/HAP-python
"""

import logging
import signal
import time
import os

from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import __version__ as pyHAP_version
from lib.fsHapper import fsBridge
from accessories.hue.hueHap import add_HUE_to_bridge
from accessories.p1smart.p1DSMR_Hap import add_p1DSMR_to_bridge
from accessories.fs20.fs20_hap import add_fs20_to_bridge
from accessories.BLEAIOS.aiosHap import add_AIOS_to_bridge
from accessories.netgear.netgear_HAP import add_WNDR_to_bridge
from lib.tls import get_logger

__maintainer__ = "Henk Jan van Aalderen"
__email__ = "hjva@notmail.nl"
__status__ = "Development"

# setup logging for console and error log and generic log
logger = get_logger(__file__, logging.INFO, logging.INFO)
logger.info('with HAP-python %s' % pyHAP_version)

driver = AccessoryDriver(port=51826)
bridge= fsBridge(driver, 'fsBridge')

if os.path.isfile("fs20.json"):
	add_fs20_to_bridge(bridge, config="fs20.json")
if os.path.isfile("p1DSMR.json"):
	add_p1DSMR_to_bridge(bridge, config="p1DSMR.json")
if os.path.isfile("hue.json"):
	add_HUE_to_bridge(bridge, config="hue.json")
if os.path.isfile("deCONZ.json"):
	add_HUE_to_bridge(bridge, config="deCONZ.json")
if os.path.isfile("aios.json"):
	add_AIOS_to_bridge(bridge, config="aios.json")
if os.path.isfile("WNDR.json"):
	add_WNDR_to_bridge(bridge, config="WNDR.json")

driver.add_accessory(accessory=bridge)

signal.signal(signal.SIGTERM, driver.signal_handler)

driver.start()

# terminate it 
logger.info('bye')
for hnd in logger.handlers:
	hnd.flush()
logging.shutdown()
logging._handlers.clear()
time.sleep(2)
