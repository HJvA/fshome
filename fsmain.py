#!/usr/bin/env python3.5
""" application to receive fs20 accessoire traffic and log results to homekit and to sqlite
	based on project HAP-python : https://github.com/ikalchev/HAP-python
"""

import logging
import signal
import time
import sys

from pyhap.accessory_driver import AccessoryDriver

sys.path.append(r"accessories/fs20")	# search path for imports
from fs20_hap import get_FS20_bridge,persist_FS20_config

__maintainer__ = "Henk Jan van Aalderen"
__email__ = "hjva@homail.nl"
__status__ = "Development"

# setup logging for console and error log and generic log
logger = logging.getLogger()
[logger.removeHandler(h) for h in logger.handlers[::-1]] # handlers persist between calls
handler=logging.StreamHandler()
handler.setLevel(logging.INFO) # console not to be cluttered with DEBUG
logger.addHandler(handler)
logger.addHandler(logging.FileHandler(filename='fs20.log', mode='w')) #details to log file
handler = logging.FileHandler(filename='error.log', mode='a')
handler.setLevel(logging.ERROR)	# only for error and critical messages
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)  #INFO)  #DEBUG)

logger.critical("### running %s dd %s ###" % (__file__,time.strftime("%y%m%d %H:%M:%S")))

driver = AccessoryDriver(port=51826)

bridge=get_FS20_bridge(driver, config="fs20.json")
driver.add_accessory(accessory=bridge)

#persist_FS20_config(driver)
#logger.info("config:%s" % serDevice.config.prettyValStr())

# We want SIGTERM (kill) to be handled by the driver itself,
# so that it can gracefully stop the accessory, server and advertising.
signal.signal(signal.SIGTERM, driver.signal_handler)

# Start it!
driver.start()

# terminate it
logger.info('bye')
for hnd in logger.handlers:
	hnd.flush()
logging.shutdown()
time.sleep(2)
