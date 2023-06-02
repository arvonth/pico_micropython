# Display Image & text on I2C driven ssd1306 OLED display 
from machine import Pin, I2C, ADC
from ssd1306 import SSD1306_I2C
import framebuf
import utime
import sys
from PiicoDev_ENS160 import PiicoDev_ENS160 # import the device driver
from PiicoDev_Unified import sleep_ms       # a cross-platform sleep function


WIDTH  = 128                                            # oled display width
HEIGHT = 64                                            # oled display height
BUFFER_WIDTH = 4
CHARACTER_WIDTH = 8
CHARACTER_HEIGHT = 8

sensor_temp = ADC(4)
conversion_factor = 3.3 / (65535)

#Create a framebuffer that can be used to clear text
s = BUFFER_WIDTH * 8 * [0]
blank_buffer = bytearray(s)
blank_fb = framebuf.FrameBuffer(blank_buffer, BUFFER_WIDTH * CHARACTER_WIDTH, CHARACTER_WIDTH, framebuf.MONO_HLSB)

RESET_PIN = Pin(22, Pin.OUT)
print("Resetting OLED...",end='')
RESET_PIN.value(False)
utime.sleep(0.25)
RESET_PIN.value(True)
print("done")

i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)# Init I2C using pins GP8 & GP9 (default I2C0 pins)
for addr in i2c.scan():
    print(hex(addr).upper()+"    ",end='')
print()
oled_addr = int(i2c.scan()[0])
print("I2C Address      : "+hex(oled_addr).upper()) # Display device address
print("I2C Configuration: "+str(i2c))                   # Display I2C config


try:
    oled = SSD1306_I2C(WIDTH, HEIGHT, i2c,addr=oled_addr,external_vcc=False)                  # Init oled display
except OSError:
    print("EIO Error - Possible Address conflict")
    sys.exit()

sensor = PiicoDev_ENS160(bus=0,scl=Pin(5), sda=Pin(4),freq=400000)   # Initialise the ENS160 module




#setup some strings
aqi_str =  '   AQI: '
tvoc_str = '  TVOC: '
eco2_str = '  eCO2: '
stat_str = 'Status: '

# Clear the oled display in case it has junk on it.
oled.fill(0)
oled.show()

#template
oled.text(aqi_str,0,20)
oled.text(tvoc_str,0,30)
oled.text(eco2_str,0,40)
oled.text('  Temp: ',0,50)
oled.text("*F",105,50)
oled.show()


# Blit the image from the framebuffer to the oled display and animate
while True:
    meas_count = 0
    sum_readings = 0
    for i in range(5):
        sum_readings+=sensor_temp.read_u16() * conversion_factor
        meas_count+=1
        utime.sleep(0.010)
        
    oled.show()
    reading = sum_readings / meas_count
    celsius_degrees = 27 - (reading - 0.706)/0.001721
    fahrenheit_degrees = celsius_degrees * 9 / 5 + 32
    # Read from the sensor
    aqi = sensor.aqi
    tvoc = sensor.tvoc
    eco2 = sensor.eco2
    
    # Print air quality metrics and temperature
    print(aqi_str + str(aqi.value) + ' [' + str(aqi.rating) +']')
    print(tvoc_str + str(tvoc) + ' ppb')
    print(eco2_str + str(eco2.value) + ' ppm [' + str(eco2.rating) +']')
    print(stat_str + sensor.operation)
    print('  Temp: ' +str(round(fahrenheit_degrees,1)) + '°F')
    print('--------------------------------')
    text_y = 8
    oled.blit(blank_fb,0,text_y)
    oled.blit(blank_fb,BUFFER_WIDTH*8,text_y)
    oled.text(sensor.operation,0,8)
    text_y = 20
    oled.blit(blank_fb,65,text_y)
    oled.text(str(aqi.value),65,text_y)
    text_y = 30
    oled.blit(blank_fb,65,text_y)
    oled.text(str(tvoc),65,text_y)
    text_y = 40
    oled.blit(blank_fb,65,text_y)
    oled.text(str(eco2.value),65,text_y)

    text_y = 50
    oled.blit(blank_fb,65,text_y)
    oled.text(str(round(fahrenheit_degrees,1)),65,50)
    utime.sleep(5)