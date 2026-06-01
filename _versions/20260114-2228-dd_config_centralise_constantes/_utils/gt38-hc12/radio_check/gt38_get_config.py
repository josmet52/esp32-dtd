"""
Configuration GT38 pour DTD - Mode FU3 (9600 bauds)
"""
from machine import UART, Pin
import time


def configure_gt38_dtd():
    print("=== CONFIGURATION GT38 POUR DTD ===\n")

    pin_set = Pin(45, Pin.OUT)
    uart = UART(2, baudrate=9600, tx=43, rx=44, timeout=200)

    # Mode CONFIG
    print("1. Mode CONFIG (SET=LOW)")
    pin_set.value(0)
    time.sleep(1)

    # Vider buffer
    while uart.any():
        uart.read(uart.any())

    # Test connexion
    print("\n2. Test connexion")
    uart.write(b'AT\r\n')
    time.sleep_ms(300)

    if uart.any():
        resp = uart.read(uart.any())
        print("   ✓ Module répond: {}".format(resp))
    else:
        print("   ✗ Pas de réponse")
        return False

    # Configuration actuelle
    print("\n3. Configuration actuelle")
    while uart.any():
        uart.read(uart.any())

    uart.write(b'AT+RX\r\n')
    time.sleep_ms(300)

    if uart.any():
        resp = uart.read(uart.any())
        print("   {}".format(resp.decode('utf-8', 'ignore')))

    # Nouvelle configuration
    print("\n4. Configuration pour DTD")

    configs = [
        (b'AT+C001\r\n', "Canal 001"),
        (b'AT+P8\r\n', "Puissance max (8)"),
        (b'AT+FU3\r\n', "Mode FU3 (9600 bauds transparent)"),
    ]

    for cmd, desc in configs:
        while uart.any():
            uart.read(uart.any())

        print("   {}...".format(desc))
        uart.write(cmd)
        time.sleep_ms(300)

        if uart.any():
            resp = uart.read(uart.any())
            resp_str = resp.decode('utf-8', 'ignore').strip()
            if 'OK' in resp_str:
                print("      ✓ {}".format(resp_str))
            else:
                print("      ? {}".format(resp_str))
        else:
            print("      ✗ Pas de réponse")

    # Vérification
    print("\n5. Vérification configuration")
    while uart.any():
        uart.read(uart.any())

    uart.write(b'AT+RX\r\n')
    time.sleep_ms(300)

    if uart.any():
        resp = uart.read(uart.any())
        print("   {}".format(resp.decode('utf-8', 'ignore')))

    # Mode RUN
    print("\n6. Passage en mode RUN (SET=HIGH)")
    pin_set.value(1)
    time.sleep(1)

    print("\n" + "="*60)
    print("✓✓ CONFIGURATION TERMINÉE")
    print("="*60)
    print("\nLe GT38 est maintenant configuré:")
    print("  - Canal: 001")
    print("  - Puissance: Max (+20dBm)")
    print("  - Mode: FU3 (transparent, 9600 bauds)")
    print("\nVous pouvez maintenant utiliser DTD en mode réel !")

    return True


# Lancer la configuration
if configure_gt38_dtd():
    print("\n🎉 SUCCÈS !")
else:
    print("\n❌ ÉCHEC")
