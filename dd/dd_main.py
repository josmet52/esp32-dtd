"""
project : DTD
Component : DD
file: dd_main.py
author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-dtd
v1.0.0 : 13.01.2026
"""

print("\n=== DD MAIN LOADER v1.0.0 ===")

# Import configuration
try:
    from dd_config import get_radio_mode, get_mode_name, RADIO_MODE_ESPNOW, RADIO_MODE_433
except ImportError:
    print("[ERREUR] dd_config.py non trouvé!")
    print("[ERREUR] Impossible de déterminer le mode radio")
    import time
    time.sleep(5)
    import machine
    machine.reset()

# Lire le mode depuis NVS
mode = get_radio_mode()

print("="*50)
print("MODE RADIO: {}".format(get_mode_name(mode)))
print("="*50)

# Charger le module approprie
if mode == RADIO_MODE_ESPNOW:
    print("[LOADER] Chargement: dd_main_espnow")
    try:
        import dd_main_espnow
        # Le module se lance automatiquement (AUTO_START=True)
    except ImportError as e:
        print("[ERREUR] dd_main_espnow.py non trouvé!")
        print("[ERREUR] Détails: {}".format(e))
        import time
        time.sleep(5)
        import machine
        machine.reset()

elif mode == RADIO_MODE_433:
    print("[LOADER] Chargement: dd_main_433")
    try:
        import dd_main_433
        # Le module se lance automatiquement (AUTO_START=True)
    except ImportError as e:
        print("[ERREUR] dd_main_433.py non trouvé!")
        print("[ERREUR] Détails: {}".format(e))
        import time
        time.sleep(5)
        import machine
        machine.reset()

else:
    print("[ERREUR] Mode radio invalide: {}".format(mode))
    print("[ERREUR] Fallback sur ESP-NOW")
    try:
        import dd_main_espnow
    except ImportError:
        print("[ERREUR CRITIQUE] Aucun module DD disponible!")
        import time
        time.sleep(10)
        import machine
        machine.reset()