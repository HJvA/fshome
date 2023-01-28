
import time
from i2cPlus import i2cPlus,bitmask,getbits

# Register definitions
_I2C_ADDR = 0x48  # default I2C Address
_TEMP_RESULT = const(0x00)
_CONFIGURATION = const(0x01)
_T_HIGH_LIMIT = const(0x02)
_T_LOW_LIMIT = const(0x03)
_EEPROM_UL = const(0x04)
_EEPROM1 = const(0x05)
_EEPROM2 = const(0x06)
_TEMP_OFFSET = const(0x07)
_EEPROM3 = const(0x08)
_DEVICE_ID = const(0x0F)
_DEVICE_ID_VALUE = 0x0117
_TMP117_RESOLUTION = (0.0078125)  # Resolution of the device, found on (page 1 of datasheet)


convbits = {
	'HIalert':(15,1),
	'LOalert':(14,1),
	'DataReady':(13,1),
	'MOD':(10,2),
	'CONV':(7,3),
	'AVG':(5,2),
	'TnA':(4,1),
	'POL':(3,1),
	'DRalert':(2,1),
	'SoftReset':(1,1)
}
class tmp117(i2cPlus):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.conf = self._read_int(_CONFIGURATION, 2, False)
		chipId = self._read_int(_DEVICE_ID, 2, False)
		if chipId != _DEVICE_ID_VALUE:
			print("bad chipId:{}".format(chipId))
	@property
	def temperature(self):
		while not self.dataReady:
			time.sleep(0.2)
		return self._read_int(_TEMP_RESULT, 2) * _TMP117_RESOLUTION
	@property
	def dataReady(self):
		self.conf = self._read_int(_CONFIGURATION, 2, False)
		bpos,blen=convbits['DataReady']
		return getbits(self.conf, bitmask(blen,bpos) ) !=0 
	@property
	def alerted(self):
		bpos,blen = (14,2)
		return getbits(self.conf, bitmask(blen,bpos) )
	def get_conf_bits(self,bname):
		if bname in convbits:
			bpos,blen=convbits[bname]
			return self._read_bits(_CONFIGURATION,bpos,blen)
	def set_conf_bits(self,bname,bval):
		if bname in convbits:
			bpos,blen=convbits[bname]
			self._write_bits(_CONFIGURATION,bpos,blen,bval)
	@property
	def ThighLim(self):
		"""  """
		return self._read_int(_T_HIGH_LIMIT,signed=True) * _TMP117_RESOLUTION
	@ThighLim.setter
	def ThighLim(self, value):
		self._write_int(_T_HIGH_LIMIT, int(value /_TMP117_RESOLUTION), 2)
	@property
	def TlowLim(self):
		"""  """
		return self._read_int(_T_LOW_LIMIT,signed=True) * _TMP117_RESOLUTION
	@TlowLim.setter
	def TlowLim(self, value):
		self._write_int(_T_LOW_LIMIT, int(value / _TMP117_RESOLUTION), 2)
	@property
	def Toffset(self):
		"""  """
		return self._read_int(_TEMP_OFFSET, signed=True) * _TMP117_RESOLUTION
	@Toffset.setter
	def Toffset(self, value):
		self._write_int(_TEMP_OFFSET, int(value / _TMP117_RESOLUTION), 2)
		
	@property
	def confMode(self):
		""" 00:cc 01:sd 10:cc 11:os """
		return (self.conf &  0x0C00)
	@confMode.setter
	def confMode(self, value):
		self.conf = setbits(self.conf,value,0xC00)
		self._write_int(_CONFIGURATION, self.conf, 2)
	@property
	def confCycl(self):
		""" """
		return (self.conf & 0x0380)
	@property
	def averaging(self):
		""" """
		return self.conf & 0x0060
	@property
	def thermSel(self):
		""" """
		return (self.conf & 0x0010)
	@property
	def alertPol(self):
		""" """
		return (self.conf & 0x0008)
	@property
	def alertPin(self):
		""" """
		return (self.conf & 0x0004)
		

def main():
	#_i2c = i2cPlus.create()
	tmp = tmp117.create( addr=_I2C_ADDR)
	print("tmp117:{}".format(tmp))
	print("TlLim:{},ThLim:{},Tofs:{}".format(tmp.TlowLim, tmp.ThighLim, tmp.Toffset))
	print("{}={:02b}".format("MOD",tmp.get_conf_bits('MOD')))
	print("{}={:03b}".format("CONV",tmp.get_conf_bits('CONV')))
	print("{}={:02b}".format("AVG",tmp.get_conf_bits('AVG')))
	tmp.TlowLim =0
	tmp.ThighLim =21.0
	while True:
		print("T:{:5f} alert={:02b}".format(tmp.temperature,tmp.alerted))
		time.sleep(0.2)

if __name__ == "__main__":	
	import os,sys
	print("sys:{} mxsz{}",os.uname().sysname, sys.maxsize)
	main()