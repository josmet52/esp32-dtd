"""
boot.py v1.2.1 - Séquence de boot DD
Gestion du démarrage et détection du mode OTA

Responsabilités:
- Validation de la configuration matérielle (MODULE_TYPE)
- Lecture de l'ID matériel via straps (0-7)
- Détection du flag OTA en NVS
- Lancement du mode approprié (normal ou OTA)
- Gestion des erreurs de démarrage OTA

IMPORTANT: En mode OTA, le flag NVS est effacé par ota_mode.py à la fin

Changelog:
v1.2.1:
- Déplacement de l'effacement du flag OTA APRÈS le lancement réussi
- Note: ota_mode.py doit maintenant effacer le flag à la fin
- Gestion d'erreur: effacement flag OTA en cas d'échec du mode OTA

v1.2.0:
- Refactorisation: élimination duplication définition pins
- Validation stricte MODULE_TYPE avec gestion d'erreur robuste

v1.1.0:
- Effacement du flag OTA IMMÉDIATEMENT pour éviter boucle de reboot

v1.0.9:
- Check flag OTA en NVS pour éviter fragmentation mémoire WROOM-32
"""

__version__ = "1.2.1"

from machine import UART, Pin
import time

print("\n=== BOOT v{} ===".format(__version__))

# ================================================================
# CONFIGURATION HARDWARE SELON MODULE_TYPE
# ================================================================
import utils.nvs_utils as nvs_utils

# Lecture du type de module depuis NVS
MODULE_TYPE = nvs_utils.get_str("DTD", "DD-type", default="UNKNOWN")

# Validation stricte MODULE_TYPE
if MODULE_TYPE not in ["WROOM-32", "WROVER-T7"]:
    print("[ERREUR CRITIQUE] MODULE_TYPE invalide: '{}'".format(MODULE_TYPE))
    print("[ERREUR] Valeurs acceptées: 'WROOM-32' ou 'WROVER-T7'")
    print("[ERREUR] Vérifiez la configuration NVS (namespace='DTD', key='DD-type')")
    print("[ERREUR] Utilisez set_module_type_and_bat_cal.py pour configurer")
    print("[ERREUR] Arrêt du système...")
    raise SystemExit()

# Configuration des pins selon le type de module
if MODULE_TYPE == "WROOM-32":
    # ESP32-WROOM-32 : Module standard sans batterie
    UART_TX_PIN = 17
    UART_RX_PIN = 16
    BIT0_PIN = 18
    BIT1_PIN = 19
    BIT2_PIN = 21
    
elif MODULE_TYPE == "WROVER-T7":
    # LilyGo T7 v1.5 : Module avec batterie et LEDs
    UART_TX_PIN = 18
    UART_RX_PIN = 23
    BIT0_PIN = 27
    BIT1_PIN = 25
    BIT2_PIN = 32

print("[BOOT] Module: {}".format(MODULE_TYPE))

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
# CHECK FLAG OTA (Avant tous les autres imports)
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
# grace a AUTO_START = True

import dd_main