import threading
from set_sockets import czujnik

threading.Thread(target=czujnik, args=(0,)).start()
