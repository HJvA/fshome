#!/usr/bin/env python3
""" just print selection from fshome database to console
	 shows latest records both tabular and graphically
	 source/room can be selected as cmd line arg
"""

import sys,logging
from dbLogger import sqlLogger,prettyprint,graphyprint
from devConfig import devConfig
from devConst import DEVT,get_logger

logger = get_logger(__file__, logging.INFO)

dbfile='~/fs20store.sqlite'
config = devConfig('fs20.json')
dbfile = config.getItem('dbFile',dbfile)
dbStore = sqlLogger(dbfile)	# must be created in same thread

sources = list(dbStore.sources())
qtyp=DEVT['temperature']
qid=None
if len(sys.argv)>1:
	src = sys.argv[1]
	qid = dbStore.quantity(src,qtyp)
	
if not qid:
	for src in sources:
		qid = dbStore.quantity(src,qtyp)
		if qid:
			break
recs = dbStore.fetchiavg(qid,tstep=60,daysback=4,source=src)
prettyprint(recs)
logger.info("showing %s(%s) in %s" % (qid, dbStore.qname(qid), src))
graphyprint(recs)
dbStore.close()

print ("\npick from:\n%s" % sources)
print ("\r\033[2A",end='')

