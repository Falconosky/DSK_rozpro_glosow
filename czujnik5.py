import threading
import RPi.GPIO as GPIO
from set_sockets import czujnik

gpio_led=14
gpio_switch1=18
gpio_switch2=15

GPIO.setmode(GPIO.BCM)
GPIO.setup(gpio_led, GPIO.OUT)
GPIO.output(gpio_led, GPIO.LOW)
GPIO.setup(gpio_switch1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(gpio_switch2, GPIO.IN, pull_up_down=GPIO.PUD_UP)

threading.Thread(target=czujnik, args=(4, gpio_led, gpio_switch1, gpio_switch2)).start()