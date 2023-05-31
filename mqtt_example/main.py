"""
MQTT example based on Les Pounder's article on Tom's Hardware
https://www.tomshardware.com/how-to/send-and-receive-data-raspberry-pi-pico-w-mqtt
"""

import network
import time
from machine import Pin
from umqtt.simple import MQTTClient
from secrets import ap, pw

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ap,pw)
time.sleep(5)
print(wlan.isconnected())

sensor = Pin(20, Pin.IN)

mqtt_server = '192.168.1.138'
client_id = ''
topic_pub = b'home-assistant/livingroom/motion/state'
topic_msg_mov = b'movement'
topic_msg_clr = b'clear'
# mqtt_server = 'broker.hivemq.com'
# client_id = 'bigles'
# topic_pub = b'TomsHardware'
# topic_msg = b'Movement Detected'

def mqtt_connect():
    client = MQTTClient(client_id, mqtt_server, keepalive=3600)
    client.connect()
    print('Connected to %s MQTT Broker'%(mqtt_server))
    return client

def reconnect():
    print('Failed to connect to the MQTT Broker. Reconnecting...')
    time.sleep(5)
    machine.reset()

try:
    client = mqtt_connect()
except OSError as e:
    reconnect()
while True:
    if sensor.value() == 0:
        client.publish(topic_pub, topic_msg_mov)
        time.sleep(10)
        client.publish(topic_pub,topic_msg_clr)
    else:
        pass