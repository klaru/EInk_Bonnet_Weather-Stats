# SPDX-FileCopyrightText: 2020 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
This example queries the Open Weather Maps site API to find out the current
weather for your location... and display it on a eInk Bonnet!

This example is for use on (Linux) computers that are using Python with
Adafruit Blinka to support CircuitPython libraries. CircuitPython does
not support PIL/pillow (python imaging library)!
"""

import time
import subprocess
import urllib.request
import urllib.parse
import digitalio
import busio
import board
import secrets
from adafruit_epd.ssd1680 import Adafruit_SSD1680
from weather_graphics import Weather_Graphics
from PIL import Image, ImageDraw, ImageFont
from adafruit_extended_bus import ExtendedI2C as I2C
from adafruit_bh1750 import BH1750
from adafruit_bme680 import Adafruit_BME680_I2C as BME680
from Adafruit_IO import MQTTClient
import paho.mqtt.client as Paho_MQTT

topic3 = 'Temp_Kitchen'
topic4 = 'Humid_Kitchen'
topic5 = 'Press_Kitchen'
topic6 = 'Gas_Kitchen'
topic7 = 'Light_Kitchen'

bme680_addresses = [0x76,0x77]
bh1750_address = 0x23

BME680_REG_CHIPID = 0xD0
BME680_CHIPID = 0x61

client_adafruit = MQTTClient(secrets.ADAFRUIT_IO_USERNAME, secrets.ADAFRUIT_IO_KEY)
client_adafruit.connect()

client = Paho_MQTT.Client(client_id="P12")
client.connect(secrets.MQTT_HOST, 1883)

i2c1 = I2C(1)
devices = i2c1.scan()
for device in devices:
    for address in bme680_addresses:
        if device == address:
            sensor1 = BME680(address=address, i2c=i2c1)
sensor2 = BH1750(i2c1, address = bh1750_address)



spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
ecs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D22)
rst = digitalio.DigitalInOut(board.D27)
busy = digitalio.DigitalInOut(board.D17)

UNITS = "standard"
DATA_SOURCE_URL = "http://api.openweathermap.org/data/2.5/weather"

if len(secrets.OPEN_WEATHER_TOKEN) == 0:
    raise RuntimeError(
        "You need to set your token first. If you don't already have one, you can register for a free account at https://home.openweathermap.org/users/sign_up"
    )

# Set up where we'll be fetching data from
params = {"lat": secrets.LAT, "lon": secrets.LON, "appid": secrets.OPEN_WEATHER_TOKEN, "units": UNITS}
data_source = DATA_SOURCE_URL + "?" + urllib.parse.urlencode(params)


# Initialize the Display
display = Adafruit_SSD1680(     # Newer eInk Bonnet
    122, 250, spi, cs_pin=ecs, dc_pin=dc, sramcs_pin=None, rst_pin=rst, busy_pin=busy,
)

display.rotation = 1


# RGB Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Create blank image for drawing.
width = display.width
height = display.height
image = Image.new("RGB", (display.width, display.height), color=WHITE)

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Alternatively load a TTF font.  Make sure the .ttf font file is in the
# same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)


gfx = Weather_Graphics(display, am_pm=False, celsius=True)
weather_refresh = None

while True:
    # only query the weather every 10 minutes (and on first run)
    if (not weather_refresh) or (time.monotonic() - weather_refresh) > 600:
        response = urllib.request.urlopen(data_source)
        if response.getcode() == 200:
            value = response.read()
            print("Response is", value)
            gfx.display_weather(value)
            weather_refresh = time.monotonic()
        else:
            print("Unable to retrieve data at {}".format(url))

    try:
        temperature = sensor1.temperature
        humidity = sensor1.relative_humidity
        pressure = sensor1.pressure
    except OSError:
        print("BME680 doesn't respond")
    temperature1 = "%0.0f"% temperature
    humidity1 = "%0.0f"% humidity
    pressure1 = "%0.0f"% pressure
    #print("Temperature = %0.0f °C" % temperature)
    #print("Relative Humidity = %0.0f %%" % humidity)
    #print("Pressure = %0.0f mbar" % pressure)
    client_adafruit.publish(topic3, temperature1)
    client_adafruit.publish(topic4, "%0.0f"% humidity)
    client_adafruit.publish(topic5, "%0.0f"% pressure)
    client.publish(topic3, temperature1)
    client.publish(topic4, humidity1)
    client.publish(topic5, pressure1)

    if sensor1._read_byte(BME680_REG_CHIPID) == BME680_CHIPID:
        gas = sensor1.gas/1000
        gas1 = "%0.0f"% gas
        #print("Gas = %d kohm" % gas)
        client_adafruit.publish(topic6, "%0.0f"% gas)
        client.publish(topic6, gas1)

    try:
        light = sensor2.lux
    except OSError:
        print("BH1750 doesn't respond")
    light1 = "%0.0f"% light
    #print("Light intensity = %.0f Lux"%light)
    client_adafruit.publish(topic7, str("%0.0f"% light))
    client.publish(topic7, light1)

    gfx.update_time()
    time.sleep(10)  # wait 10 seconds

    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=WHITE)

    # Shell scripts for system monitoring from here:
    # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    cmd = "hostname -I | cut -d' ' -f1"
    IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
    CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'"
    MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = 'df -h | awk \'$NF=="/"{printf "Disk: %d/%d GB  %s", $3,$2,$5}\''
    Disk = subprocess.check_output(cmd, shell=True).decode("utf-8")

    # Write four lines of text.
    draw.text((x, top + 0), "IP: " + IP, font=font, fill=BLACK)
    draw.text((x, top + 16), CPU, font=font, fill=BLACK)
    draw.text((x, top + 32), MemUsage, font=font, fill=BLACK)
    draw.text((x, top + 48), Disk, font=font, fill=BLACK)

    draw.text((x, top + 64), "Temperature: " + temperature1 + " °C", font=font, fill=BLACK)
    draw.text((x, top + 80), "Humidity: " + humidity1 + " %" + "     Gas: " + gas1 + " kOhm", font=font, fill=BLACK)
    draw.text((x, top + 96), "Light Intensity: " + light1 + " lux", font=font, fill=BLACK)

    # Display image.
    display.image(image)
    display.display()
    time.sleep(10)

