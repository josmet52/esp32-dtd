"""
================================================================================
ta_config.py - Configuration globale du système DTD (Détecteur de Détection)
================================================================================

Description:
-----------
Fichier centralisé de configuration pour le Terminal Aggregator (TA).
Contient tous les paramètres hardware, UI, radio et application.

Hardware supporté:
-----------------
- Carte: LilyGO T-Display-S3 AMOLED
- Écran: AMOLED 240x536 pixels (mode portrait uniquement)
- Radio: Module 433MHz GT38 via UART
- Boutons: UP (GPIO 0) et DOWN (GPIO 21)

Organisation:
------------
1. VERSION - Informations de version
2. HARDWARE - Configuration pins et périphériques
3. APPLICATION - Paramètres de l'application principale
4. INTERFACE UTILISATEUR - Layout et dimensions de l'écran
5. RADIO 433 MHz - Configuration du protocole de communication
6. LOGGER - Configuration du système de logs

Mode de communication:
---------------------
Mode séquentiel uniquement (POLL:XX → ACK:XX:Y)
- TA interroge chaque DD individuellement
- Attente de la réponse ACK avant DD suivant
- Timeout configurable par POLL_PERIOD_MS

Auteur: jom52
Version: 2.5.0
Date: 09.12.2025
================================================================================
"""

import tft_config_amoled as tft_config

# ============================================================================
# VERSION
# ============================================================================
# Informations de version affichees a l'ecran et dans les logs
# Note: APP_NAME est modifie dynamiquement par ta_main.py selon le mode radio

APP_NAME = "TA-espnow"       # Nom par defaut (modifie par ta_main.py)
APP_VERSION = "2.7.1"        # Numero de version
APP_DATE = "27.12.2025"      # Date de la version

# ============================================================================
# HARDWARE
# ============================================================================
# Configuration de tous les composants matériels

HARDWARE = {
    # Identification de la carte
    "BOARD_NAME": "LilyGO T-Display-S3 AMOLED",
    
    # Dimensions natives de l'écran AMOLED
    "DISPLAY": {
        "WIDTH": 240,      # Largeur en pixels (mode portrait)
        "HEIGHT": 536,     # Hauteur en pixels (mode portrait)
    },

    # configuration WIFI
    "WIFI": {
        "SSID": "Jo",
        "PASSWORD": "mablonde"
    },
    
    # Configuration UART pour le module radio 433MHz GT38
    "UART_RADIO": {
        "INDEX": 2,            # UART2 de l'ESP32
        "BAUD": 9600,          # Vitesse de communication
        "TX": 43,              # Pin transmission (ESP32 → GT38)
        "RX": 44,              # Pin réception (GT38 → ESP32)
        "PIN_GT38_SET": 45,    # Pin SET du GT38 (initialisation)
        "TIMEOUT_MS": 100,     # Timeout lecture UART en millisecondes
    },

    # Configuration des boutons physiques
    "BUTTONS": {
        "PIN_UP": 0,           # GPIO 0 - Bouton UP (mode OTA si pression longue)
        "PIN_DOWN": 21,        # GPIO 21 - Bouton DOWN (affichage batterie)
        "LONG_MS": 800,        # Durée pression longue standard (ms)
        "DEBOUNCE_MS": 50,     # Anti-rebond (ms)
    },
    
    # Configuration de la batterie (ADC)
    "BATTERY": {
        "PIN_ADC": 4,          # GPIO 4 - Pin ADC pour lecture batterie
        "VOLTAGE_MIN": 3.0,    # Tension minimale batterie (V)
        "VOLTAGE_MAX": 4.2,    # Tension maximale batterie (V)
        "VOLTAGE_DIVIDER": 2,  # Ratio du diviseur de tension
        "ADC_MAX": 4095,       # Valeur max de l'ADC (12 bits)
        "VREF": 3.3,           # Tension de référence ADC (V)
    },
}

# ============================================================================
# APPLICATION
# ============================================================================
# Paramètres généraux de l'application principale

MAIN = {
    "APP_NAME": APP_NAME,                  # Nom affiché
    "VERSION_NO": APP_VERSION,             # Version affichée
    "VERSION_DATE": APP_DATE,              # Date affichée
    "DEBUG_MODE": True,                   # Active les logs de débogage détaillés
    "WATCHDOG_ENABLED": False,             # Watchdog hardware (reset auto si freeze)
    "WATCHDOG_TIMEOUT_MS": 30000,          # Timeout watchdog (30 secondes)
}

