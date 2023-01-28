
import os,sys,logging
from sqlite3 import connect,OperationalError
if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),'..'))

from lib.grtls import julianday,prettydate
from lib.tls import get_logger
from lib.dbLogger import sqlLogger

store = "/mnt/extssd/storage/fs20store.sqlite"
sql = "select quantity,qu.name,count(*) as cnt,cast((ddJulian-0.5)*24 as int) % 24 as hr,MIN(numval),AVG(numval),MAX(numval),MIN(ddJulian) as mnjd,MAX(ddJulian) as mxjd  from logdat inner join vwQuantities as qu on quantity=qu.id where julianday('now')-{} between ddJulian-1 and ddJulian  group by hr,quantity"
sql0 = """
SELECT qdy,ddJulian,numval,
		row_number() OVER win as rownr,
		first_value(ddJulian) OVER win as dd1st,
		first_value(numval) OVER win as num1st,
		last_value(ddJulian) OVER win as ddlst,
	   last_value(numval) OVER win as numlst,
		AVG(ddJulian) OVER win as ddavg, AVG(numval) OVER win as numavg
    FROM 
    (SELECT ddJulian,quantity,numval,ROUND(ddJulian*{1})%{2} as qdy FROM logdat
		WHERE quantity={3} AND {0} < ddJulian)
		WINDOW win AS (PARTITION BY qdy)
"""
def regression(qkey, jdback=1, itvhrs=6):
	""" """
	sql = """ SELECT qdy,COUNT(*) as cnt,dd1st,ddavg,ddlst,num1st,numavg,numlst, 
   SUM((ddJulian-ddavg)*(numval-numavg)) as ddSumNum, 
   SUM(((ddJulian-ddavg)*(ddJulian-ddavg))) as ddSumSqr
	FROM 
   (SELECT qdy,ddJulian,numval,
		first_value(ddJulian) OVER win as dd1st,
		first_value(numval) OVER win as num1st,
		last_value(ddJulian) OVER win as ddlst,
	   last_value(numval) OVER win as numlst,
		AVG(ddJulian) OVER win as ddavg,AVG(numval) OVER win as numavg
    FROM 
    (SELECT ddJulian,quantity,numval,CAST(ddJulian*{1} AS int)/{1} as qdy FROM logdat
	   WHERE quantity={3} AND {0} < ddJulian)
 	   WINDOW win AS (PARTITION BY qdy))
	 GROUP BY qdy 
	 """
	itvday=24/itvhrs
	jdstart = round((jd-jdback)*itvday+0.5)/itvday
	logger.info("q:{} strt:{}={} itv:{}".format(qkey,jdstart,prettydate(jdstart),itvhrs))
	recs=cur.execute(sql.format(jdstart, itvday,jdback*itvday, qkey))
	return recs


if __name__ == "__main__":		# for testing
	jdback=2  #1.0/24.0
	#jdback=7
	itvhrs = 6
	#itvhrs =24
	qkey =300 #P
	qkey =302 #V
	#qkey =804 #CO2
	qkey =806 #Press
	logger = get_logger(__file__, logging.DEBUG)  #logging.getLogger()
	#logger.removeHandler(h) for h in logger.handlers[::-1]]
	#logger.addHandler(logging.StreamHandler())	# use console
	#logger.setLevel(logging.DEBUG)

	dbstr = sqlLogger(store)
	rslt = dbstr.linRegression(qkey, itvhrs, jdback)
	#logger.info("linR:{}".format(rslt))
	dbstr.close()
	exit(0)   
	#raise Exception()
	
	con=connect(store, check_same_thread=False)
	with con:
		cur = con.cursor()
		try:
			jd=julianday()
			recs = regression(qkey, jdback, itvhrs)
			for rec in recs:
				logger.info("{}".format(rec))
		except OperationalError:
			logger.exception("db error")
		
	