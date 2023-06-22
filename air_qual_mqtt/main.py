from machine import Pin, I2C, ADC
from micropython import const
from ssd1306 import SSD1306_I2C
import framebuf
import utime
import sys
from PiicoDev_ENS160 import PiicoDev_ENS160 # import the device driver
from PiicoDev_Unified import sleep_ms       # a cross-platform sleep function
import network
from umqtt.simple import MQTTClient
from secrets import ap, pw



#Constants
WIDTH  = const(128)         # oled display width
HEIGHT = const(64)          # oled display height
BUFFER_WIDTH = const(4)
CHARACTER_WIDTH = const(8)
CHARACTER_HEIGHT = const(8)
refresh_period_seconds = const(10)

#Strings
aqi_str =  '   AQI: '
tvoc_str = '  TVOC: '
eco2_str = '  eCO2: '
stat_str = 'Status: '

#i2c variables
i2c0_scl = Pin(5)
i2c0_sda = Pin(4)
i2c0_freq = const(400000)
i2c0_bus = const(0)

#wlan variables

#mqtt variables
mqtt_server = '192.168.1.138'
client_id = ''
aqi_topic = b'home-assistant/livingroom/aqi'
eco2_topic = b'home-assistant/livingroom/eco2'
tvoc_topic = b'home-assistant/livingroom/tvoc'

sensor_temp = ADC(4)
conversion_factor = 3.3 / (65535)
#Create a framebuffer that can be used to clear text
s = BUFFER_WIDTH * 8 * [0]
blank_buffer = bytearray(s)
blank_fb = framebuf.FrameBuffer(blank_buffer, BUFFER_WIDTH * CHARACTER_WIDTH, CHARACTER_WIDTH, framebuf.MONO_HLSB)

def init_system():
    """setup i2c devices, make the wifi connection"""
    
    print("Wi-Fi Connecting...",end='')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ap,pw)
    utime.sleep(5)
    if(wlan.isconnected()):
        print("success!")
    else:
        print("failure")

    #This block is need for the older Adafruit displays that have reset pin
    RESET_PIN = Pin(22, Pin.OUT)
    print("Resetting OLED...",end='')
    RESET_PIN.value(False)
    utime.sleep(0.25)
    RESET_PIN.value(True)
    print("done")

    i2c = I2C(i2c0_bus, scl=i2c0_scl, sda=i2c0_sda, freq=i2c0_freq)# Init I2C using pins GP8 & GP9 (default I2C0 pins)
    oled_addr = int(i2c.scan()[0])
    print("I2C Address      : "+hex(oled_addr).upper()) # Display device address
    print("I2C Configuration: "+str(i2c))                   # Display I2C config


    try:
        oled = SSD1306_I2C(WIDTH, HEIGHT, i2c,addr=oled_addr,external_vcc=False)                  # Init oled display
        oled.text(aqi_str,0,20)
        oled.text(tvoc_str,0,30)
        oled.text(eco2_str,0,40)
        oled.text('  Temp: ',0,50)
        oled.text("*F",105,50)
        oled.show()
    except OSError:
        print("SSD1306 EIO Error - Possible Address conflict")
        sys.exit()

    try:
        sensor = PiicoDev_ENS160(bus=i2c0_bus,scl=i2c0_scl, sda=i2c0_sda,freq=i2c0_freq)   # Initialise the ENS160 module
    except OSError:
        print("ENS160 EIO Error - Possible Address conflict")
        sys.exit()
        
    return oled, sensor

def mqtt_connect():
    client = MQTTClient(client_id, mqtt_server, keepalive=3600)
    client.connect()
    print('Connected to %s MQTT Broker'%(mqtt_server))
    return client

def reconnect():
    print('Failed to connect to the MQTT Broker. Reconnecting...')
    utime.sleep(5)
    machine.reset()

def display_sensor_data(oled,aqi,eco2,tvoc,operation):
    """display sensor data on the oled"""
    meas_count = 0
    sum_readings = 0
    for i in range(5):
        sum_readings+=sensor_temp.read_u16() * conversion_factor
        meas_count+=1
        utime.sleep(0.010)
        
    reading = sum_readings / meas_count
    celsius_degrees = 27 - (reading - 0.706)/0.001721
    fahrenheit_degrees = celsius_degrees * 9 / 5 + 32
    
    # Print air quality metrics and temperature
    print(aqi_str + str(aqi.value) + ' [' + str(aqi.rating) +']')
    print(tvoc_str + str(tvoc) + ' ppb')
    print(eco2_str + str(eco2.value) + ' ppm [' + str(eco2.rating) +']')
    print(stat_str + operation)
    print('  Temp: ' +str(round(fahrenheit_degrees,1)) + '°F')
    print('--------------------------------')
    text_y = 8
    for x_offset in range(0,100,4):
        oled.blit(blank_fb,x_offset,text_y)
    oled.text(operation,0,8)
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
    oled.show()

def display_fatal_error():
    """Display an error if the sensor or network doesn't work"""
    pass

def main():
    """Main Loop"""
    oled, sensor = init_system()
    try:
        mqtt_client = mqtt_connect()
    except OSError as e:
        sys.exit()

    sensor_dict = {}

    while True:
        # Read from the sensor
        aqi = sensor.aqi
        tvoc = sensor.tvoc
        eco2 = sensor.eco2
        operation = sensor.operation

        #display sensor data
        display_sensor_data(oled,aqi,eco2,tvoc,operation)

        #publish the data
        mqtt_client.publish(aqi_topic,str(aqi.value))
        mqtt_client.publish(tvoc_topic,str(tvoc))
        mqtt_client.publish(eco2_topic,str(eco2.value))
        
        utime.sleep(refresh_period_seconds)
        
if __name__ == '__main__':
    main()



