"""
dd_main.py v6.0.0 - Chargeur dynamique selon mode NVS
Date: 26.12.2025

Charge le module approprié selon la configuration NVS:
- Mode ESP-NOW → dd_main_espnow.py
- Mode 433MHz → dd_main_433.py

Le mode est défini:
- Automatiquement par le TA (commande MODE:XXX)
- Manuellement via REPL (dd_nvs_config.quick_set_mode())

Synchronisation automatique:
- TA envoie "MODE:ESPNOW" ou "MODE:433MHZ" avant de changer
- DD reçoit, change son mode NVS, reboot
- TA change son mode, reboot
- Tous en sync automatiquement ✅
"""

print("\n=== DD MAIN LOADER v6.0.0 ===")

# Import NVS config
try:
    from dd_nvs_config import DDNVSConfig, RADIO_MODE_ESPNOW, RADIO_MODE_433
except ImportError:
    print("[ERREUR] dd_nvs_config.py non trouvé!")
    print("[ERREUR] Impossible de déterminer le mode radio")
    import time
    time.sleep(5)
    import machine
    machine.reset()

# Lire le mode depuis NVS
mode = DDNVSConfig.get_radio_mode()

print("="*50)
print("MODE RADIO: {}".format(DDNVSConfig.get_mode_name(mode)))
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
        print("[ERREUR] Renommez l'ancien dd_main.py en dd_main_espnow.py")
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