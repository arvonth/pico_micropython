from machine import Pin, I2C, ADC, WDT, reset
from micropython import const
import network
import utime
import sys
import framebuf

from ssd1306 import SSD1306_I2C
import onewire, ds18x20
from PiicoDev_ENS160 import PiicoDev_ENS160
from PiicoDev_Unified import sleep_ms
from umqtt.simple import MQTTClient
from secrets import ap, pw, mqtt_user, mqtt_pw

# === Constants ===
WIDTH = const(128)
HEIGHT = const(64)
BUFFER_WIDTH = const(8)
CHAR_WIDTH = const(8)
CHAR_HEIGHT = const(8)
REFRESH_SECONDS = const(10)

MQTT_SERVER = '192.168.1.131'
MQTT_PORT = 1883
MQTT_TOPICS = {
    "aqi": b'home-assistant/livingroom/aqi',
    "eco2": b'home-assistant/livingroom/eco2',
    "tvoc": b'home-assistant/livingroom/tvoc'
}

I2C0_SCL = Pin(5)
I2C0_SDA = Pin(4)
I2C0_FREQ = const(400_000)
I2C0_BUS = const(0)

# === Global Sensor Setup ===
sensor_temp = ADC(4)
VOLTAGE_CONVERSION = 3.3 / 65535
#blank_fb = framebuf.FrameBuffer(bytearray(BUFFER_WIDTH * 8), BUFFER_WIDTH * CHAR_WIDTH, CHAR_HEIGHT, framebuf.MONO_HLSB)
# Create a framebuffer to blank a 128x8 area of the display
blank_buffer = bytearray(128 * 8 // 8)  # 128 pixels wide × 8 pixels high ÷ 8 bits/byte
blank_fb = framebuf.FrameBuffer(blank_buffer, 128, 8, framebuf.MONO_HLSB)

# === Utility Functions ===

def average_temp_f():
    """Read and return temperature in Fahrenheit."""
    sum_readings = sum(sensor_temp.read_u16() * VOLTAGE_CONVERSION for _ in range(5))
    avg_reading = sum_readings / 5
    celsius = 27 - (avg_reading - 0.706) / 0.001721
    return round(celsius * 9 / 5 + 32, 1)

def celsius_to_fahrenheit(temp_c):
    return temp_c * 9 / 5 + 32

def read_ds18b20_temp(ds, ds_rom):
    """
    Initiates a temperature conversion and reads the temperature
    from a DS18B20 sensor.

    Args:
        ds (DS18X20): The DS18X20 temperature sensor object.
        ds_rom (bytearray): The ROM code of the sensor.

    Returns:
        float: The temperature in Celsius.
    """
    ds.convert_temp()
    utime.sleep_ms(750)  # Wait for conversion to complete
    temp_c = ds.read_temp(ds_rom)
    return temp_c

def init_i2c_display(i2c):
    """Initialize SSD1306 OLED display."""
    addr = i2c.scan()[0]
    print(f"I2C Address: {hex(addr).upper()}")

    try:
        oled = SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=addr, external_vcc=False)
        oled.text("Display...OK", 0, 10)
        oled.show()
        return oled
    except OSError:
        print("SSD1306 EIO Error - Possible Address conflict")
        sys.exit()

def init_ens160_sensor():
    """Initialize ENS160 sensor."""
    try:
        return PiicoDev_ENS160(bus=I2C0_BUS, scl=I2C0_SCL, sda=I2C0_SDA, freq=I2C0_FREQ)
    except OSError:
        print("ENS160 EIO Error - Possible Address conflict")
        sys.exit()

def connect_wifi(oled):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ap, pw)

    oled.text("WIFI...", 0, 40)
    oled.show()

    for _ in range(10):
        if wlan.status() >= 3:
            break
        utime.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError("Network connection failed")
    
    ip = wlan.ifconfig()[0]
    print(f"Connected. IP: {ip}")
    oled.text("WIFI...OK", 0, 40)
    oled.show()
    utime.sleep(2)
    oled.fill(0)

def init_system():
    """Initialize all hardware and return handles."""
    # Reset OLED if needed
    reset_pin = Pin(23, Pin.OUT)
    reset_pin.value(False)
    utime.sleep(0.25)
    reset_pin.value(True)

    i2c = I2C(I2C0_BUS, scl=I2C0_SCL, sda=I2C0_SDA, freq=I2C0_FREQ)
    oled = init_i2c_display(i2c)
    sensor = init_ens160_sensor()
    oled.text("Sensor...OK", 0, 20)
    oled.show()

    # Setup OneWire sensor (DS18B20)
    try:
        ow = onewire.OneWire(Pin(22))  # create a OneWire bus on GPIO22
        roms = ow.scan()
        if not roms:
            raise Exception("No DS18B20 sensor found")
        ds = ds18x20.DS18X20(ow)
        ds_rom = roms[0]
        oled.text("DS18B20...OK", 0, 30)
        oled.show()
    except Exception as e:
        oled.text("DS18B20...FAIL", 0, 30)
        oled.show()
        print("DS18B20 Error:", e)
        ds = None
        ds_rom = None

    connect_wifi(oled)

    return oled, sensor, ds_rom, ds

def mqtt_connect():
    """Connect to MQTT broker and return client."""
    try:
        client = MQTTClient('', MQTT_SERVER, MQTT_PORT, mqtt_user, mqtt_pw, keepalive=3600)
        client.connect()
        print(f'Connected to MQTT broker at {MQTT_SERVER}')
        return client
    except Exception as e:
        print("MQTT connection failed. Rebooting...")
        utime.sleep(5)
        reset()

def display_sensor_data(oled, sensor, temp_f):
    """Display sensor readings on the OLED screen."""
    aqi = sensor.aqi
    tvoc = sensor.tvoc
    eco2 = sensor.eco2
    operation = sensor.operation

    print(f"   AQI: {aqi.value} [{aqi.rating}]")
    print(f"  TVOC: {tvoc} ppb")
    print(f"  eCO2: {eco2.value} ppm [{eco2.rating}]")
    print(f"Status: {operation}")
    print(f"  Temp: {str(round(temp_f,1))}°F")
    print("-" * 32)

    # Clear lines
    for y in [8, 20, 30, 40, 50]:
        oled.blit(blank_fb, 0, y)

    # Display updated text
    oled.text(f"{operation}", 0, 8)
    oled.text(f" AQI: {aqi.value}", 0, 20)
    oled.text(f"TVOC: {tvoc}", 0, 30)
    oled.text(f"eCO2: {eco2.value}", 0, 40)
    oled.text(f"Temp: {round(temp_f,1)}  F", 0, 50)
    oled.text("o", 88, 45)
    oled.show()


# === Main Program ===

def main():
    oled, sensor, ds_rom, ds = init_system()
    mqtt_client = mqtt_connect()
    wdt = WDT(timeout=5000)

    while True:
        temp_c = read_ds18b20_temp(ds, ds_rom)
        temp_f = celsius_to_fahrenheit(temp_c)
        sensor.temperature = temp_c
        aqi = sensor.aqi
        tvoc = sensor.tvoc
        eco2 = sensor.eco2
        operation = sensor.operation

        display_sensor_data(oled, sensor, temp_f)

        mqtt_client.publish(MQTT_TOPICS['aqi'], str(aqi.value))
        mqtt_client.publish(MQTT_TOPICS['tvoc'], str(tvoc))
        mqtt_client.publish(MQTT_TOPICS['eco2'], str(eco2.value))

        for _ in range(REFRESH_SECONDS):
            utime.sleep(1)
            wdt.feed()

if __name__ == "__main__":
    main()
