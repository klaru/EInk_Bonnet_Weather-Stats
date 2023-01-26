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

topic3 = 'Temp_LivingRoom'
topic4 = 'Humid_LivingRoom'
topic5 = 'Press_LivingRoom'
topic6 = 'Gas_LivingRoom'
topic7 = 'Light_LivingRoom'

bme680_address = 0x77
bh1750_address = 0x23

BME680_REG_CHIPID = 0xD0
BME680_CHIPID = 0x61

client_adafruit = MQTTClient(secrets.ADAFRUIT_IO_USERNAME, secrets.ADAFRUIT_IO_KEY)
client_adafruit.connect()

i2c1 = I2C(1)
sensor1 = BME680(address=bme680_address, i2c=i2c1)
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
        "You need to set your token first. If you don't already have one, you can register for a free account at http>
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

    temperature = sensor1.temperature
    humidity = sensor1.relative_humidity
    pressure = sensor1.pressure
    #print("Temperature = %0.0f °C" % temperature)
    #print("Relative Humidity = %0.0f %%" % humidity)
    #print("Pressure = %0.0f mbar" % pressure)
    client_adafruit.publish(topic3, "%0.0f"% temperature)
    client_adafruit.publish(topic4, str("%0.0f"% humidity))
    client_adafruit.publish(topic5, str("%0.0f"% pressure))

    if sensor1._read_byte(BME680_REG_CHIPID) == BME680_CHIPID:
        gas = sensor1.gas/1000
        #print("Gas = %d kohm" % gas)
        client_adafruit.publish(topic6, "%0.0f"% gas)
    
    light = sensor2.lux
    #print("Light intensity = %.0f Lux"%light)
    client_adafruit.publish(topic7, str("%0.0f"% light))

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

    # Display image.
    display.image(image)
    display.display()
    time.sleep(10)
