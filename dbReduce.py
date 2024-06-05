import logging
from collections import namedtuple
from submod.pyCommon.tls import get_logger
from lib.devConfig import devConfig
from lib.dbLogger import sqlLogger
from lib.devConst import DEVT,qCOUNTING,qACCUMULATING,strokes,SIsymb,qSrc, qDEF,qtName,typnames,typSI

DEBUG=False

if __name__ == '__main__':
	logger = get_logger(__file__,logging.INFO, logging.DEBUG if DEBUG else logging.INFO)
	conf={	# to be loaded from json file
		#"dbFile": "/mnt/extssd/storage/fs20store.sqlite"
		"dbFile": '~/work/fs20store.sqlite',
	}
	dbFile=conf['dbFile']
	dbStore = sqlLogger(dbFile)
	#logger.info("dbStat:{}".format(dbStore.statistics()))

	ndays=1 #1/24
	flds="source,quantity,name,type"
	sql = f"SELECT {flds},COUNT(*) as cnt,AVG(numval) as avgval,MIN(numval) as minval,MAX(numval) as maxval, MIN(ddJulian) jdFirst " \
			f"FROM logdat,quantities WHERE ID=quantity AND ddJulian BETWEEN julianday('now')-{ndays} AND julianday('now') " \
			f"GROUP BY {flds} ORDER BY ID;" #.format(flds,ndays,flds)
	breakpoint()
	recs = dbStore.execute(sql)
	#qRec = namedtuple('qRec', flds + ',cnt,avgval,jdFirst')
	#breakpoint()
	for rec in recs:
		#nrec = qRec(*rec)
		logger.info("rec:{}".format(rec))
	
else:	# this is running as a module
	logger = get_logger()	# get logger from main program
