# ta_rx_probe.py — mesure des intervalles inter-octet sur RX (TA)
from machine import UART, Pin
from time import ticks_us, ticks_ms, ticks_diff, sleep_ms

UART_IDX=2; PIN_TX=43; PIN_RX=44; BAUD=9600
Pin(45, Pin.OUT, value=1)  # SET haut en dur si câblé
u = UART(UART_IDX, baudrate=BAUD, tx=PIN_TX, rx=PIN_RX,
         bits=8, parity=None, stop=1, timeout=50, timeout_char=2, rxbuf=2048)

print("=== RX interval probe ===")
while True:
    # collecte ~1 s
    t0 = ticks_ms(); last = None; gaps = []; nbytes = 0
    while ticks_diff(ticks_ms(), t0) < 1000:
        if u.any():
            b = u.read(1)
            if b:
                now = ticks_us(); nbytes += 1
                if last is not None:
                    gaps.append((now - last)/1000.0)
                last = now
        else:
            sleep_ms(1)
    if gaps:
        print("n={} | gaps ms  min={:.2f} avg={:.2f} max={:.2f}".format(
            nbytes, min(gaps), sum(gaps)/len(gaps), max(gaps)))
    else:
        print("aucun octet")
