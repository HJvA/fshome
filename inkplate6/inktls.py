U2G8 ={
	2 : "img/helvB08_te.u8f",
	3 : "img/luRS18_te.u8f",
	4 : "img/inr24_mr.u8f",
	5 : "img/inr38_mr.u8f",  # "inb33_f.u8f",
	8 : "img/inr42_mr.u8f",
	10 :"img/inr53_mr.u8f",
	12 :"img/logisoso92_tn.u8f"	}
try:
	from inkplate6 import Inkplate,D_ROWS,D_COLS
except ImportError:
	from inkplate6_PLUS import Inkplate,D_ROWS,D_COLS
if U2G8:
	from u8g2_font import Font

scrWDTH = D_COLS
scrHGTH = D_ROWS
	
from grtls import julianday,prettydate,JulianTime

grxPOS = 100
gryHGTH= 200
gryPOS = scrHGTH-gryHGTH-70  #350
grxWDTH= scrWDTH - 300  #500

# display text fields txtsize:(width,height)
qFLDS = {	2 : (200, 16),
				3 : (280, 24),  # dd, title, ax
				4 : (180, 30),  # lbl
				5 : (180, 38),  # sideval
				8 : (200, 40),
				10: (360, 80),  # 
				12: (360, 92)   # qmain
				}

itmMAP = {0:'year',1:'month',2:'day',3:'hour',4:'minute'}
display=None
font=None

def inkInit():
	global display,font
	display = Inkplate(Inkplate.INKPLATE_1BIT)
	display.begin()
	if U2G8:
		display.setFont(None)  # free mem
		font = Font(U2G8[4], display.writePixel)
	print("ink display:{} x {} battery:{}".format(display.width(),display.height(),display.readBattery()) ) #, (esp32.raw_temperature()-32)/1.8))

def showText(txt,x,y, size=None,frm='{:>4}'):
	""" x,y=left,top """
	global display,font
	if display is None:
		return
	if size is None:
		size=4
	if size in U2G8:
		font = Font(U2G8[size], display.writePixel)
		#y+=qFLDS[size][1]
	elif size not in qFLDS:
		size = next(sz for sz,tp in qFLDS.items() if sz<abs(size))
		display.setTextSize(size)
	if frm:
		txt = frm.format(txt.upper())
	wd = qFLDS[size][0]  # 240
	mxwd=size*len(txt)*7
	print("shwtxt:'{}'({}):wdth={}->{}".format(txt,size,wd,mxwd))
	if wd>mxwd:
		wd =mxwd
	if x+wd>display.width():
		wd = display.width()-x-1
	ht = qFLDS[size][1] #100
	
	#display.drawRect(x,y,wd,ht,display.BLACK)	#fillRect(x, y, w, h, color)
	display.fillRect(x,y,wd,ht,display.WHITE)  # clear area
	#print("field.txt:{}:sz:{}@x,y:{},{} wd,ht:{},{}".format(txt,size,x,y,wd,ht))
	if font:  # 6plus
		font.text(txt, x, y+qFLDS[size][1], 1)
	else:
		display.printText(x,y, txt)  # Default font has only upper case letters
	return wd,ht
	
def showNumber(num,x=100,y=100, size=4, frmt='{:4.3g}', lbl=''):  # '{:5.1f}'
	#display.setTextSize(size)
	cmd = frmt.format(num)
	showText(lbl+cmd,x,y,size)
	
def showGraph(xdat,ydat,rad=5,clr=True,title=None):
	""" draw chart to grxPOS,gryPOS with xdat,ydat data and rad marker at each data point 
	 
	"""
	if xdat and ydat:
		minx=min(xdat)
		maxx=max(xdat)
		miny=min(ydat)
		maxy=max(ydat)
	else: 
		return
	if minx>=maxx or miny>=maxy:
		print("warn:uniform gr dat")
		return
	
	xscale = grxWDTH/(maxx-minx)
	yscale = gryHGTH/(maxy-miny)
	if clr:
		display.fillRect(grxPOS-rad, gryPOS-rad, grxWDTH+rad+rad, gryHGTH+rad+rad, display.WHITE)  # clear area
	#display.drawRect(grxPOS, gryPOS, grxWDTH, gryHGTH, display.BLACK)	# cadre
	display.drawRoundRect(grxPOS, gryPOS, grxWDTH, gryHGTH, 6, display.BLACK)
	
	utcnow=julianday(isMJD=True)  #datetime.datetime.utcnow().timestamp()
	#itoday = next(i for i,x in enumerate(xdat) if x > utcnow)
	xp = int(grxPOS + (utcnow-minx)*xscale)
	if xp>grxPOS and xp<grxPOS+grxWDTH:  # now marker.
		display.drawLine(xp,gryPOS,xp,gryPOS+gryHGTH,4)
	
	if maxx-minx>9:
		xstp = 7 # a week
		itm  = 1 # mnth
	elif maxx-minx>1:
		xstp=1  # a day
		itm =2  # mday
	else:
		xstp =1/24.0 # an hour
		itm =3  # hour
	nminx = (minx//xstp)*xstp  # normalise to multiples of xstp
	stps = [nminx+i*xstp+xstp for i in range(int((maxx-minx)//xstp))]
	print('graph min:{} {} max:{} {} xstp={} nstps={} today@{}'.format( nminx,miny,maxx,maxy, xstp,len(stps),utcnow))
	for jd in stps:
		xp = int(grxPOS + (jd-minx)*xscale)
		display.drawLine(xp,gryPOS,xp,gryPOS+gryHGTH,1)
		tmrk = JulianTime(jd,True)
		print('ax jd:{}=>{}'.format(jd,tmrk))
		showNumber(tmrk[itm], xp,gryPOS+gryHGTH+20, 3, '{:4.0f}')
	x0=y0=None
	for x,y in zip(xdat,ydat):
		xp = int(grxPOS + (x-minx)*xscale)
		yp = int(gryPOS + (maxy-y)*yscale)
		if x0 and y0:
			display.drawLine(x0,y0,xp,yp,4)
			#time.sleep(0.1)
		if rad==2:
			display.drawCircle(xp,yp,rad,display.BLACK)
		elif rad==3:
			display.drawRect(xp-rad,yp-rad,rad+rad,rad+rad,display.BLACK)
		elif rad:
			display.fillCircle(xp,yp,rad,display.BLACK)
		x0=xp
		y0=yp
	if title:
		showText(title+' / '+itmMAP[itm], grxPOS,gryPOS-10, 3)
		#display.display()
	
if __name__ == "__main__":
	inkInit()	
	jd0 = julianday()
	#display = Inkplate(Inkplate.INKPLATE_1BIT)
	#nic = nic_connect()
	#display.begin()
	showNumber(display.readBattery(),200,20,size=3,lbl='Vbatt:',frmt='{:5.2f}')
	
	showText('hjva1',420,70,12)
	tmax = [jd0+itm for itm in [.1,.2,.3,.4,.5]]
	showGraph(tmax,[0.1,0.11,0.14,0.02,0.02],title='tsGr')
	display.display()