import random
import socket
import time
import threading
import queue
import RPi.GPIO as GPIO

debug_level = 1

def blink(gpio_led, blink_queue):
    GPIO.setmode(GPIO.BCM)

    blinking_duration = 1
    loop_speed = 0.5  # Jak szybko/często wątek sprawdza zawartość kolejki
    sie_pali_czy_nie = 0
    last_time = 0
    tryb = None

    while True:
        try:
            # Sprawdzanie, czy w kolejce są nowe wiadomości
            while not blink_queue.empty():
                tryb = blink_queue.get_nowait()
                print("Tryb: " + str(tryb))

            # Działania zależne od trybu
            if tryb == 0:
                GPIO.output(gpio_led, GPIO.LOW)
            elif tryb == 1:
                GPIO.output(gpio_led, GPIO.HIGH)
            elif tryb == 2:
                current_time = time.time()
                if sie_pali_czy_nie == 0 and last_time + blinking_duration < current_time:
                    GPIO.output(gpio_led, GPIO.HIGH)
                    last_time = current_time
                    sie_pali_czy_nie = 1
                elif sie_pali_czy_nie == 1 and last_time + blinking_duration < current_time:
                    GPIO.output(gpio_led, GPIO.LOW)
                    last_time = current_time
                    sie_pali_czy_nie = 0

            # Czekanie przed kolejnym cyklem pętli
            time.sleep(loop_speed)
        except queue.Empty:
            print("Kolejka jest teraz pusta.")
            continue

