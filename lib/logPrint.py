#!/usr/bin/env python3
""" just print selection from fs20 database to console
	shows latest records both tabular and graphically
	quantity can be selected as cmd line arg
"""

import sys,logging
from dbLogger import sqlLogger,prettyprint,graphyprint
from devConfig import devConfig

logger = logging.getLogger()
#[logger.removeHandler(h) for h in logger.handlers[::-1]] # handlers persist between calls
logger.addHandler(logging.FileHandler(filename='logPrint.log', mode='w')) #details to log file
handler=logging.StreamHandler()
handler.setLevel(logging.INFO) 
handler.setFormatter(logging.Formatter("[%(module)s] %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)  #INFO)  #DEBUG)

dbfile='~/fs20store.sqlite'
config = devConfig('fs20.json')
dbfile = config.getItem('dbFile',dbfile)
dbStore = sqlLogger(dbfile)	# must be created in same thread


#prettyprint (dbStore.fetch('motion',daysback=1))
#prettyprint(dbStore.fetchavg('temperature',tstep=60,daysback=0.25,source='kamer'))
quantities=['temperature']
Tidx=0
sources = list(dbStore.sources(quantities))
src = sources[0]
if len(sys.argv)>1:
	src = sys.argv[1]
	quantities=list(dbStore.quantities([src]))
	Tidx = quantities.index('temperature')
recs = dbStore.fetchavg(quantities[Tidx],tstep=60,daysback=4,source=src)
prettyprint(recs)

graphyprint(recs)
dbStore.close()

print ("pick from:\n%s" % sources)
print ("\r\033[2A",end='')

