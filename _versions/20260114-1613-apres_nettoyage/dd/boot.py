"""
project : DTD
Component : DD
file: dd_boot.py
author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-dtd
v1.0.0 : 13.01.2026
"""

__version__ = "1.0.0"

from machine import UART, Pin
import time

print("\n=== BOOT v{} ===".format(__version__))

# ================================================================
# CONFIGURATION HARDWARE - WROVER-T7
# ================================================================
import dd_nvs_utils as nvs_utils

# LilyGo T7 v1.5 : Module avec batterie et LEDs
UART_TX_PIN = 18
UART_RX_PIN = 23
BIT0_PIN = 27
BIT1_PIN = 25
BIT2_PIN = 32

print("[BOOT] Module: WROVER-T7")

# ================================================================
# LECTURE DD_ID (Hardware Straps)
# ================================================================
def read_dd_id():
    """
    Lit l'ID hardware du DD via les straps (0-7)
    
    Les pins BIT0, BIT1, BIT2 sont configurées en pull-up interne.
    Un strap fermé (connecté à GND) donne 0, un strap ouvert donne 1.
    
    Exemple:
        Straps: BIT2=OUVERT, BIT1=FERMÉ, BIT0=FERMÉ
        Binaire: 0 1 1 = Décimal: 3
        → DD_ID = 3
    
    Returns:
        int: ID du DD (0-7)
    """
    p0 = Pin(BIT0_PIN, Pin.IN, Pin.PULL_UP)
    p1 = Pin(BIT1_PIN, Pin.IN, Pin.PULL_UP)
    p2 = Pin(BIT2_PIN, Pin.IN, Pin.PULL_UP)
    
    # Lecture des pins (0 si strap ferme, 1 si ouvert)
    bit0 = 0 if p0.value() == 0 else 1
    bit1 = 0 if p1.value() == 0 else 1
    bit2 = 0 if p2.value() == 0 else 1
    
    # Calcul de l'ID (bit2 bit1 bit0 en binaire)
    return (bit2 << 2) | (bit1 << 1) | bit0

# Lecture de l'ID materiel
DD_ID = read_dd_id()

# ================================================================
# CHECK FLAG OTA
# ================================================================
# Le flag OTA est un int32 en NVS:
#   0 = mode normal (demarrage dd_main.py)
#   1 = mode OTA (demarrage ota_mode.py)
OTA_FLAG = nvs_utils.get_i32("DTD", "ota_mode", default=0)

if OTA_FLAG == 1:
    # ============================================================
    # MODE OTA - Mise a jour sans fil
    # ============================================================
    print("DD{:02d}".format(DD_ID))
    print(">>> OTA MODE (from NVS flag) <<<")
    
    # Garbage collect avant OTA pour maximiser la memoire disponible
    import gc
    gc.collect()
    
    # Lancer OTA directement (memoire propre, pas de fragmentation)
    try:
        from ota_mode import enter_ota_mode
        
        # IMPORTANT: Le flag sera efface par ota_mode.py a la fin
        # Ceci garantit que le flag n'est efface que si OTA se termine normalement
        enter_ota_mode(DD_ID)
        
        # Ne devrait jamais arriver ici (enter_ota_mode ne retourne pas)
        
    except Exception as e:
        # En cas d'erreur pendant le mode OTA
        print("[BOOT] ERREUR OTA:", e)
        import sys
        sys.print_exception(e)
        
        # Effacer le flag pour eviter une boucle de reboot
        print("[BOOT] Effacement flag OTA...")
        nvs_utils.set_i32("DTD", "ota_mode", 0)
        
        # Redemarrer en mode normal
        print("[BOOT] Reboot en mode NORMAL...")
        time.sleep(2)
        import machine
        machine.reset()
        
    # Ne revient jamais ici en fonctionnement normal

# ================================================================
# MODE NORMAL - Lancement du programme principal
# ================================================================
# Si on arrive ici, c'est que OTA_FLAG == 0
# Le programme principal (dd_main.py) demarre automatiquement

import dd_main