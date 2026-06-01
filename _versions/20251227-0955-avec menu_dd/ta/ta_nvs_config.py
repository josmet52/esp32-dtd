"""
ta_nvs_config.py - Gestion configuration NVS pour mode radio
Version: 1.0.0
Date: 26.12.2025

Stockage persistant du mode radio sélectionné par l'utilisateur.
Permet de changer de mode sans reflasher le firmware.

Modes disponibles:
- ESP-NOW Normal (sans WiFi, rapide)
- ESP-NOW RSSI (avec WiFi, diagnostic)
- Radio 433MHz (ancien mode)
"""

try:
    import esp32
except ImportError:
    esp32 = None

from ta_logger import get_logger
logger = get_logger()

# Constantes de modes radio
RADIO_MODE_ESP_NORMAL = 0  # ESP-NOW v5.0.0 sans WiFi
RADIO_MODE_ESP_RSSI = 1    # ESP-NOW v5.1.2 avec WiFi
RADIO_MODE_433 = 2         # Radio 433MHz UART

# Clé NVS pour le mode radio
NVS_NAMESPACE = "ta_config"
NVS_KEY_RADIO_MODE = "radio_mode"

# Mode par défaut (ESP-NOW Normal)
DEFAULT_RADIO_MODE = RADIO_MODE_ESP_NORMAL

class NVSConfig:
    """Gestionnaire de configuration NVS"""
    
    @staticmethod
    def get_radio_mode():
        """
        Lit le mode radio depuis la NVS
        
        Returns:
            int: Mode radio (RADIO_MODE_ESP_NORMAL, RADIO_MODE_ESP_RSSI, ou RADIO_MODE_433)
                 Retourne DEFAULT_RADIO_MODE si aucune valeur en NVS
        """
        if not esp32:
            logger.warning("NVS non disponible (pas sur ESP32)", "nvs")
            return DEFAULT_RADIO_MODE
        
        try:
            # Lire depuis NVS
            nvs = esp32.NVS(NVS_NAMESPACE)
            mode = nvs.get_i32(NVS_KEY_RADIO_MODE)
            
            # Valider le mode
            if mode in [RADIO_MODE_ESP_NORMAL, RADIO_MODE_ESP_RSSI, RADIO_MODE_433]:
                logger.info("Mode radio NVS: {}".format(
                    NVSConfig.get_mode_name(mode)), "nvs")
                return mode
            else:
                logger.warning("Mode NVS invalide ({}), utilisation défaut".format(mode), "nvs")
                return DEFAULT_RADIO_MODE
                
        except OSError:
            # Clé n'existe pas encore
            logger.info("Pas de mode en NVS, utilisation défaut: {}".format(
                NVSConfig.get_mode_name(DEFAULT_RADIO_MODE)), "nvs")
            return DEFAULT_RADIO_MODE
            
        except Exception as e:
            logger.error("Erreur lecture NVS: {}".format(e), "nvs")
            return DEFAULT_RADIO_MODE
    
    @staticmethod
    def set_radio_mode(mode):
        """
        Enregistre le mode radio dans la NVS
        
        Args:
            mode (int): Mode radio à enregistrer
            
        Returns:
            bool: True si succès, False sinon
        """
        if not esp32:
            logger.error("NVS non disponible (pas sur ESP32)", "nvs")
            return False
        
        # Valider le mode
        if mode not in [RADIO_MODE_ESP_NORMAL, RADIO_MODE_ESP_RSSI, RADIO_MODE_433]:
            logger.error("Mode invalide: {}".format(mode), "nvs")
            return False
        
        try:
            # Écrire dans NVS
            nvs = esp32.NVS(NVS_NAMESPACE)
            nvs.set_i32(NVS_KEY_RADIO_MODE, mode)
            nvs.commit()
            
            logger.info("Mode radio enregistré: {}".format(
                NVSConfig.get_mode_name(mode)), "nvs")
            return True
            
        except Exception as e:
            logger.error("Erreur écriture NVS: {}".format(e), "nvs")
            return False
    
    @staticmethod
    def get_mode_name(mode):
        """
        Retourne le nom du mode radio
        
        Args:
            mode (int): Mode radio
            
        Returns:
            str: Nom du mode
        """
        names = {
            RADIO_MODE_ESP_NORMAL: "ESP-NOW Normal",
            RADIO_MODE_ESP_RSSI: "ESP-NOW RSSI",
            RADIO_MODE_433: "Radio 433MHz"
        }
        return names.get(mode, "Inconnu")
    
    @staticmethod
    def clear():
        """
        Efface la configuration NVS (remet aux valeurs par défaut)
        
        Returns:
            bool: True si succès, False sinon
        """
        if not esp32:
            logger.error("NVS non disponible", "nvs")
            return False
        
        try:
            nvs = esp32.NVS(NVS_NAMESPACE)
            nvs.erase_key(NVS_KEY_RADIO_MODE)
            nvs.commit()
            logger.info("Configuration NVS effacée", "nvs")
            return True
            
        except Exception as e:
            logger.error("Erreur effacement NVS: {}".format(e), "nvs")
            return False