# main.py
#
# Sniffer GT38 autonome avec timings en microsecondes :
# - démarre au boot
# - affiche une ligne par message
# - mesures microsecondes :
#     * durée_msg : 1er octet -> '\n'
#     * idle_before : temps entre fin du message précédent
#                     et début du message courant
#
from machine import UART, Pin
import time

# === Paramètres matériel ===
UART_INDEX    = 1
UART_TX_PIN   = 17
UART_RX_PIN   = 18
GT38_SET_PIN  = 43
BAUDRATE      = 9600
UART_TIMEOUT  = 10   # ms

def init_gt38():
    """Place le GT38 en mode transparent (normal mode)."""
    set_pin = Pin(GT38_SET_PIN, Pin.OUT)
    set_pin.value(1)   # Adapter selon ton module/câblage
    return set_pin

def init_uart():
    return UART(
        UART_INDEX,
        baudrate=BAUDRATE,
        bits=8,
        parity=None,
        stop=1,
        tx=Pin(UART_TX_PIN),
        rx=Pin(UART_RX_PIN),
        timeout=UART_TIMEOUT,
    )

def sniffer_loop(uart):
    buffer = bytearray()
    msg_start_us = None           # horodatage du 1er octet du message
    last_message_end_us = None    # fin du message précédent
    msg_id = 0

    print("=== GT38 Sniffer autonome (µs) ===")
    print("UART:", UART_INDEX, "TX:", UART_TX_PIN, "RX:", UART_RX_PIN, "BAUD:", BAUDRATE)
    print("Sniffer en écoute...\n")
    loop_time = time.ticks_us()

    while True:
        if uart.any():
            b = uart.read(1)
            now_us = time.ticks_us()

            if msg_start_us is None:
                # Début d’un nouveau message
                msg_start_us = now_us
                buffer = bytearray()
                msg_id += 1

                # Calcul du temps depuis le dernier message
                if last_message_end_us is not None:
                    idle_us = time.ticks_diff(msg_start_us, last_message_end_us)
                else:
                    idle_us = 0

            buffer.extend(b)

            if b == b'\n':
                # Fin du message
                duration_us = time.ticks_diff(now_us, msg_start_us)
                last_message_end_us = now_us

                # Convertir en texte affichable
#                 try:
                text = buffer.decode().rstrip()
#                 print(text)
                if text == "POLL:00" or  "SYNC" in text:
                    t_loop = time.ticks_diff(time.ticks_us(), loop_time)
                    print("-"*60)
                    print("Loop time : {}ms".format(int(t_loop/1000)))
                    print("-"*60)
                    loop_time = time.ticks_us()
                        
                    
#                 except:
#                     text = str(buffer)

                # Impression compacte *sur une seule ligne*
                print(f"{msg_id:05d} | recv={duration_us:7d} us | idle={idle_us:7d} us | {text}")

                # Reset pour message suivant
                msg_start_us = None
                buffer = bytearray()

        else:
            time.sleep_ms(1)

def main():
    init_gt38()
    uart = init_uart()
    sniffer_loop(uart)

main()
