"""
dd_nvs_config.py - Gestion configuration NVS pour mode radio DD
Version: 6.0.0
Date: 26.12.2025

Stockage persistant du mode radio sélectionné.
Modes disponibles:
- ESP-NOW (sans fil 2.4GHz)
- Radio 433MHz (GT38 UART)
"""

try:
    import esp32
except ImportError:
    esp32 = None

# Constantes de modes radio
RADIO_MODE_ESPNOW = 0  # ESP-NOW sans fil
RADIO_MODE_433 = 1     # Radio 433MHz UART

# Cle NVS pour le mode radio
NVS_NAMESPACE = "DTD"
NVS_KEY_RADIO_MODE = "radio_mode"

# Mode par defaut (ESP-NOW)
DEFAULT_RADIO_MODE = RADIO_MODE_ESPNOW

class DDNVSConfig:
    """Gestionnaire de configuration NVS pour DD"""
    
    @staticmethod
    def get_radio_mode():
        """
        Lit le mode radio depuis la NVS
        
        Returns:
            int: Mode radio (RADIO_MODE_ESPNOW ou RADIO_MODE_433)
                 Retourne DEFAULT_RADIO_MODE si aucune valeur en NVS
        """
        if not esp32:
            print("[NVS] NVS non disponible (pas sur ESP32)")
            return DEFAULT_RADIO_MODE
        
        try:
            # Lire depuis NVS
            nvs = esp32.NVS(NVS_NAMESPACE)
            mode = nvs.get_i32(NVS_KEY_RADIO_MODE)
            
            # Valider le mode
            if mode in [RADIO_MODE_ESPNOW, RADIO_MODE_433]:
                print("[NVS] Mode radio: {}".format(
                    DDNVSConfig.get_mode_name(mode)))
                return mode
            else:
                print("[NVS] Mode invalide ({}), utilisation défaut".format(mode))
                return DEFAULT_RADIO_MODE
                
        except OSError:
            # Cle n'existe pas encore
            print("[NVS] Pas de mode en NVS, utilisation défaut: {}".format(
                DDNVSConfig.get_mode_name(DEFAULT_RADIO_MODE)))
            return DEFAULT_RADIO_MODE
            
        except Exception as e:
            print("[NVS] Erreur lecture: {}".format(e))
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
            print("[NVS] NVS non disponible")
            return False
        
        # Valider le mode
        if mode not in [RADIO_MODE_ESPNOW, RADIO_MODE_433]:
            print("[NVS] Mode invalide: {}".format(mode))
            return False
        
        try:
            # Ecrire dans NVS
            nvs = esp32.NVS(NVS_NAMESPACE)
            nvs.set_i32(NVS_KEY_RADIO_MODE, mode)
            nvs.commit()
            
            print("[NVS] Mode radio enregistré: {}".format(
                DDNVSConfig.get_mode_name(mode)))
            return True
            
        except Exception as e:
            print("[NVS] Erreur écriture: {}".format(e))
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
            RADIO_MODE_ESPNOW: "ESP-NOW",
            RADIO_MODE_433: "Radio 433MHz"
        }
        return names.get(mode, "Inconnu")
    
    @staticmethod
    def clear():
        """
        Efface la configuration NVS
        
        Returns:
            bool: True si succès, False sinon
        """
        if not esp32:
            print("[NVS] NVS non disponible")
            return False
        
        try:
            nvs = esp32.NVS(NVS_NAMESPACE)
            nvs.erase_key(NVS_KEY_RADIO_MODE)
            nvs.commit()
            print("[NVS] Configuration effacée")
            return True
            
        except Exception as e:
            print("[NVS] Erreur effacement: {}".format(e))
            return False


def show_current_mode():
    """Affiche le mode actuel"""
    mode = DDNVSConfig.get_radio_mode()
    print("="*50)
    print("MODE RADIO ACTUEL")
    print("="*50)
    print("Mode: {}".format(DDNVSConfig.get_mode_name(mode)))
    print("Code: {}".format(mode))
    print("="*50)
    return mode


def quick_set_mode(mode_name):
    """
    Change rapidement de mode depuis REPL
    
    Args:
        mode_name (str): 'espnow' ou '433'
    
    Example:
        >>> from dd_nvs_config import quick_set_mode
        >>> quick_set_mode('espnow')
    """
    mode_map = {
        'espnow': RADIO_MODE_ESPNOW,
        '433': RADIO_MODE_433
    }
    
    mode_name = mode_name.lower()
    if mode_name not in mode_map:
        print("Mode invalide. Utilisez: 'espnow' ou '433'")
        return False
    
    mode = mode_map[mode_name]
    print("Changement vers: {}".format(DDNVSConfig.get_mode_name(mode)))
    
    if DDNVSConfig.set_radio_mode(mode):
        print("✓ Mode enregistré!")
        print("Rebootez le DD: import machine; machine.reset()")
        return True
    else:
        print("✗ Erreur")
        return False