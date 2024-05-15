import socket
import time
import threading
import queue
import RPi.GPIO as GPIO


def send_messages_thread(ktory_socket, czujniki_porty, message_queue, gpio_led, gpio_switch1, gpio_switch2):
    GPIO.setmode(GPIO.BCM)
    #   STALE KONFIGURACYJNE
    cooldown_otrzymania_info_o_pozarze = 30     # w sekundach

    #   schemat wiadomosci
    #   {typ_wiadomosci}{numer_czujnika_nadawczego}{informacja}
    #       typ_wiadomosci: 1   -   informacje o pozarze
    #       1{numer_czujnika_nadawczego}{bool:jest_pozar/nie_ma_pozaru}
    #       -----------------------------------------------------------
    #       typ_wiadomosci: 2   -   wymiana informacji o zebranych komunikatach
    #       2{numer_czujnika_nadawczego}{bool_czuj0}{bool_czuj1}{bool_czuj2}{bool_czuj3}{bool_czuj4}

    wlasna_tablica_otrzymanych_informacji = ['0', '0', '0', '0', '0']
    klienci_tablica_otrzymanych_informacji = [['0', '0', '0', '0', '0'],
                                              ['0', '0', '0', '0', '0'],
                                              ['0', '0', '0', '0', '0'],
                                              ['0', '0', '0', '0', '0']]
    time_otrzymania_info_o_pozarze = [0, 0, 0, 0]

    while True:
        #   Wysyłanie informacji o pozarze
        stan_czujnika = None
        tresc_wiadomosci = '2'

        #   !!!!!!!!!!!!!!!!!   TEMP    !!!!!!!!!!!!!!!!!
        if GPIO.input(gpio_switch1) == GPIO.LOW:
            stan_czujnika = 1
        else:
            stan_czujnika = 0

        if tresc_wiadomosci[0] == '1':
            tresc_wiadomosci = '2'+str(ktory_socket)
            tresc_wiadomosci += wlasna_tablica_otrzymanych_informacji[0]
            tresc_wiadomosci += wlasna_tablica_otrzymanych_informacji[1]
            tresc_wiadomosci += wlasna_tablica_otrzymanych_informacji[2]
            tresc_wiadomosci += wlasna_tablica_otrzymanych_informacji[3]
            tresc_wiadomosci += wlasna_tablica_otrzymanych_informacji[4]
        elif tresc_wiadomosci[0] == '2':
            tresc_wiadomosci = '1'+str(ktory_socket)+str(stan_czujnika)

        time.sleep(5)
        for i, port in enumerate(czujniki_porty):
            if i != ktory_socket:  # Nie wysyłać do samego siebie
                client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                client_address = ('localhost', port)
                message = f'{tresc_wiadomosci}'
                client_sock.sendto(message.encode(), client_address)
                client_sock.close()

        # Sprawdzanie kolejki na nowe wiadomości do wyświetlenia
        try:
            while not message_queue.empty():
                msg = message_queue.get_nowait()
                if msg[0] == '1':
                    if msg[2] == '1':
                        if time_otrzymania_info_o_pozarze[int(msg[1])] == 0:
                            time_otrzymania_info_o_pozarze[int(msg[1])] = time.time()
                        elif time_otrzymania_info_o_pozarze[int(msg[1])] + cooldown_otrzymania_info_o_pozarze < time.time():
                            #   AWARIA ze zbyt dlugim pozarem
                            wlasna_tablica_otrzymanych_informacji[int(msg[1])] = 'x'

                        # weryfikacja czy jest pozar
                        ile_czujnikow_dziala = 0
                        ile_czujnikow_plonie = 0
                        for i in range(5):
                            if not str(wlasna_tablica_otrzymanych_informacji[i]) == 'x':
                                if str(wlasna_tablica_otrzymanych_informacji[i]) == '1':
                                    ile_czujnikow_plonie += 1
                                ile_czujnikow_dziala += 1
                        if ile_czujnikow_plonie >= ile_czujnikow_dziala/2:
                            GPIO.output(gpio_led, GPIO.HIGH)
                        else:
                            GPIO.output(gpio_led, GPIO.LOW)
                    wlasna_tablica_otrzymanych_informacji[int(msg[1])] = msg[2]
                if msg[0] == '2':
                    klienci_tablica_otrzymanych_informacji[int(msg[1])][0] = msg[2]
                    klienci_tablica_otrzymanych_informacji[int(msg[1])][1] = msg[3]
                    klienci_tablica_otrzymanych_informacji[int(msg[1])][2] = msg[4]
                    klienci_tablica_otrzymanych_informacji[int(msg[1])][3] = msg[5]
                    klienci_tablica_otrzymanych_informacji[int(msg[1])][4] = msg[6]
                    #   Obsluga bledu nr3
                    for i in range(5):
                        if wlasna_tablica_otrzymanych_informacji[i] != klienci_tablica_otrzymanych_informacji[int(msg[1])][i]:
                            wlasna_tablica_otrzymanych_informacji[i] = 'x'
                            print("awaria typu 3")

                print(wlasna_tablica_otrzymanych_informacji)
        except queue.Empty:
            continue


def receive_messages_thread(ktory_socket, server_sock, message_queue):
    while True:
        data, address = server_sock.recvfrom(4096)
        if data:
            data_decoded = data.decode('utf-8')
            message = f"{data_decoded}"
            message_queue.put(message)  # Dodanie wiadomości do kolejki


def czujnik(ktory_socket, gpio_led, gpio_switch1, gpio_switch2):
    GPIO.setmode(GPIO.BCM)
    czujniki_porty = [10001, 10002, 10003, 10004, 10005]
    message_queue = queue.Queue()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('localhost', czujniki_porty[ktory_socket])
    server_sock.bind(server_address)

    # Uruchomienie wątku do wysyłania wiadomości
    threading.Thread(target=send_messages_thread, args=(ktory_socket, czujniki_porty, message_queue, gpio_led, gpio_switch1, gpio_switch2)).start()

    # Uruchomienie wątku do odbierania wiadomości
    threading.Thread(target=receive_messages_thread, args=(ktory_socket, server_sock, message_queue)).start()
