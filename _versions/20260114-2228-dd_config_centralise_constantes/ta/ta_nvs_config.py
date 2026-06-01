"""
project : DTD
Component : TA
file: ta_nvs_config.py

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-dtd

v1.0.0 : 13.01.2026
"""

try:
    import esp32
except ImportError:
    esp32 = None

from ta_logger import get_logger
logger = get_logger()

# Constantes de modes radio
RADIO_MODE_ESP_NORMAL = 0  # ESP-NOW sans WiFi
RADIO_MODE_433 = 2         # Radio 433MHz UART

# Cle NVS pour le mode radio
NVS_NAMESPACE = "ta_config"
NVS_KEY_RADIO_MODE = "radio_mode"

# Mode par defaut (ESP-NOW)
DEFAULT_RADIO_MODE = RADIO_MODE_ESP_NORMAL

class NVSConfig: 
    """Gestionnaire de configuration NVS"""
    
    @staticmethod
    def get_radio_mode():
        """
        Lit le mode radio depuis la NVS
        
        Returns:
            int: Mode radio (RADIO_MODE_ESP_NORMAL ou RADIO_MODE_433)
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
            if mode in [RADIO_MODE_ESP_NORMAL, RADIO_MODE_433]:
                logger.info("Mode radio NVS: {}".format(
                    NVSConfig.get_mode_name(mode)), "nvs")
                return mode
            else:
                logger.warning("Mode NVS invalide ({}), utilisation défaut".format(mode), "nvs")
                return DEFAULT_RADIO_MODE
                
        except OSError:
            # Cle n'existe pas encore
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
        if mode not in [RADIO_MODE_ESP_NORMAL, RADIO_MODE_433]:
            logger.error("Mode invalide: {}".format(mode), "nvs")
            return False
        
        try:
            # Ecrire dans NVS
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
            RADIO_MODE_ESP_NORMAL: "ESP-NOW",
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
    
    @staticmethod
    def dump_nvs():
        """
        Affiche tout le contenu de la NVS (namespace ta_config)
        
        Returns:
            dict: Contenu de la NVS ou None si erreur
        """
        if not esp32:
            print("NVS non disponible (pas sur ESP32)")
            return None
        
        try:
            nvs = esp32.NVS(NVS_NAMESPACE)
            print("="*60)
            print("CONTENU NVS - Namespace: {}".format(NVS_NAMESPACE))
            print("="*60)
            
            # Essayer de lire le mode radio
            try:
                mode = nvs.get_i32(NVS_KEY_RADIO_MODE)
                print("radio_mode: {} ({})".format(mode, NVSConfig.get_mode_name(mode)))
            except OSError:
                print("radio_mode: <non défini>")
            
            print("="*60)
            return {"radio_mode": mode if 'mode' in locals() else None}
            
        except Exception as e:
            print("Erreur lecture NVS: {}".format(e))
            return None
    
    @staticmethod
    def show_all_namespaces():
        """
        Tente d'afficher tous les namespaces NVS disponibles
        Note: esp32.NVS ne permet pas de lister tous les namespaces,
        on affiche donc uniquement le namespace ta_config
        """
        if not esp32:
            print("NVS non disponible (pas sur ESP32)")
            return
        
        print("="*60)
        print("NAMESPACES NVS CONNUS")
        print("="*60)
        print("ta_config - Configuration TA (mode radio)")
        print("\nNote: MicroPython ne permet pas de lister tous les namespaces.")
        print("Seuls les namespaces connus sont affichés.")
        print("="*60)


def interactive_menu():
    """
    Menu interactif CLI pour gérer la configuration NVS
    Utilisé pour debug et configuration manuelle
    """
    if not esp32:
        print("NVS non disponible - Cette fonction nécessite un ESP32")
        return
    
    while True:
        print("\n" + "="*60)
        print("MENU CONFIGURATION NVS - ta_nvs_config.py v1.2.0")
        print("="*60)
        print("1. Afficher mode radio actuel")
        print("2. Afficher tout le contenu NVS")
        print("3. Changer mode -> ESP-NOW")
        print("4. Changer mode -> Radio 433MHz")
        print("5. Effacer configuration NVS")
        print("6. Info: Lancer mode OTA")
        print("0. Quitter")
        print("="*60)
        
        try:
            choice = input("Votre choix: ").strip()
            
            if choice == "0":
                print("Au revoir!")
                break
                
            elif choice == "1":
                mode = NVSConfig.get_radio_mode()
                print("\nMode radio actuel: {} ({})".format(
                    NVSConfig.get_mode_name(mode), mode))
                
            elif choice == "2":
                NVSConfig.dump_nvs()
                NVSConfig.show_all_namespaces()
                
            elif choice == "3":
                print("\nChangement vers: ESP-NOW (sans WiFi)")
                confirm = input("Confirmer? (o/n): ").strip().lower()
                if confirm == 'o':
                    if NVSConfig.set_radio_mode(RADIO_MODE_ESP_NORMAL):
                        print("✓ Mode enregistré avec succès!")
                        print("Rebootez le TA pour activer le nouveau mode.")
                    else:
                        print("✗ Erreur lors de l'enregistrement")
                else:
                    print("Annulé")
                    
            elif choice == "4":
                print("\nChangement vers: Radio 433MHz (ancien mode)")
                confirm = input("Confirmer? (o/n): ").strip().lower()
                if confirm == 'o':
                    if NVSConfig.set_radio_mode(RADIO_MODE_433):
                        print("✓ Mode enregistré avec succès!")
                        print("Rebootez le TA pour activer le nouveau mode.")
                    else:
                        print("✗ Erreur lors de l'enregistrement")
                else:
                    print("Annulé")
                    
            elif choice == "5":
                print("\nEffacement de la configuration NVS")
                print("Le mode par défaut (ESP-NOW) sera utilisé au prochain boot")
                confirm = input("Confirmer? (o/n): ").strip().lower()
                if confirm == 'o':
                    if NVSConfig.clear():
                        print("✓ Configuration effacée!")
                    else:
                        print("✗ Erreur lors de l'effacement")
                else:
                    print("Annulé")
                    
            elif choice == "6":
                print("\nINFO: Mode OTA")
                print("Pour lancer le mode OTA:")
                print("1. Via le menu TA (pression longue bouton)")
                print("2. Via Python REPL:")
                print("   >>> from ta_ota import enter_ota_mode")
                print("   >>> enter_ota_mode()")
                
            else:
                print("Choix invalide")
                
        except KeyboardInterrupt:
            print("\n\nInterruption - Au revoir!")
            break
        except Exception as e:
            print("Erreur: {}".format(e))


def quick_set_mode(mode_name):
    """
    Fonction rapide pour changer de mode depuis REPL
    
    Args:
        mode_name (str): 'espnow' ou '433'
    
    Example:
        >>> from ta_nvs_config import quick_set_mode
        >>> quick_set_mode('espnow')
    """
    mode_map = {
        'espnow': RADIO_MODE_ESP_NORMAL,
        'normal': RADIO_MODE_ESP_NORMAL,  # Alias
        '433': RADIO_MODE_433
    }
    
    mode_name = mode_name.lower()
    if mode_name not in mode_map:
        print("Mode invalide. Utilisez: 'espnow', 'normal', ou '433'")
        return False
    
    mode = mode_map[mode_name]
    print("Changement vers: {}".format(NVSConfig.get_mode_name(mode)))
    
    if NVSConfig.set_radio_mode(mode):
        print("✓ Mode enregistré!")
        print("Rebootez le TA pour activer: import machine; machine.reset()")
        return True
    else:
        print("✗ Erreur")
        return False


def show_current_mode():
    """
    Affiche le mode actuel de manière claire
    
    Example:
        >>> from ta_nvs_config import show_current_mode
        >>> show_current_mode()
    """
    mode = NVSConfig.get_radio_mode()
    print("="*60)
    print("MODE RADIO ACTUEL")
    print("="*60)
    print("Mode: {}".format(NVSConfig.get_mode_name(mode)))
    print("Code: {}".format(mode))
    print("="*60)
    return mode


# Si execute directement, lancer le menu interactif
if __name__ == "__main__":
    print("\nta_nvs_config.py - Configuration NVS TA")
    print("Lancement du menu interactif...\n")
    interactive_menu()
