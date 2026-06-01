"""
project : DTD
Component : TA
file: tft_config_amoled.py

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-dtd

v1.0.0 : 13.01.2026
"""

import amoled
from machine import Pin, SPI

# ============================================================================
# Pin definitions pour T-Display-S3 AMOLED
# ============================================================================

TFT_SD0 = Pin(8, Pin.OUT)    # SERIAL OUTPUT SIGNAL
TFT_TE  = Pin(9, Pin.OUT)    # TEARING EFFECT CONTROL
TFT_CS  = Pin(6, Pin.OUT)    # CHIP SELECT
TFT_SCK = Pin(47, Pin.OUT)   # SPICLK_P
TFT_RST = Pin(17, Pin.OUT)   # RESET
TFT_D0  = Pin(18, Pin.OUT)   # D0 QSPI
TFT_D1  = Pin(7, Pin.OUT)    # D1 QSPI
TFT_D2  = Pin(48, Pin.OUT)   # D2 QSPI & SPICLK_N
TFT_D3  = Pin(5, Pin.OUT)    # D3 QSPI
TFT_CDE = Pin(38, Pin.OUT)   # GPIO38 - POWER ENABLE (CRITICAL!)
TFT_TS_IN = Pin(21, Pin.IN, Pin.PULL_UP)  # INTERRUPT (optionnel)

# ============================================================================
# Constantes pour compatibilité avec l'ancien code
# ============================================================================

# Constantes de couleur RGB565 (format BRG565 pour cet ecran AMOLED)
# ATTENTION: Cet ecran utilise BRG au lieu de RGB !
# Format: BBBBB RRRRR GGGGGG (Bleu haut, Rouge milieu, Vert bas)
BLACK   = 0x0000  # BRG565: 0,   0,   0
WHITE   = 0xFFFF  # BRG565: 255, 255, 255
RED     = 0x07E0  # BRG565: 0,   255, 0    (vert → rouge)
GREEN   = 0x001F  # BRG565: 0,   0,   255  (bleu → vert)
BLUE    = 0xF800  # BRG565: 255, 0,   0    (rouge → bleu)
YELLOW  = 0x07FF  # BRG565: 0,   255, 255  (rouge + vert = jaune)
CYAN    = 0xF81F  # BRG565: 255, 0,   255  (bleu + vert = cyan)
MAGENTA = 0xFFE0  # BRG565: 255, 255, 0    (bleu + rouge = magenta)

# ============================================================================
# Fonction de conversion couleur (compatibilité)
# ============================================================================

def color565(r, g, b):
    """
    Convertit RGB (0-255) en format BRG565 pour cet ecran AMOLED
    
    Args:
        r: Rouge (0-255)
        g: Vert (0-255)
        b: Bleu (0-255)
    
    Returns:
        int: Couleur au format BRG565
    
    Note:
        ATTENTION: Cet ecran utilise BRG565 au lieu de RGB565 !
        Format: BBBBB RRRRR GGGGGG (16 bits)
        B: 5 bits (bits 11-15), R: 5 bits (bits 5-10 partage avec G), G: 6 bits (bits 0-5)
        
        Mapping des canaux:
        - Bleu (b)  → bits 11-15 (poids fort)
        - Rouge (r) → bits 5-9 (milieu, sur 5 bits)
        - Vert (g)  → bits 0-5 (poids faible, sur 6 bits)
    """
    # Convertir RGB 8-bit en BRG565
    # B: 8 bits -> 5 bits (position bits 11-15)
    # R: 8 bits -> 5 bits (position bits 5-9)
    # G: 8 bits -> 6 bits (position bits 0-5)
    return ((b & 0xF8) << 8) | ((r & 0xF8) << 3) | (g >> 2)


# ============================================================================
# Fonction de configuration principale
# ============================================================================

def config(rotation=1):
    """
    Configure AMOLED display avec séquence d'initialisation complète
    
    Args:
        rotation: Rotation de l'écran
                  0 = Portrait (240x536)
                  1 = Landscape (536x240) - Par défaut pour DTD
                  2 = Portrait inversé (240x536)
                  3 = Landscape inversé (536x240)
    
    Returns:
        AMOLED display object prêt à l'emploi
    
    Note:
        Cette fonction active automatiquement GPIO38 (alimentation écran)
        mais n'appelle pas reset()/init()/rotation()/brightness()
        Ces méthodes doivent être appelées par ta_ui.py
    """
    # ÉTAPE 1: Activer l'alimentation de l'écran (CRITIQUE!)
    TFT_CDE.value(1)
    
    # ÉTAPE 2: Créer le bus SPI (sans MOSI/MISO car QSPI utilise les data pins)
    spi = SPI(2, sck=TFT_SCK, mosi=None, miso=None, polarity=0, phase=0)
    
    # ÉTAPE 3: Créer le QSPIPanel avec les 4 lignes de données
    panel = amoled.QSPIPanel(
        spi=spi,
        data=(TFT_D0, TFT_D1, TFT_D2, TFT_D3),  # 4 lignes QSPI (CRITIQUE!)
        dc=TFT_D1,          # D1 utilisé comme DC en mode QSPI
        cs=TFT_CS,
        pclk=80_000_000,    # 80MHz
        width=240,          # Largeur native
        height=536          # Hauteur native
    )
    
    # ÉTAPE 4: Créer l'objet AMOLED display
    return amoled.AMOLED(panel, type=0, reset=TFT_RST, bpp=16)


# ============================================================================
# Fonction d'initialisation complète (helper)
# ============================================================================

def init_display(tft, rotation=1, brightness=128):
    """
    Initialise complètement l'écran avec toute la séquence
    
    Args:
        tft: Objet AMOLED retourné par config()
        rotation: Rotation (0-3)
        brightness: Luminosité initiale (0-255)
    
    Returns:
        tft: L'objet AMOLED initialisé
    
    Note:
        Cette fonction est optionnelle. Dans DTD, l'initialisation
        est faite directement dans ta_ui.py et ta_ui_portrait.py
    """
    # Vérifier que GPIO38 est activé
    if TFT_CDE.value() == 0:
        TFT_CDE.value(1)
    
    # Séquence d'initialisation complète
    tft.reset()
    tft.init()
    tft.rotation(rotation)
    tft.brightness(brightness)
    
    return tft


# ============================================================================
# Fonction de configuration alternative (compatibilité)
# ============================================================================

def config_qspi():
    """
    Configuration alternative utilisant le mode QSPI complet
    (Alias de config() pour compatibilité)
    
    Returns:
        AMOLED display object
    """
    return config()


# ============================================================================
# Informations du module
# ============================================================================

__version__ = "2.0.0-AMOLED-NATIVE"
__author__ = "jom52 / Claude AI"
__date__ = "08.11.2025"

# Message de chargement (optionnel - commentez si vous ne voulez pas)
# print("[tft_config_amoled] Module chargé - Version {}".format(__version__))
# print("[tft_config_amoled] Driver: amoled natif (QSPI)")
# print("[tft_config_amoled] GPIO38 (TFT_CDE) géré automatiquement")
