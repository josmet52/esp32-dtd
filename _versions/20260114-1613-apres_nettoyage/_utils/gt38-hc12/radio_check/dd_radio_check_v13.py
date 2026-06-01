# dd_responder.py
# Réponse "fast-echo": on renvoie dès que LEN+PAYLOAD est reçu (sans attendre CHK/ETX)
# Matériel : ESP32-WROOM-32 (DD) + GT38 @ 9600 bps
# Broches DD : UART2  TX=17 -> GT38.RX, RX=16 <- GT38.TX, SET=4
# Version : 1.2.1 (fix inter-char timeout & race, echo garanti)

from machine import UART, Pin
from time import ticks_us, ticks_ms, ticks_diff, sleep_ms

# ======= Configuration matérielle =======
UART_IDX = 2
PIN_TX   = 17        # vers RX du GT38
PIN_RX   = 16        # depuis TX du GT38
PIN_SET  = 4         # SET du GT38 (haut = normal)
BAUD = 9600

# ======= Paramètres protocole =======
STX = 0x02
ETX = 0x03

# Fenêtres de réception
OVERALL_TIMEOUT_MS    = 1500   # garde-fou global par trame
INTERCHAR_TIMEOUT_MS  = 120    # délai max entre deux octets consécutifs

FRAMING_BITS_PER_BYTE = 10
PREAMBLE_BYTES = 0
RADIO_OVERHEAD_BYTES = 0

def estimate_on_air_ms(num_bytes, baud=BAUD):
    bits = (num_bytes + PREAMBLE_BYTES + RADIO_OVERHEAD_BYTES) * FRAMING_BITS_PER_BYTE
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
    timeout=50, timeout_char=2, rxbuf=2048
)

print("=== DD responder (FAST_ECHO, v1.2.1) ===")
print("UART{} @ {} bps, TX={}, RX={}, SET={}".format(UART_IDX, BAUD, PIN_TX, PIN_RX, PIN_SET))

ok_cnt = 0
err_cnt = 0

while True:
    # -------- Attendre STX --------
    t0 = ticks_ms()
    t_last = ticks_ms()
    t_first_us = None

    while True:
        if uart.any():
            b = uart.read(1)
            if b:
                if t_first_us is None:
                    t_first_us = ticks_us()
                if b[0] == STX:
                    break  # trouvé STX
                t_last = ticks_ms()
        else:
            # garde-fou global
            if ticks_diff(ticks_ms(), t0) > OVERALL_TIMEOUT_MS:
                # On repart à zéro pour une nouvelle trame
                t0 = ticks_ms()
                t_last = ticks_ms()
                t_first_us = None
            sleep_ms(1)

    # -------- Lire LEN --------
    # (petite attente si besoin, avec interchar timeout)
    while uart.any() == 0:
        if ticks_diff(ticks_ms(), t_last) > INTERCHAR_TIMEOUT_MS:
            err_cnt += 1
            print("DD ERR #{} | Timeout LEN".format(err_cnt))
            break
        sleep_ms(1)
    else:
        bl = uart.read(1)
        if not bl:
            err_cnt += 1
            print("DD ERR #{} | LEN manquant".format(err_cnt))
            continue
        length = bl[0]
        t_last = ticks_ms()

        # -------- Lire PAYLOAD (avec interchar timeout) --------
        payload = bytearray()
        while len(payload) < length:
            if uart.any():
                chunk = uart.read(length - len(payload))
                if chunk:
                    payload.extend(chunk)
                    t_last = ticks_ms()
            else:
                # inter-char timeout uniquement (pas de timeout global ici)
                if ticks_diff(ticks_ms(), t_last) > INTERCHAR_TIMEOUT_MS:
                    err_cnt += 1
                    print("DD ERR #{} | Timeout PAYLOAD (recu {}/{})".format(err_cnt, len(payload), length))
                    break
                sleep_ms(1)

        # Si on a bien reçu tout le payload, on répond IMMÉDIATEMENT
        if len(payload) == length:
            t_payload_complete_us = ticks_us()

            resp_payload = bytes(payload)
            resp_frame = build_frame(resp_payload)

            tx_start_us = ticks_us()
            uart.write(resp_frame)
            tx_end_call_us = ticks_us()
            tx_onair_ms = estimate_on_air_ms(len(resp_frame))

            ok_cnt += 1
            rx_first_to_payload_ms = (ticks_diff(t_payload_complete_us, t_first_us)) / 1000.0 if t_first_us else -1.0
            print("DD OK #{:d} | RX 1st→payload: {:6.2f} ms | TX call: {:6.2f} ms | TX on-air(est): {:6.2f} ms | resp_bytes: {}".format(
                ok_cnt,
                rx_first_to_payload_ms,
                (ticks_diff(tx_end_call_us, tx_start_us)) / 1000.0,
                tx_onair_ms,
                len(resp_frame)
            ))

            # -------- Lire CHK + ETX de la trame entrante, SANS bloquer la réponse --------
            # On laisse 2 petites fenêtres pour "nettoyer" si les octets arrivent vite.
            # CHK
            w = ticks_ms()
            while uart.any() == 0 and ticks_diff(ticks_ms(), w) < 30:
                sleep_ms(1)
            if uart.any():
                _ = uart.read(1)  # CHK

            # ETX
            w = ticks_ms()
            while uart.any() == 0 and ticks_diff(ticks_ms(), w) < 30:
                sleep_ms(1)
            if uart.any():
                _ = uart.read(1)  # ETX

            # Retour à l'attente d'une nouvelle trame
            continue

        # Sinon (payload incomplet), on retombe au début du while principal (attente nouvelle trame)
        # et on laisse les logs d'erreur ci-dessus pour diagnostic.
        # Pas d'echo car trame incomplète.
        continue
