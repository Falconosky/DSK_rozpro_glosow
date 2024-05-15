import threading
import RPi.GPIO as GPIO
from set_sockets import czujnik

gpio_led=17
gpio_switch1=22
gpio_switch2=27

GPIO.setmode(GPIO.BCM)
GPIO.setup(gpio_led, GPIO.OUT)
GPIO.output(gpio_led, GPIO.LOW)
GPIO.setup(gpio_switch1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(gpio_switch2, GPIO.IN, pull_up_down=GPIO.PUD_UP)

threading.Thread(target=czujnik, args=(3, gpio_led, gpio_switch1, gpio_switch2)).start()