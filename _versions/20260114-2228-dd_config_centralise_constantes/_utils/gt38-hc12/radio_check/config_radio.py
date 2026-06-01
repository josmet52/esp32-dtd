# config_gt38.py — à lancer une fois par module (TA puis DD)
from machine import UART, Pin
from time import sleep_ms

UART_IDX = 2
PIN_TX = 17
PIN_RX = 16
PIN_SET = 4
BAUD = 9600

def send_cmd(u, cmd, wait=200):
    u.write(cmd + b'\r\n')
    sleep_ms(wait)
    resp = b""
    while u.any():
        resp += u.read()
    print(cmd, "->", resp)

# -- 1) Mode configuration --
set_pin = Pin(PIN_SET, Pin.OUT)
set_pin.value(0)   # SET bas = config
sleep_ms(50)

uart = UART(UART_IDX, baudrate=BAUD, tx=PIN_TX, rx=PIN_RX, timeout=200)

# -- 2) Quelques commandes "classiques" type HC-12 (à adapter si GT38 diffère) --
# Vérifier la présence
send_cmd(uart, b"AT")           # doit répondre "OK"

# Mode rapide (faible latence) — pour HC-12 ce serait FU3
send_cmd(uart, b"AT+FU3")

# Débit UART (garde 9600 si tu veux)
send_cmd(uart, b"AT+B9600")

# Puissance (si dispo)
# send_cmd(uart, b"AT+P8")

# Canal (si besoin)
# send_cmd(uart, b"AT+C001")

# Air data rate rapide (si commandes spécifiques GT38 existent, remplacer ici)
# send_cmd(uart, b"AT+DRx")  # <— placeholder, se référer à la doc de ton GT38

# -- 3) Quitter config --
set_pin.value(1)   # SET haut = normal
sleep_ms(50)
print("Config terminée. Remets tes scripts de test.")
