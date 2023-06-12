from machine import Pin, I2C, ADC, const
from micropython import const
from ssd1306 import SSD1306_I2C
import framebuf
import utime
import sys
from image_arrays import bw_buffer
from PiicoDev_ENS160 import PiicoDev_ENS160 # import the device driver
from PiicoDev_Unified import sleep_ms       # a cross-platform sleep function
import network
from umqtt.simple import MQTTClient
from secrets import ap, pw



#Constants
WIDTH  = const(128)         # oled display width
HEIGHT = const(64)          # oled display height

#Strings
aqi_str =  '   AQI: '
tvoc_str = '  TVOC: '
eco2_str = '  eCO2: '
stat_str = 'Status: '

#i2c variables
i2c0_scl = Pin(5)
i2c0_sda = Pin(4)
i2c0_freq = 400000
i2c0_bus = 0

#wlan variables

#mqtt variables
mqtt_server = '192.168.1.138'
client_id = ''
aqi_topic = b'home-assistant/livingroom/aqi'
eco2_topic = b'home-assistant/livingroom/eco2'
tvoc_topic = b'home-assistant/livingroom/tvoc'


conversion_factor = 3.3 / (65535)

def init_system():
    """setup i2c devices, make the wifi connection, connect to mqtt broker"""
    
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
    except OSError:
        print("SSD1306 EIO Error - Possible Address conflict")
        sys.exit()

    try:
        sensor = PiicoDev_ENS160(bus=i2c0_bus,scl=i2c0_scl, sda=i2c0_sda,freq=i2c0_freq)   # Initialise the ENS160 module
    except OSError:
        print("ENS160 EIO Error - Possible Address conflict")
        sys.exit()

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ap,pw)
    utime.sleep(5)
    print(wlan.isconnected())

    return oled, sensor

def create_topic_dict(sensor):
    """given a sensor object create a dictionary of where the topic to publish is the key
    and the sensor reading is the value"""
    sensor_dict = {}
    sensor_dict[b'home-assistant/livingroom/aqi'] = sensor.aqi
    sensor_dict[b'home-assistant/livingroom/eco2'] = sensor.eco2
    sensor_dict[b'home-assistant/livingroom/tvoc'] = sensor.tvoc
    return sensor_dict

def mqtt_connect():
    client = MQTTClient(client_id, mqtt_server, keepalive=3600)
    client.connect()
    print('Connected to %s MQTT Broker'%(mqtt_server))
    return client

def reconnect():
    print('Failed to connect to the MQTT Broker. Reconnecting...')
    time.sleep(5)
    machine.reset()

def display_sensor_data():
    """display sensor data on the oled"""
    pass

def publish_mqtt_data(sensor_dict):
    """publish mqtt data"""
    try:
        client = mqtt_connect()
    except OSError as e:
        reconnect()
    for topic in sensor_dict:
        client.publish(topic,sensor_dict[topic])
    client.disconnect()



