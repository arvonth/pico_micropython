# Display Image & text on I2C driven ssd1306 OLED display 
from machine import Pin, I2C, ADC
from ssd1306 import SSD1306_I2C
import framebuf
import utime
import sys
from image_arrays import bw_buffer

WIDTH  = 128                                            # oled display width
HEIGHT = 64                                            # oled display height

sensor_temp = ADC(4)
conversion_factor = 3.3 / (65535)

RESET_PIN = Pin(22, Pin.OUT)
print("Resetting OLED...",end='')
RESET_PIN.value(False)
utime.sleep(0.25)
RESET_PIN.value(True)
print("done")

i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)# Init I2C using pins GP8 & GP9 (default I2C0 pins)
oled_addr = int(i2c.scan()[0])
print("I2C Address      : "+hex(oled_addr).upper()) # Display device address
print("I2C Configuration: "+str(i2c))                   # Display I2C config


try:
    oled = SSD1306_I2C(WIDTH, HEIGHT, i2c,addr=oled_addr,external_vcc=False)                  # Init oled display
except OSError:
    print("EIO Error - Possible Address conflict")
    sys.exit()

# Raspberry Pi logo as 32x32 bytearray
rpi_buffer = bytearray(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00|?\x00\x01\x86@\x80\x01\x01\x80\x80\x01\x11\x88\x80\x01\x05\xa0\x80\x00\x83\xc1\x00\x00C\xe3\x00\x00~\xfc\x00\x00L'\x00\x00\x9c\x11\x00\x00\xbf\xfd\x00\x00\xe1\x87\x00\x01\xc1\x83\x80\x02A\x82@\x02A\x82@\x02\xc1\xc2@\x02\xf6>\xc0\x01\xfc=\x80\x01\x18\x18\x80\x01\x88\x10\x80\x00\x8c!\x00\x00\x87\xf1\x00\x00\x7f\xf6\x00\x008\x1c\x00\x00\x0c \x00\x00\x03\xc0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
# Load the raspberry pi logo into the framebuffer (the image is 32x32)
fb = framebuf.FrameBuffer(rpi_buffer, 32, 32, framebuf.MONO_HLSB)

# Load the BW logo into the framebuffer (the image is 64x64)
image_w = 616
image_h = 64
bw_fb = framebuf.FrameBuffer(bw_buffer, image_w, image_h, framebuf.MONO_HLSB)


# Clear the oled display in case it has junk on it.
oled.fill(0)
oled.show()
# oled.blit(bw_fb,-480,0)
# oled.show()

# Blit the image from the framebuffer to the oled display and animate
while True:
    meas_count = 0
    sum_readings = 0
    for i in range(128,-520,-1):
        oled.blit(bw_fb, i, 0)
        oled.show()
        sum_readings+=sensor_temp.read_u16() * conversion_factor
        meas_count+=1
        
    oled.fill(0)
    oled.show()
    reading = sum_readings / meas_count
    celsius_degrees = 27 - (reading - 0.706)/0.001721
    fahrenheit_degrees = celsius_degrees * 9 / 5 + 32
    print(str(round(fahrenheit_degrees,2)))
    oled.text("Temp: ",6,8)
    oled.text(str(round(fahrenheit_degrees,1)),50,8)
    oled.text("*F",95,8)
    oled.show()
    utime.sleep(3)
    oled.fill(0)
    oled.show()


