"""
================================================================================
boot.py v2.0.0 - Séquence de démarrage TA (Terminal Aggregator)
================================================================================

Description:
-----------
Point d'entrée principal du système TA. Ce fichier est exécuté automatiquement 
au démarrage de l'ESP32 et démarre toujours l'application en mode normal.

Fonctionnement:
--------------
- Au démarrage: Lance TOUJOURS en mode NORMAL
- En mode normal: Pression longue bouton UP (3s) → Passage en mode OTA
- En mode OTA: Pression longue bouton UP (3s) → Retour en mode NORMAL

Architecture:
------------
boot.py (ce fichier)
    ↓
ta_main.py (mode normal)
    ↓
ta_app.py (application principale)

Note importante:
---------------
Le passage entre modes normal/OTA se fait par détection des boutons dans 
les modules respectifs (ta_buttons.py pour normal → OTA, ta_ota.py pour OTA → normal)

Auteur: jom52
Version: 2.0.0
Date: 09.12.2025
================================================================================
"""

__version__ = "2.0.0"

# Affichage du message de démarrage
print("\n=== TA BOOT v{} ===".format(__version__))
print("NORMAL MODE")

# Démarrage du mode normal (toujours au boot)
import ta_main
ta_main.main()
