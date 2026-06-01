# dd_responder.py
# Réponse écho + mesures, destiné au poste distant (DD) avec GT38
# Auteur: vous ; Date: 2025-11-12 ; Version: 1.0.0

from machine import UART, Pin
from time import ticks_us, ticks_ms, ticks_diff, sleep_ms

# ========= Configuration matérielle =========
UART_IDX = 2
PIN_TX = 17        # vers RX du GT38
PIN_RX = 16        # depuis TX du GT38  (adapter selon câblage)
PIN_SET = 4        # SET du GT38 (haut = normal)
BAUD = 9600
UART_TIMEOUT_MS = 100

# ========= Paramètres protocole =========
READ_TIMEOUT_MS = 1500
FRAMING_BITS_PER_BYTE = 10
PREAMBLE_BYTES = 0
RADIO_OVERHEAD_BYTES = 0

STX = 0x02
ETX = 0x03

def estimate_on_air_ms(num_bytes, baud=BAUD):
    total_bytes = num_bytes + PREAMBLE_BYTES + RADIO_OVERHEAD_BYTES
    bits = total_bytes * FRAMING_BITS_PER_BYTE
    return (bits * 1000) // baud

def checksum(b):
    s = 0
    for x in b:
        s = (s + x) & 0xFF
    return s

def build_frame(payload: bytes) -> bytes:
    ch = checksum(payload)
    return bytes([STX, len(payload)]) + payload + bytes([ch, ETX])

def parse_frame(uart, overall_timeout_ms=READ_TIMEOUT_MS):
    """Retourne (payload, t_first_us, t_end_us) ou (None, None, None)."""
    start_ms = ticks_ms()
    saw_first = False
    t_first_us = None

    # Attente STX
    while True:
        if uart.any():
            b = uart.read(1)
            if not saw_first:
                t_first_us = ticks_us()
                saw_first = True
            if b and b[0] == STX:
                break
        if ticks_diff(ticks_ms(), start_ms) > overall_timeout_ms:
            return None, None, None

    # LEN
    while not uart.any():
        if ticks_diff(ticks_ms(), start_ms) > overall_timeout_ms:
            return None, None, None
    bl = uart.read(1)
    if not bl:
        return None, None, None
    length = bl[0]

    # PAYLOAD
    payload = bytearray()
    while len(payload) < length:
        if uart.any():
            chunk = uart.read(length - len(payload))
            if chunk:
                payload.extend(chunk)
        if ticks_diff(ticks_ms(), start_ms) > overall_timeout_ms:
            return None, None, None

    # CHK
    while not uart.any():
        if ticks_diff(ticks_ms(), start_ms) > overall_timeout_ms:
            return None, None, None
    bchk = uart.read(1)
    if not bchk:
        return None, None, None

    # ETX
    while not uart.any():
        if ticks_diff(ticks_ms(), start_ms) > overall_timeout_ms:
            return None, None, None
    betx = uart.read(1)
    t_end_us = ticks_us()

    if not betx or betx[0] != ETX:
        return None, None, None
    if bchk[0] != checksum(payload):
        return None, None, None

    return bytes(payload), t_first_us, t_end_us

# ========= Init =========
Pin(PIN_SET, Pin.OUT, value=1)
uart = UART(UART_IDX, baudrate=BAUD, tx=PIN_TX, rx=PIN_RX, timeout=UART_TIMEOUT_MS)

print("=== DD responder ===")
print("UART2 @ {} bps, TX={}, RX={}, SET={}".format(BAUD, PIN_TX, PIN_RX, PIN_SET))

ok_cnt = 0
err_cnt = 0
while True:
    # Réception
    pl, r_first_us, r_end_us = parse_frame(uart, READ_TIMEOUT_MS)
    if pl is None:
        # Pas de trame (ou invalide) -> on boucle
        continue

    rx_first_to_full_ms = (ticks_diff(r_end_us, r_first_us)) / 1000.0

    # Prépare la réponse (écho)
    resp_payload = pl  # on renvoie le même payload
    resp_frame = build_frame(resp_payload)

    # Emission
    tx_start_us = ticks_us()

    # Petit délai pour le retournement RF sur certains modules (TX->RX)
    sleep_ms(15)
    uart.write(resp_frame)

    uart.write(resp_frame)
    tx_end_call_us = ticks_us()
    tx_onair_ms = estimate_on_air_ms(len(resp_frame))

    # Stats/log
    ok_cnt += 1
    print("DD OK #{:d} | RX 1st→full: {:6.2f} ms | TX call: {:6.2f} ms | TX on-air(est): {:6.2f} ms | resp_bytes: {}".format(
        ok_cnt, rx_first_to_full_ms, (ticks_diff(tx_end_call_us, tx_start_us))/1000.0, tx_onair_ms, len(resp_frame)
    ))
