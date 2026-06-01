"""
config_ta_mac.py - Configuration du MAC du Terminal Admin

À exécuter UNE FOIS sur chaque DD pour configurer le MAC du TA.

Usage:
1. Sur le TA, récupérer son MAC avec:
   >>> import network
   >>> sta = network.WLAN(network.STA_IF)
   >>> sta.active(True)
   >>> ':'.join('{:02X}'.format(b) for b in sta.config('mac'))

2. Sur chaque DD, modifier TA_MAC ci-dessous puis exécuter ce script
"""

import utils.nvs_utils as nvs_utils

# ====== CONFIGURATION ======
# Remplacer par le vrai MAC du TA
TA_MAC = "24:58:7C:D1:B5:CC" # "80:65:99:A0:4E:EC"
# ===========================

print("Configuration MAC du Terminal Admin")
print("MAC du TA: {}".format(TA_MAC))

# Stocker en NVS
nvs_utils.set_str("DTD", "ta_mac", TA_MAC)

# Verifier
stored = nvs_utils.get_str("DTD", "ta_mac", default="")
print("Stocké en NVS: {}".format(stored))

if stored == TA_MAC:
    print("✓ Configuration OK!")
else:
    print("✗ ERREUR de stockage!")

print("\nLe DD peut maintenant communiquer avec le TA via ESP-NOW")