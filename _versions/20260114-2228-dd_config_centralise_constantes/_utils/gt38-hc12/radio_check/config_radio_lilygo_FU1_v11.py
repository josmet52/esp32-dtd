# gt38_configurator.py — MicroPython (ESP32)
# Objectif: passer les GT-38 en FU3 (faible latence) @ 9600, vérifier canal
# Broches LilyGO T-Display-S3 AMOLED: TX=43, RX=44, SET=45

from machine import Pin, UART
from time import sleep_ms, ticks_ms, ticks_diff

UART_IDX = 1          # UART1 sur S3: TX=43, RX=44
PIN_TX   = 43
PIN_RX   = 44
PIN_SET  = 45
BAUD     = 9600

ENDINGS = [b"\r\n", b"\r", b"\n"]

def read_all(u, ms=200):
    t0 = ticks_ms()
    buf = b""
    while ticks_diff(ticks_ms(), t0) < ms:
        if u.any():
            buf += u.read()
        else:
            sleep_ms(5)
    return buf

def send_cmd(u, cmd):
    # essaie avec CRLF, puis CR, puis LF
    for e in ENDINGS:
        u.write(cmd + e)
        sleep_ms(120)
        resp = read_all(u, 300)
        if resp:
            print(cmd, "->", resp)
            return resp
    print(cmd, "->", b"(no response)")
    return b""

def enter_at_mode(uart):
    # SET bas, attendre >= 40ms, purger RX
    setp.value(0)
    sleep_ms(60)
    read_all(uart, 150)  # flush silent
    # test “AT”
    return send_cmd(uart, b"AT")

def leave_at_mode():
    setp.value(1)
    sleep_ms(60)

# --- init ---
setp = Pin(PIN_SET, Pin.OUT, value=1)   # normal
uart = UART(UART_IDX, baudrate=BAUD, tx=PIN_TX, rx=PIN_RX,
            bits=8, parity=None, stop=1, timeout=200, timeout_char=2, rxbuf=2048)

print("=== GT38 configurateur ===")
print("Basculer en mode AT…")
ok = enter_at_mode(uart)
if not ok:
    # Certains modules demandent d’entrer AT mode juste après power-on:
    # on tente une bascule/retour puis re-entrée
    leave_at_mode()
    sleep_ms(100)
    ok = enter_at_mode(uart)

# Lecture des paramètres actuels
send_cmd(uart, b"AT+RB")   # baud -> "OK+B9600" attendu
send_cmd(uart, b"AT+RF")   # mode FU -> "OK+FU3" attendu (FU1/FU2 = lent)
send_cmd(uart, b"AT+RC")   # canal -> "OK+RC100" par défaut

# Réglages recommandés pour faible latence:
# send_cmd(uart, b"AT+FU3")      # mode rapide (par défaut, mais on force)
# send_cmd(uart, b"AT+B9600")    # UART 9600 (garder identique sur TA & DD)
send_cmd(uart, b"AT+FU1")
send_cmd(uart, b"AT+B9600")

# (optionnel) régler la puissance & canal:
# send_cmd(uart, b"AT+P8")     # +20 dBm
# send_cmd(uart, b"AT+C100")   # canal 100 (par défaut), même canal sur les deux modules

# Vérification finale
send_cmd(uart, b"AT+RB")
send_cmd(uart, b"AT+RF")
send_cmd(uart, b"AT+RC")

print("Quitter AT…")
leave_at_mode()
print("Terminé. Remets ton script de mesure.")
