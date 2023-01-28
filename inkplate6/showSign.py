from machine import Pin
import neopixel
import time
"""
Pins 1 and 3 are REPL UART TX and RX respectively
Pins 6, 7, 8, 11, 16, and 17 are used for connecting the embedded flash, and are not recommended for other uses
Pins 34-39 are input only, and also do not have internal pull-up resistors
The pull value of some pins can be set to Pin.PULL_HOLD to reduce power consumption during deepsleep.
"""
pin = Pin(12, Pin.OUT) # The pin pins available for NeoPixel are P5, P6, P7 (RGB on board), P8, P9, P11, P13, P14, P15, P16, P19, P20 of the control board.
np = neopixel.NeoPixel(pin, n=12,bpp=3,timing=1)   #800khz

np[0] = (255, 255, 255) # Set the first LED pixel to white
np.write()

def demo(np):
	n = np.n

	# cycle
	for i in range(4 * n):
		for j in range(n):
			np[j] = (0, 0, 0)
		np[i % n] = (255, 255, 255)
		np.write()
		time.sleep_ms(25)
	
	# bounce
	for i in range(4 * n):
		for j in range(n):
			np[j] = (0, 0, 128)
		if (i // n) % 2 == 0:
			np[i % n] = (0, 0, 0)
		else:
			np[n - 1 - (i % n)] = (0, 0, 0)
		np.write()
		time.sleep_ms(60)
	
	 # fade in/out
	for i in range(0, 4 * 256, 8):
		for j in range(n):
			if (i // 256) % 2 == 0:
				val = i & 0xff
			else:
				val = 255 - (i & 0xff)
			np[j] = (val, 0, 0)
		np.write()

    # clear
	for i in range(n):
		np[i] = (0, 0, 0)
		np.write()

if __name__ == "__main__":
	demo(np)
	time.sleep(10)
	np.fill( (255, 255, 255) )
	#np.brightness(0.5)