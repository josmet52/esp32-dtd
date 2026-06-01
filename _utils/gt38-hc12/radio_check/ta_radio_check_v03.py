# ta_latency_tester.py
# Mesure de latence TA -> DD -> TA avec GT38 @ 9600 bauds
# Matériel: LilyGO T-Display-S3 AMOLED (ESP32-S3)
# Broches: TX=43, RX=44, SET=45
# Version: 1.3.0 (streaming sans 'del', purge AVANT émission, timeouts robustes)

from machine import UART, Pin
from time import ticks_us, ticks_ms, ticks_diff, sleep_ms
import urandom

# ========= Configuration matérielle =========
UART_IDX = 2
PIN_TX   = 43            # vers RX du GT38
PIN_RX   = 44            # depuis TX du GT38
PIN_SET  = 45            # SET du GT38 (haut = mode normal)
BAUD = 9600

# ========= Paramètres protocole & test =========
MSG_LEN = 1
EXCHANGE_PERIOD_MS = 1200
READ_TIMEOUT_MS = 2500           # fenêtre globale de parse (streaming)
FRAMING_BITS_PER_BYTE = 10       # 8N1
PREAMBLE_BYTES = 0
RADIO_OVERHEAD_BYTES = 0
PRINT_HEX = False

STX = 0x02
ETX = 0x03

# ========= Utils =========
def estimate_on_air_ms(num_bytes, baud=BAUD):
    bits = (num_bytes + PREAMBLE_BYTES + RADIO_OVERHEAD_BYTES) * FRAMING_BITS_PER_BYTE
    return (bits * 1000) // baud

def make_payload(n):
    alphabet = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return bytes(alphabet[urandom.getrandbits(8) % len(alphabet)] for _ in range(n))

def checksum(b):
    s = 0
    for x in b:
        s = (s + x) & 0xFF
    return s

def build_frame(payload: bytes) -> bytes:
    ch = checksum(payload)
    return bytes([STX, len(payload)]) + payload + bytes([ch, ETX])

def bytes_visible(b):
    if PRINT_HEX:
        return b.hex()
    try:
        return b.decode()
    except:
        return b.hex()

# ========= Parseur streaming (sans 'del') =========
def parse_frame(uart, overall_timeout_ms=READ_TIMEOUT_MS):
    """
    Assemble une trame [0x02][LEN][PAYLOAD][CHK][0x03] depuis le flux UART.
    Retourne (payload, t_first_us, t_end_us) ou (None, None, None).
    Implémentation sans 'del' : on avance un pointeur 'ptr' et on compacte le buffer périodiquement.
    """
    t0 = ticks_ms()
    t_first_us = None
    buf = bytearray()
    ptr = 0  # pointeur de lecture dans buf

    while ticks_diff(ticks_ms(), t0) <= overall_timeout_ms:
        # Lire tout ce qui est disponible
        if uart.any():
            chunk = uart.read()
            if chunk:
                if t_first_us is None:
                    t_first_us = ticks_us()
                buf.extend(chunk)

                # Tenter d'extraire des frames tant que possible
                while True:
                    # Avancer jusqu'à STX
                    n = len(buf)
                    while ptr < n and buf[ptr] != STX:
                        ptr += 1
                    if ptr >= n:
                        # rien à parser pour l'instant
                        break

                    # Besoin au moins de STX+LEN
                    if n - ptr < 2:
                        break

                    length = buf[ptr + 1]
                    frame_len = 1 + 1 + length + 1 + 1  # STX + LEN + PAYLOAD + CHK + ETX

                    # Attendre la frame complète
                    n = len(buf)
                    if n - ptr < frame_len:
                        break

                    # Frame candidate via memoryview (pas de copie)
                    mv = memoryview(buf)[ptr:ptr + frame_len]

                    # Vérifs ETX et checksum
                    if mv[-1] != ETX:
                        # faux STX -> on saute d'un octet et on réessaie
                        ptr += 1
                        continue

                    payload_mv = mv[2:2 + length]
                    chk = mv[2 + length]

                    s = 0
                    for x in payload_mv:
                        s = (s + x) & 0xFF
                    if chk != s:
                        # mauvais CHK -> avancer d'un octet
                        ptr += 1
                        continue

                    # OK — on extrait la payload
                    payload = bytes(payload_mv)
                    t_end_us = ticks_us()

                    # Avancer ptr au-delà de la frame
                    ptr += frame_len

                    # Compacter le buffer si le pointeur a trop avancé
                    # (on garde la "queue" restante)
                    if ptr > 512 or ptr > len(buf) // 2:
                        buf = buf[ptr:]
                        ptr = 0

                    return payload, t_first_us, t_end_us

                # Fin d'extraction; si le pointeur est trop loin, compacter
                if ptr > 512 or ptr > len(buf) // 2:
                    buf = buf[ptr:]
                    ptr = 0
        else:
            # Laisser respirer l'ISR UART
            sleep_ms(1)

    return None, None, None

