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
CONFIG = {
    "PIN_TX"   : 43,    # GPIO TX_PIN -> GT38 RX_PIN
    "PIN_RX"   : 44,    # GPIO RX_PIN -> GT38 TX_PIN
    "PIN_SET"  : 45,    # GPIO SET_PIN -> GT38 SET_PIN
    "BAUD_RATE" : "9600", # 1200, 9600, 19200, 38400
    "FU_MODE" : "3",      # FU3 = transparent
    "CHANNEL" : "001",    # 001 ... 127 <--> 433 ... 473 Mhz
    "POWER" : "8",        # 1 ... 8 <-> -1, 2, 5, 8, 11, 14, 17, 20 dbm
    "UART_FORMAT" : "8N1", # 8 bits, parité None, 1 stop bit
    "UART_IDX" : 1,     # UART1 sur S3 AMOLED 
    }
UART_IDX = CONFIG["UART_IDX"]          # UART1 sur S3: TX=43, RX=44
PIN_TX   = CONFIG["PIN_TX"] # 43
PIN_RX   = CONFIG["PIN_RX"] # 44
PIN_SET  = CONFIG["PIN_SET"] # 45
BAUD     = 9600


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
print("-"*60)
print("Basculer en mode AT…")
ok = enter_at_mode(uart)
if not ok:
    # Certains modules demandent d’entrer AT mode juste après power-on:
    # on tente une bascule/retour puis re-entrée
    leave_at_mode()
    sleep_ms(100)
    ok = enter_at_mode(uart)

print("-"*60)
print("Etat initial")
# Lecture des paramètres actuels
send_cmd(uart, b"AT+RB")   # baud -> "OK+B9600" attendu
send_cmd(uart, b"AT+RF")   # mode FU -> "OK+FU3" attendu (FU1/FU2 = lent)
send_cmd(uart, b"AT+RC")   # canal -> "OK+RC100" par défaut
send_cmd(uart, b"AT+RP")   # canal -> "OK+RC100" par défaut
print("-"*60)

print("Appliquer nouveaux réglages")
# Réglages recommandés pour faible latence:
send_cmd(uart, b"AT+FU{}".format(CONFIG["FU_MODE"]))      # mode rapide (par défaut, mais on force)
send_cmd(uart, b"AT+B{}".format(CONFIG["BAUD_RATE"]))    # UART 9600 (garder identique sur TA & DD)
send_cmd(uart, b"AT+P{}".format(CONFIG["POWER"]))     # +20 dBm
send_cmd(uart, b"AT+C{}".format(CONFIG["CHANNEL"]))   # canal 100 (par défaut), même canal sur les deux modules
send_cmd(uart, b"AT+U{}".format(CONFIG["UART_FORMAT"]))   # canal 100 (par défaut), même canal sur les deux modules

print("-"*60)
print("Etat final")
send_cmd(uart, b"AT+RB")   # baud -> "OK+B9600" attendu
send_cmd(uart, b"AT+RF")   # mode FU -> "OK+FU3" attendu (FU1/FU2 = lent)
send_cmd(uart, b"AT+RC")   # canal -> "OK+RC100" par défaut
send_cmd(uart, b"AT+RP")   # canal -> "OK+RC100" par défaut
print("-"*60)
send_cmd(uart, b"AT+V")     # +20 dBm
print("-"*60 + "\n")

# Vérification finale
# send_cmd(uart, b"AT+RB")
# send_cmd(uart, b"AT+RF")
# send_cmd(uart, b"AT+RC")

print("Quitter AT…")
leave_at_mode()
print("Terminé")
