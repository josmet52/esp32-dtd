# dd_responder.py
# Réponse "fast-echo" : on renvoie dès que le PAYLOAD est reçu (sans attendre CHK/ETX)
# Matériel: ESP32-WROOM-32 (DD) + GT38 @ 9600 bps
# Broches par défaut DD: UART2  TX=17 (-> RX GT38), RX=16 (<- TX GT38), SET=4
# Date: 2025-11-12  |  Version: 1.1.0 (FAST_ECHO)

from machine import UART, Pin
from time import ticks_us, ticks_ms, ticks_diff, sleep_ms

# ======= Configuration matérielle =======
UART_IDX = 2
PIN_TX   = 17        # vers RX du GT38
PIN_RX   = 16        # depuis TX du GT38
PIN_SET  = 4         # SET du GT38 (haut = normal)
BAUD = 9600

# ======= Paramètres protocole =======
READ_TIMEOUT_MS = 1500
FRAMING_BITS_PER_BYTE = 10
PREAMBLE_BYTES = 0
RADIO_OVERHEAD_BYTES = 0

STX = 0x02
ETX = 0x03

# Active la réponse immédiate dès que le PAYLOAD est complet
FAST_ECHO = True

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

# ==== Init ====
Pin(PIN_SET, Pin.OUT, value=1)  # SET=1 -> mode transparent
uart = UART(
    UART_IDX, baudrate=BAUD, tx=PIN_TX, rx=PIN_RX,
    bits=8, parity=None, stop=1,
    timeout=0, timeout_char=2, rxbuf=2048
)

print("=== DD responder (FAST_ECHO) ===")
print("UART{} @ {} bps, TX={}, RX={}, SET={}".format(UART_IDX, BAUD, PIN_TX, PIN_RX, PIN_SET))

ok_cnt = 0
err_cnt = 0

while True:
    # -------- Parse de trame entrante --------
    start_ms = ticks_ms()
    saw_first = False
    t_first_us = None

    # 1) Attendre STX
    while True:
        if uart.any():
            b = uart.read(1)
            if not saw_first:
                t_first_us = ticks_us()   # 1er octet vu (souvent STX)
                saw_first = True
            if b and b[0] == STX:
                break
        if ticks_diff(ticks_ms(), start_ms) > READ_TIMEOUT_MS:
            # rien reçu -> boucle attente
            continue

    # 2) LEN
    while not uart.any():
        if ticks_diff(ticks_ms(), start_ms) > READ_TIMEOUT_MS:
            err_cnt += 1
            print("DD ERR #{} | Timeout LEN".format(err_cnt))
            break
    else:
        bl = uart.read(1)
        if not bl:
            err_cnt += 1
            print("DD ERR #{} | LEN manquant".format(err_cnt))
            continue
        length = bl[0]

        # 3) PAYLOAD
        payload = bytearray()
        while len(payload) < length:
            if uart.any():
                chunk = uart.read(length - len(payload))
                if chunk:
                    payload.extend(chunk)
            if ticks_diff(ticks_ms(), start_ms) > READ_TIMEOUT_MS:
                err_cnt += 1
                print("DD ERR #{} | Timeout PAYLOAD (recu {}/{})".format(err_cnt, len(payload), length))
                break
        else:
            # PAYLOAD complet
            t_payload_complete_us = ticks_us()

            # --- FAST ECHO: répondre tout de suite ---
            resp_payload = bytes(payload)
            resp_frame = build_frame(resp_payload)

            tx_start_us = ticks_us()
            uart.write(resp_frame)
            tx_end_call_us = ticks_us()
            tx_onair_ms = estimate_on_air_ms(len(resp_frame))

            # 4) Finir de consommer CHK + ETX (sans bloquer) pour propreté du flux
            #    On ne fait pas dépendre l'émission de leur bonne réception.
            t_frame_complete_us = None

            # Lire CHK (1 octet) si arrive vite
            t0 = ticks_ms()
            while ticks_diff(ticks_ms(), t0) < 50 and uart.any() == 0:
                pass
            if uart.any():
                _ = uart.read(1)  # CHK

            # Lire ETX (1 octet) si arrive vite
            t0 = ticks_ms()
            while ticks_diff(ticks_ms(), t0) < 50 and uart.any() == 0:
                pass
            if uart.any():
                _ = uart.read(1)  # ETX
                t_frame_complete_us = ticks_us()

            # ---- Logs/mesures DD ----
            ok_cnt += 1
            rx_first_to_payload_ms = (ticks_diff(t_payload_complete_us, t_first_us)) / 1000.0
            if t_frame_complete_us is not None:
                rx_first_to_frame_ms = (ticks_diff(t_frame_complete_us, t_first_us)) / 1000.0
            else:
                rx_first_to_frame_ms = None

            print("DD OK #{:d} | RX 1st→payload: {:6.2f} ms | RX 1st→frame: {} | TX call: {:6.2f} ms | TX on-air(est): {:6.2f} ms | resp_bytes: {}".format(
                ok_cnt,
                rx_first_to_payload_ms,
                ("{:6.2f} ms".format(rx_first_to_frame_ms) if rx_first_to_frame_ms is not None else "—"),
                (ticks_diff(tx_end_call_us, tx_start_us)) / 1000.0,
                tx_onair_ms,
                len(resp_frame)
            ))
            # Retour boucle principale (attente nouvelle trame)
            continue

    # Si on sort par un 'break' de timeout LEN, on relance la boucle
    # (rien à faire ici)