# ========= Init matériel =========
Pin(PIN_SET, Pin.OUT, value=1)  # SET haut = mode normal
uart = UART(
    UART_IDX,
    baudrate=BAUD,
    tx=PIN_TX,
    rx=PIN_RX,
    bits=8, parity=None, stop=1,
    timeout=50,          # légèrement bloquant
    timeout_char=2,
    rxbuf=2048
)

print("=== TA latency tester ===")
print("UART{} @ {} bps, TX={}, RX={}, SET={}".format(UART_IDX, BAUD, PIN_TX, PIN_RX, PIN_SET))

counter = 0
while True:
    counter += 1
    payload = make_payload(MSG_LEN)
    frame = build_frame(payload)

    # ---- Purge AVANT émission (et seulement ici) ----
    while uart.any():
        uart.read()

    # ---- Emission ----
    tx_start_us = ticks_us()
    uart.write(frame)
    tx_end_call_us = ticks_us()

    on_air_ms = estimate_on_air_ms(len(frame))
    tx_end_onair_us = tx_start_us + on_air_ms * 1000  # estimation fin RF

    # Petit délai pour laisser le module repasser proprement côté RX si besoin
    sleep_ms(10)

    # ---- Réception de la réponse ----
    resp, r_first_us, r_end_us = parse_frame(uart, READ_TIMEOUT_MS)

    # ---- Calculs TA ----
    tx_duration_call_ms = ticks_diff(tx_end_call_us, tx_start_us) / 1000.0
    tx_duration_onair_ms = on_air_ms

    print("---- TA ITER {:>5} ----".format(counter))
    print("TX len={} frame_bytes={}  payload={}".format(
        MSG_LEN, len(frame), bytes_visible(payload)))
    print("TX call   : {:6.2f} ms (debut->fin write)".format(tx_duration_call_ms))
    print("TX on-air : {:6.2f} ms (estimation 8N1 @ {} bps)".format(tx_duration_onair_ms, BAUD))

    if resp is not None:
        wait_resp_ms = max(0, (r_first_us - tx_end_onair_us) / 1000.0)
        rx_first_to_complete_ms = (ticks_diff(r_end_us, r_first_us)) / 1000.0
        rtt_ms = (ticks_diff(r_end_us, tx_start_us)) / 1000.0

        print("RX first→full : {:6.2f} ms".format(rx_first_to_complete_ms))
        print("Attente réponse: {:6.2f} ms (fin TX on-air → 1er octet)".format(wait_resp_ms))
        print("RTT total     : {:6.2f} ms (tx_start → rx_full)".format(rtt_ms))
        print("Réponse OK    : len={}".format(len(resp)))
    else:
        print("Réponse: TIMEOUT (aucun octet)")

    # ---- Période entre tests ----
    t0 = ticks_ms()
    while ticks_diff(ticks_ms(), t0) < EXCHANGE_PERIOD_MS:
        pass
