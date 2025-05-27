import network
import time
from machine import Pin
from umqtt.simple import MQTTClient
from secrets import ap, pw, mqtt_user, mqtt_pw

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ap,pw)
time.sleep(5)
print(wlan.isconnected())

LED = Pin("LED", Pin.OUT)

mqtt_server = '192.168.1.131'
mqtt_port = 1883
client_id = ''
topic_sub = b'home-assistant/garage-door/state'


def sub_cb(topic, msg):
    print("New message on topic {}".format(topic.decode('utf-8')))
    msg = msg.decode('utf-8')
    print(msg)
    if msg == "Open":
        LED.on()
    elif msg == "Closed":
        LED.off()

def mqtt_connect():
    #client = MQTTClient(client_id, mqtt_server, keepalive=60)
    client = MQTTClient('', mqtt_server, mqtt_port, mqtt_user, mqtt_pw, keepalive=60)
    client.set_callback(sub_cb)
    client.connect()
    print('Connected to %s MQTT Broker'%(mqtt_server))
    return client

def reconnect():
    print('Failed to connect to MQTT Broker. Reconnecting...')
    time.sleep(5)
    machine.reset()
    
try:
    client = mqtt_connect()
except OSError as e:
    reconnect()
while True:
    client.subscribe(topic_sub)
    time.sleep(1)
    print("tick")