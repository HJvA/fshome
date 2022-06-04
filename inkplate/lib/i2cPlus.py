
from machine import I2C, Pin

def bitmask(nbits, toleft):
	mask = (1 << nbits) -1
	return mask << toleft
def setbits(reg, bval, mask):
	chg = (reg ^ bval) & mask
	return reg ^ chg
def getbits(reg, mask):
	while mask & 1 == 0:
		mask >>= 1
		reg >>= 1
	return reg & mask

class i2cPlus():
	def __init__(self, addr, ioSCL,ioSDA, debug=False):
		self.i2c = I2C(0, scl=Pin(ioSCL), sda=Pin(ioSDA), freq=10000)
		#super().__init__(0, scl=Pin(ioSCL), sda=Pin(ioSDA), freq=10000)
		if addr in self.i2c.scan():
			self._address = addr
		else:
			self._address = None
		self._debug = debug
		
	@classmethod
	def create(cls, addr, ioSCL=22, ioSDA=21, debug=False):
		""" defaults for inkplate6 """
		obj = cls(addr, ioSCL,ioSDA,debug)
		if obj._address:   #addr in obj.i2c.scan():
			return obj
	def __enter__(self):
		print('enter i2c')
		return self
	def __exit__(self, exc_type, exc_value, exc_traceback):
		print('exit:{} val:{}'.format(exc_type, exc_value))
		  
	def __repr__(self):
		return "{} on:{} at:{}".format(self.i2c, type(self).__name__, self._address)
	def _read(self, register, length):
		result = bytearray(length)
		if self._address:
			self.i2c.readfrom_mem_into(self._address, register & 0xff, result)
		#if self._debug:
		#	print("\t${:x} read ".format(register), " ".join(["{:02x}".format(i) for i in result]))
		return result
	def _write(self, register, values):
		if self._debug:
			print("\t${:x} write".format(register), " ".join(["{:02x}".format(i) for i in values]))
		#with self.i2c as i2c:
		if self._address:
			self.i2c.writeto_mem(self._address, register, values)
	def _read_byte(self, register):
		return self._read(register, 1)[0]
	def _write_byte(self, register, value):
		self._write(register, bytearray([value & 0xff]))
	def _read_int(self, register, length=2, signed=True):
		data = self._read(register, length)
		if signed and data[0] & 0x80: # negative
			iv=0
			for b in data:
				iv = (iv<<8) + ~b
			iv -= 1
		else:
			iv = int.from_bytes(data, 'big')
		if self._debug:
			print("rd reg:{0:02x}={1:016b}".format(register,iv))
		return iv
	def _write_int(self, register, value, length=2):
		data = value.to_bytes(length, 'big')
		self._write(register, data)
		if self._debug:
			print("wr reg:{0:02x}={1:016b}".format(register,value))
	def _read_bits(self,register,bpos,nbits):
		reg = self._read_int(register,2,False)
		msk = bitmask(nbits,bpos)
		#if self._debug:
		#	print("cnv:{0:02x} msk:{1:016b}".format(reg,msk))
		return getbits(reg, msk)
	def _write_bits(self,register,bpos,nbits,bval):
		reg = self._read_int(register,2,False)
		reg = setbits(reg, bval << bpos, bitmask(nbits,bpos))
		self._write_int(register,reg)
		