# ta_latency_tester.py
# Mesure de latence TA -> DD -> TA avec GT38 @ 9600 bauds
# Auteur: vous ; Date: 2025-11-12 ; Version: 1.0.0

from machine import UART, Pin
from time import ticks_us, ticks_ms, ticks_diff
import urandom

# ========= Configuration matérielle =========
UART_IDX = 2
PIN_TX = 43        # vers RX du GT38
PIN_RX = 44        # depuis TX du GT38
PIN_SET = 45        # SET du GT38 (haut = mode normal)
BAUD = 9600
UART_TIMEOUT_MS = 100  # timeout lecture non bloquante

# ========= Paramètres protocole & test =========
MSG_LEN = 20                  # longueur du payload aléatoire (par défaut = 20)
EXCHANGE_PERIOD_MS = 500      # délai entre deux tests
READ_TIMEOUT_MS = 600        # timeout global de réception d'une trame
FRAMING_BITS_PER_BYTE = 10    # 8N1 => 1 start + 8 data + 1 stop
PREAMBLE_BYTES = 0            # si vous estimez un préambule radio
RADIO_OVERHEAD_BYTES = 0      # si le GT38 ajoute un overhead (mettre ici)
PRINT_HEX = False             # payload affiché en ASCII ou hex

STX = 0x02
ETX = 0x03

# ========= Utils =========
def profile_rx_intervals(uart, window_ms=600):
    from time import ticks_us, ticks_ms, ticks_diff
    t0 = ticks_ms()
    last = None
    gaps = []
    while ticks_diff(ticks_ms(), t0) < window_ms:
        if uart.any():
            b = uart.read(1)
            if b:
                now = ticks_us()
                if last is not None:
                    gaps.append((now - last)/1000.0)
                last = now
    if gaps:
        print("Intervalles RX (ms): min={:.1f}  avg={:.1f}  max={:.1f}  n={}".format(
            min(gaps), sum(gaps)/len(gaps), max(gaps), len(gaps)))
    else:
        print("Aucun octet pendant la fenêtre de profilage.")

def sniff_bytes(uart, ms=200):
    """Sniffe pendant ms et renvoie les octets lus (debug)."""
    t0 = ticks_ms()
    buf = bytearray()
    while ticks_diff(ticks_ms(), t0) < ms:
        if uart.any():
            buf.extend(uart.read())
    return bytes(buf)

def estimate_on_air_ms(num_bytes, baud=BAUD):
    """Estimation du temps on-air en ms pour UART 8N1 + overheads optionnels."""
    total_bytes = num_bytes + PREAMBLE_BYTES + RADIO_OVERHEAD_BYTES
    bits = total_bytes * FRAMING_BITS_PER_BYTE
    return (bits * 1000) // baud

def make_payload(n):
    # ASCII lisible (A–Z + 0–9)
    alphabet = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return bytes(alphabet[urandom.getrandbits(8) % len(alphabet)] for _ in range(n))

def checksum(b):
    # somme mod 256 des octets du payload
    s = 0
    for x in b:
        s = (s + x) & 0xFF
    return s

def build_frame(payload: bytes) -> bytes:
    ch = checksum(payload)
    return bytes([STX, len(payload)]) + payload + bytes([ch, ETX])

def parse_frame(uart, overall_timeout_ms=2000):
    """
    Parse 'streaming' d'une trame [0x02][LEN][PAYLOAD][CHK][0x03].
    Retourne (payload, t_first_us, t_end_us) ou (None, None, None).
    """
    from time import ticks_ms, ticks_us, ticks_diff, sleep_ms

    STX = 0x02
    ETX = 0x03

    t0 = ticks_ms()
    t_first_us = None
    buf = bytearray()

    def find_stx(b: bytearray) -> int:
        for k, v in enumerate(b):
            if v == STX:
                return k
        return -1

    while ticks_diff(ticks_ms(), t0) <= overall_timeout_ms:
        # lire tout ce qui est dispo
        if uart.any():
            chunk = uart.read()
            if chunk:
                if t_first_us is None:
                    t_first_us = ticks_us()
                buf.extend(chunk)

                # extraction tant que possible
                while True:
                    i = find_stx(buf)
                    if i < 0:
                        if len(buf) > 4:
                            del buf[:-4]
                        break

                    if len(buf) - i < 2:
                        # pas encore LEN
                        break

                    length = buf[i + 1]
                    frame_len = 1 + 1 + length + 1 + 1  # STX+LEN+PAYLOAD+CHK+ETX

                    if len(buf) - i < frame_len:
                        # pas encore la frame complète
                        if i > 0:
                            del buf[:i]
                        break

                    # frame candidate
                    frame = buf[i:i + frame_len]
                    del buf[:i + frame_len]

                    if frame[-1] != ETX:
                        continue

                    payload = frame[2:2 + length]
                    chk = frame[2 + length]

                    s = 0
                    for x in payload:
                        s = (s + x) & 0xFF
                    if chk != s:
                        continue

                    t_end_us = ticks_us()
                    return bytes(payload), t_first_us, t_end_us
        else:
            # laisse respirer l'interruption UART et le RTOS
            sleep_ms(1)

    return None, None, None

