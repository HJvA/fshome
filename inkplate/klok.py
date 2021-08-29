import machine 
import neopixel
import time
import grtls
"""
"""
nNEO = 12	# nr of leds
pNEO = 12	# pinnr

wzSEC = 0
wzMIN = 1
wzHR  = 2


class horloge():
	def __init__(self,pinnr=pNEO,nleds=nNEO):
		pn = machine.Pin(pinnr, machine.Pin.OUT) 
		self.np = neopixel.NeoPixel(pn, n=nleds,bpp=3,timing=1)   #800kHz
		self.np.fill( (0,0,0) )
		self.np.write()
		self.rgb={}
		self.scl={}
		self.actad={}
		self.actsb={}
		self.nleds=nleds
		self.last ={}

	def __del__(self):
		print("dispose klok")
		self.np.fill( (0,0,0) )
		self.np.write()
		
	def defWijzer(self, id, rgb, rndval=60):
		self.rgb[id]  = rgb
		self.scl[id]  = rndval
		self.actad[id]= 0
		self.actsb[id]= 0
		self.last[id] =0
	
	def prevLed(self, ldi):
		''' preceeding led '''
		return ldi-1 if ldi>0 else self.nleds-1
		
	def wijz(self, wid, tm):
		""" draw wijzer   tm : 0..scl """
		tpst = self.scl[wid]//self.nleds	# tm per led step
		frac = (tm % tpst) / tpst			# frac in step 
		ldi = tm // tpst						# front led
		if frac<self.last[wid]:				# next led pair
			print("new step ld0:{} ld:{} tm:{} fr:{}".format(self.prevLed(ldi),ldi,tm,frac))
			self.appl(wid, self.prevLed(ldi), 0)
			self.actsb[wid] = self.actad[wid]
			self.actad[wid] = 0
			self.last[wid]=0
		else:
			self.appl(wid, self.prevLed(ldi), 1-frac)
			self.appl(wid, ldi, frac)
			self.last[wid] = frac
		
	def appl(self, wid, ldi, frac=0.2):
		""" draw wijz led """
		fadd = frac-self.last[wid]
		if fadd>0:	# increasing
			self.actad[wid] += fadd
			#self.last[wid] = frac
			print("ld1:{} fadd:{} ".format(ldi,fadd))
		elif frac==0:
			fadd = -self.actsb[wid]
			print("ld0:{} fadd:{} off".format(ldi,fadd))
		else:
			self.actsb[wid] += fadd
			print("ld0:{} fadd:{}".format(ldi,fadd))
		add = [ld*abs(fadd) for ld in self.rgb[wid]]
		act = list(self.np[ldi])	# incl other wijz
		self.np[ldi] = [max(0,int(a+d)) for a,d in zip(act,add)]
	
	def klok(self,tobj):
		""" draw time """
		seco = tobj[6]
		minu = tobj[5]
		self.wijz(0, seco)
		#self.wijz(1, minu)
		self.np.write()

if __name__ == "__main__":
	kl = horloge()
	kl.defWijzer(0, (5,0,0) )	# red
	kl.defWijzer(1, (0,5,0))	# green
	try:
		while True:
			tobj = machine.RTC().datetime()
			kl.klok(tobj)
			time.sleep(0.9)
			#machine.lightsleep(1000)
	except Exception as ex:
		print("main error:",ex)
		#raise RuntimeError('Failed to continue') from ex
	finally:
		if kl:
			del kl
			