# ============================================================================
# INTERFACE UTILISATEUR
# ============================================================================
# Configuration du layout et de l'affichage

UI = {
    # Dimensions et orientation
    "WIDTH": 240,                          # Largeur écran en pixels
    "HEIGHT": 536,                         # Hauteur écran en pixels
    "ROTATION": 0,                         # 0=portrait, 1=landscape, 2=portrait inversé, 3=landscape inversé
    
    # Hauteurs des zones (en pixels)
    "ZONE_TITLE_HEIGHT": 45,               # Zone titre en haut
    "ZONE_DD_LINE_HEIGHT": 45,             # Hauteur d'une ligne DD (8 lignes = DD0 à DD7)
    "ZONE_LOG_LINE_HEIGHT": 70,            # Zone de log/info au centre
    
    # Marges et espacement
    "MARGIN_LEFT": 8,                      # Marge gauche
    "MARGIN_RIGHT": 8,                     # Marge droite
    "MARGIN_TOP": 3,                       # Marge en haut des sections
    "LINE_SPACING": 3,                     # Espacement entre lignes DD
    
    # Logs (pour compatibilité, non utilisé actuellement)
    "LOG_MAX_LINES": 15,                   # Nombre max de lignes de log gardées
}

# Palette de couleurs (format RGB565)
COLORS = {
    "C_BLACK": tft_config.BLACK,                         # Noir (fond)
    "C_WHITE": tft_config.WHITE,                         # Blanc (texte)
    "C_BG":    tft_config.color565(0, 0, 0),        # Fond noir
    "C_HDR":   tft_config.color565(0, 64, 200),     # Bleu foncé (header)
    "C_ON":    tft_config.color565(0, 200, 0),      # Vert (détecteur présent)
    "C_OFF":   tft_config.color565(200, 0, 0),      # Rouge (détecteur absent)
    "C_UNK":   tft_config.color565(120, 120, 120),  # Gris (état inconnu)
    "C_PGR":   tft_config.color565(255, 127, 0),    # Orange (progression)
}

# ============================================================================
# RADIO 433 MHz
# ============================================================================
# Configuration du protocole de communication radio

RADIO = {
    # IDs des détecteurs à surveiller (DD0 à DD7)
    "GROUP_IDS": [0, 1, 2, 3, 4, 5, 6, 7],
    
    # Timing du mode séquentiel
    "POLL_PERIOD_MS": 1100,         # Période entre interrogations (ms)
    "REPLY_TIMEOUT_MS": 300,        # Timeout attente réponse ACK (ms)
    
    # Gestion des réessais en cas d'échec
    "RETRY": {
        "MAX_RETRIES": 3,           # Nombre max de tentatives
        "TIMEOUT_BASE_MS": 500,     # Timeout de base (ms)
        "TIMEOUT_MULTIPLIER": 1.5,  # Multiplicateur exponentiel
        "BACKOFF_ENABLED": True,    # Active le backoff exponentiel
        "BACKOFF_MS": 100,          # Délai initial entre réessais (ms)
    },

    # États possibles d'un détecteur
    "STATE_UNKNOWN": 0,             # État inconnu (pas encore interrogé ou timeout)
    "STATE_PRESENT": 1,             # Détecteur présent/actif (ACK:XX:1)
    "STATE_ABSENT": 2,              # Détecteur absent/inactif (ACK:XX:0)

    # Format des trames (pour référence, géré par ta_radio_433.py)
    "FRAME": {
        "START_BYTE": 0xA5,         # Octet de début de trame
        "END_BYTE": 0x5A,           # Octet de fin de trame
        "PROTO_VER": 0x01,          # Version du protocole
        "MAX_LEN": 16,              # Longueur max d'une trame
    },
}

# ============================================================================
# LOGGER
# ============================================================================
# Configuration du système de logging

LOGGER = {
    # Niveau de log: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    # DEBUG: Tous les messages
    # INFO: Messages informatifs et supérieurs
    # WARNING: Avertissements et supérieurs
    # ERROR: Erreurs et critiques uniquement
    "LEVEL": "INFO",
}