def send_messages_thread(ktory_socket, czujniki_porty, message_queue, gpio_led, gpio_switch1, gpio_switch2):
    GPIO.setmode(GPIO.BCM)
    #   STALE KONFIGURACYJNE
    cooldown_otrzymania_info_o_pozarze = 30     # w sekundach
    wiarygodnosc_bredzenia = 4
    aktualne_podejrzenia = 0
    awaria3_pomocnicza_tabela = [0, 0, 0, 0, 0]
    tresc_wiadomosci = '2'
    juz_jest_pozar = 0
    na_pewno = 0

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
                                              ['0', '0', '0', '0', '0'],
                                              ['0', '0', '0', '0', '0']]
    time_otrzymania_info_o_pozarze = [0, 0, 0, 0, 0]
    blink_queue = queue.Queue()
    threading.Thread(target=blink, args=(gpio_led, blink_queue)).start()

    klienci_tablica_otrzymanych_informacji[ktory_socket] = ['-', '-', '-', '-', '-']


    while True:
        #   Wysyłanie informacji o pozarze
        stan_czujnika = None
        awaria3 = 0

        if wlasna_tablica_otrzymanych_informacji[ktory_socket] != 'x':
            if GPIO.input(gpio_switch1) == GPIO.LOW:
                stan_czujnika = 1
                wlasna_tablica_otrzymanych_informacji[ktory_socket] = '1'
            else:
                stan_czujnika = 0
                wlasna_tablica_otrzymanych_informacji[ktory_socket] = '0'
                if GPIO.input(gpio_switch2) == GPIO.LOW:
                    awaria3 = 1
                else:
                    awaria3 = 0
        else:
            stan_czujnika = 'x'

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
                if awaria3 == 1:
                    if tresc_wiadomosci[0] == '1':
                        tmp = '1' + tresc_wiadomosci[1] + str(random.randint(0, 1))
                        tresc_wiadomosci = tmp
                message = f'{tresc_wiadomosci}'
                client_sock.sendto(message.encode(), client_address)
                client_sock.close()

        # Sprawdzanie kolejki na nowe wiadomości do wyświetlenia
        try:
            print(str(ktory_socket) + "---------------------------------------------")
            while not message_queue.empty():
                msg = message_queue.get_nowait()
                if debug_level >= 1:
                    print(msg)
                if wlasna_tablica_otrzymanych_informacji[int(msg[1])] != 'x' and wlasna_tablica_otrzymanych_informacji[ktory_socket] != 'x':
                    if msg[0] == '1':
                        if msg[2] == '1':
                            if time_otrzymania_info_o_pozarze[int(msg[1])] == 0:
                                time_otrzymania_info_o_pozarze[int(msg[1])] = time.time()
                                for i in range(len(time_otrzymania_info_o_pozarze)):
                                    if time_otrzymania_info_o_pozarze[i] != 0:
                                        time_otrzymania_info_o_pozarze[i] = time.time()
                            elif time_otrzymania_info_o_pozarze[int(msg[1])] + cooldown_otrzymania_info_o_pozarze < time.time() and juz_jest_pozar == 0:
                                #   AWARIA ze zbyt dlugim pozarem
                                print("Wykryto awarie nr 2 w czujniku nr " + msg[1])
                                wlasna_tablica_otrzymanych_informacji[int(msg[1])] = 'x'
                        elif time_otrzymania_info_o_pozarze[int(msg[1])] != 0:
                            time_otrzymania_info_o_pozarze[int(msg[1])] = 0

                        #   detekcja awarii nr 3
                        awaria3_pomocnicza_tabela[int(msg[1])] = 1
                        awaria3_pomocnicza_tabela[ktory_socket] = 1
                        ktory_to_nie_dziala = 0
                        if awaria3_pomocnicza_tabela[0] == 1 and awaria3_pomocnicza_tabela[1] == 1 and awaria3_pomocnicza_tabela[2] == 1 and awaria3_pomocnicza_tabela[3] == 1 and awaria3_pomocnicza_tabela[4] == 1:
                            zebrano_podejrzenia = 0
                            for i in range(5):
                                if i == ktory_socket:
                                    continue
                                for j in range(5):
                                    if wlasna_tablica_otrzymanych_informacji[j] != klienci_tablica_otrzymanych_informacji[i][j]:
                                        print(str(wlasna_tablica_otrzymanych_informacji[j]) + "!=" + str(klienci_tablica_otrzymanych_informacji[i][j]))
                                        print(aktualne_podejrzenia)
                                        awaria3_pomocnicza_tabela = [0, 0, 0, 0, 0]
                                        ktory_to_nie_dziala = j
                                        aktualne_podejrzenia += 1
                                        zebrano_podejrzenia = 1
                                        break
                                if zebrano_podejrzenia == 1:
                                    break
                            if zebrano_podejrzenia == 0:
                                aktualne_podejrzenia = 0
                            elif aktualne_podejrzenia >= wiarygodnosc_bredzenia:
                                aktualne_podejrzenia = 0
                                wlasna_tablica_otrzymanych_informacji[ktory_to_nie_dziala] = 'x'
                                print("wykryto awarie nr 3 w czujniku nr " + str(ktory_to_nie_dziala))

                        if wlasna_tablica_otrzymanych_informacji[int(msg[1])] != 'x':
                            if time_otrzymania_info_o_pozarze[int(msg[1])] != 0 and msg[2] == 0:
                                time_otrzymania_info_o_pozarze[int(msg[1])] = 0
                            wlasna_tablica_otrzymanych_informacji[int(msg[1])] = msg[2]
                            # weryfikacja czy jest pozar
                            ile_czujnikow_dziala = 0
                            ile_czujnikow_plonie = 0
                            for i in range(5):
                                if str(wlasna_tablica_otrzymanych_informacji[i]) != 'x':
                                    if str(wlasna_tablica_otrzymanych_informacji[i]) == '1':
                                        ile_czujnikow_plonie += 1
                                    ile_czujnikow_dziala += 1
                            if ile_czujnikow_plonie >= ile_czujnikow_dziala / 2:
                                blink_queue.put(1)
                                juz_jest_pozar = 1
                                print("jest juz pozar")
                            elif juz_jest_pozar == 1:
                                juz_jest_pozar = 0
                                for i in range(5):
                                    if time_otrzymania_info_o_pozarze[i] != 0:
                                        time_otrzymania_info_o_pozarze[i] = time.time()
                            else:
                                blink_queue.put(0)
                                juz_jest_pozar = 0
                                print("nie ma juz pozaru")
                    if msg[0] == '2':
                        klienci_tablica_otrzymanych_informacji[int(msg[1])][0] = msg[2]
                        klienci_tablica_otrzymanych_informacji[int(msg[1])][1] = msg[3]
                        klienci_tablica_otrzymanych_informacji[int(msg[1])][2] = msg[4]
                        klienci_tablica_otrzymanych_informacji[int(msg[1])][3] = msg[5]
                        klienci_tablica_otrzymanych_informacji[int(msg[1])][4] = msg[6]

                        ile_na_nie = 0
                        for i in range(5):
                            if i == ktory_socket:
                                continue
                            if klienci_tablica_otrzymanych_informacji[i][ktory_socket] == 'x':
                                ile_na_nie += 1
                        if ile_na_nie >= 4:
                            print("To ja nie dzialam :(")
                            wlasna_tablica_otrzymanych_informacji[ktory_socket] = 'x'

                        #   Obsluga bledu nr3
                        ktora_to_literka = 2 + ktory_socket
                        if msg[ktora_to_literka] == 'x' and wlasna_tablica_otrzymanych_informacji[int(msg[1])] != 'x':
                            blink_queue.put(2)
                        for i in range(5):
                            if i == ktory_socket:
                                continue
                            if wlasna_tablica_otrzymanych_informacji[i] != klienci_tablica_otrzymanych_informacji[int(msg[1])][i]:
                                na_pewno += 1
                                if na_pewno >= 10:
                                    wlasna_tablica_otrzymanych_informacji[i] = 'x'
                            else:
                                na_pewno = 0
                            if wlasna_tablica_otrzymanych_informacji[i] == 'x':
                                klienci_tablica_otrzymanych_informacji[i] = ['x', 'x', 'x', 'x', 'x']
                if debug_level >= 1:
                    print(wlasna_tablica_otrzymanych_informacji)

                if wlasna_tablica_otrzymanych_informacji[ktory_socket] == 'x':
                    blink_queue.put(2)

                print("klieci")
                print(klienci_tablica_otrzymanych_informacji[0])
                print(klienci_tablica_otrzymanych_informacji[1])
                print(klienci_tablica_otrzymanych_informacji[2])
                print(klienci_tablica_otrzymanych_informacji[3])
                print(klienci_tablica_otrzymanych_informacji[4])
                print("\n")
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
