#!/usr/bin/env python3
""" just print selection from fshome database to console
	 shows latest records both tabular and graphically
	 source/room can be selected as cmd line arg
"""

import sys,logging
from submod.pyCommon.tls import get_logger
from lib.dbLogger import sqlLogger,its
#from lib.grtls import prettyprint,graphyprint,julianday
from submod.pyCommon.timtls import prettyprint,graphyprint,julianday,tmTUP,normGRdat
from lib.devConfig import devConfig
from lib.devConst import DEVT,qCOUNTING,qACCUMULATING,typnames

from submod.cutie import cutie
import pdb

logger = get_logger(__file__, logging.INFO, logging.DEBUG)

dbfile= '/mnt/extssd/storage/fs20store.sqlite' #  '~/fs20store.sqlite'
config = devConfig('~/fshome/config/fs20.json')
dbfile = config.getItem('dbFile',dbfile)
dbStore = sqlLogger(dbfile)	# must be created in same thread

ndays = cutie.get_number("days back:",0.5,allow_float=True)

stats = dbStore.statistics(ndays) # for fun
sources = list(dbStore.sources(minDaysBack=ndays))

qid=None
if len(sys.argv)>1:
	src = sys.argv[1]
else:
	print("sources:")
	isrc = cutie.select(sources)
	src = sources[isrc]

selqs=typnames(dbStore.quantities([src],prop=2))
print("typ:")
qtyp = cutie.select(selqs)
if not qtyp:
	pdb.set_trace()
	qtyp=DEVT['temperature']
qid = dbStore.quantity(src,qtyp)
logger.info("qsrc:{} qtyp:{} qid:{} qnm:{} nd:{} tmtup:{}".format(src, qtyp, qid, dbStore.qname(qid), ndays, tmTUP(ndays)))

if not qid:
	pdb.set_trace()
	for src in sources:
		qid = dbStore.quantity(src,qtyp)
		if qid:
			logger.info("finding first typ:{} -> qid:{} in {}".format(qtyp,qid,src))
			break

mnstep = tmTUP(ndays).avgmin
#mnstep = cutie.get_number("bar interv minutes:",30,allow_float=False)
regr = dbStore.linRegression(qid, mnstep/60, ndays)
logger.info("regression:{}".format(regr))

recs={}
dbres = dbStore.fetchiavg(qid,mnstep=mnstep,daysback=ndays,jdend=None)
if dbres:
	if dbStore.qtyp(qid) in qACCUMULATING:
		vFirst = dbres[0][1]
	else:
		pdb.set_trace()
		vFirst = 0.0
	#recs[qid] = [rec[1]-vFirst for rec in dbres]
	#recs[qid*10] = [round(rec[0]-2400000.5,3) for rec in dbres]  # MJD
	jdlast = dbres[-1][0]
	#nrmrec = normGRdat(dbres)
	#prettyprint(dbres)
	logger.debug("showing {}({}) in {} n={}".format(qid, dbStore.qname(qid), src, len(dbres)))
	graphyprint(dbres)
else:
	logger.warning("no recs in database for qid:{} last days:{}".format(qid,4))
dbStore.close()

print ("\npick from:\n%s" % sources)
print ("\r\033[2A",end='')