def bytes_visible(b):
    if PRINT_HEX:
        return b.hex()
    try:
        return b.decode()
    except:
        return b.hex()

# ========= Init matériel =========
_pin_set = Pin(PIN_SET, Pin.OUT, value=1)  # haut = mode normal GT38
# uart = UART(UART_IDX, baudrate=BAUD, tx=PIN_TX, rx=PIN_RX, timeout=UART_TIMEOUT_MS)
uart = UART(
    UART_IDX, baudrate=BAUD, tx=PIN_TX, rx=PIN_RX,
    bits=8, parity=None, stop=1,
    timeout=50,         # au lieu de 0 (non bloquant)
    timeout_char=2,
    rxbuf=2048
)

print("=== TA latency tester ===")
print("UART2 @ {} bps, TX={}, RX={}, SET={}".format(BAUD, PIN_TX, PIN_RX, PIN_SET))

f_pass = True
counter = 0
while True:
    counter += 1
    payload = make_payload(MSG_LEN)
    frame = build_frame(payload)

    # Purge tout éventuel résidu/echo avant d'attendre la réponse DD
    # (certains modules émettent un écho local ou laissent traîner des octets)
    while uart.any():
        uart.read()

    # ---- Emission ----
    tx_start_us = ticks_us()
    n = uart.write(frame)

    tx_end_call_us = ticks_us()  # fin de l'appel write()
    on_air_ms = estimate_on_air_ms(len(frame))
    tx_end_onair_us = tx_start_us + on_air_ms * 1000  # estimation fin réelle RF

    
    if f_pass:
        profile_rx_intervals(uart, window_ms=600)
        f_pass = False

    # ---- Réception de la réponse ----
    # On mesure: temps d'attente de la réponse = entre fin on-air estimée et 1er octet reçu
    resp, r_first_us, r_end_us = parse_frame(uart, READ_TIMEOUT_MS)

    # ---- Calculs TA ----
    tx_duration_call_ms = ticks_diff(tx_end_call_us, tx_start_us) / 1000.0
    tx_duration_onair_ms = on_air_ms

    if resp is not None:
        wait_resp_ms = max(0, (r_first_us - tx_end_onair_us) / 1000.0)
        rx_first_to_complete_ms = (ticks_diff(r_end_us, r_first_us)) / 1000.0
        rtt_ms = (ticks_diff(r_end_us, tx_start_us)) / 1000.0
        ok = True
    else:
        wait_resp_ms = None
        rx_first_to_complete_ms = None
        rtt_ms = None
        ok = False

    # ---- Log lisible ----
    print("---- TA ITER {:>5} ----".format(counter))
    print("TX len={} frame_bytes={}  payload={}".format(
        MSG_LEN, len(frame), bytes_visible(payload)))
    print("TX call   : {:6.2f} ms (debut->fin write)".format(tx_duration_call_ms))
    print("TX on-air : {:6.2f} ms (estimation 8N1 @ {} bps)".format(tx_duration_onair_ms, BAUD))

    if ok:
        print("RX first→full : {:6.2f} ms".format(rx_first_to_complete_ms))
        print("Attente réponse: {:6.2f} ms (fin TX on-air → 1er octet)".format(wait_resp_ms))
        print("RTT total     : {:6.2f} ms (tx_start → rx_full)".format(rtt_ms))
        print("Réponse OK    : len={}".format(len(resp)))
    else:
        # Sniff 200 ms pour voir si quelque chose tombe quand même
        junk = sniff_bytes(uart, 200)
        if junk:
            print("Réponse: INVALID (octets recus hors trame) :", junk.hex())
        else:
            print("Réponse:  (aucun octet)")

    # Petit spacing entre tests
    t0 = ticks_ms()
    while ticks_diff(ticks_ms(), t0) < EXCHANGE_PERIOD_MS:
        pass
