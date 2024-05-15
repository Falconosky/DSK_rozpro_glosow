import threading
import RPi.GPIO as GPIO
from set_sockets import czujnik

gpio_led=10
gpio_switch1=11
gpio_switch2=9

GPIO.setmode(GPIO.BCM)
GPIO.setup(gpio_led, GPIO.OUT)
GPIO.setup(gpio_switch1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(gpio_switch2, GPIO.IN, pull_up_down=GPIO.PUD_UP)

threading.Thread(target=czujnik, args=(2, gpio_led, gpio_switch1, gpio_switch2)).start()