"""
project : DTD
Component : DD
file: dd_config.py
author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-dtd
v1.0.2 : 14.01.2026 - Regroupement de toutes les constantes
"""

__version__ = "1.0.2"

import dd_nvs_utils as nvs_utils
import machine

# ================================================================
# CONSTANTES - MODES RADIO
# ================================================================
RADIO_MODE_ESPNOW = 0
RADIO_MODE_433 = 1

MODE_NAMES = {
    RADIO_MODE_ESPNOW: "ESP-NOW",
    RADIO_MODE_433: "Radio 433MHz"
}

# ================================================================
# CONSTANTES - COMPORTEMENT SYSTÈME
# ================================================================
DEV_MODE = False
WATCHDOG_ENABLED = False
WATCHDOG_MS = 30000
STAT_PERIOD = 5000
AUTO_START = True

# ================================================================
# CONSTANTES - BATTERIE
# ================================================================
UBAT_HIGH = 4.0
UBAT_MID = 3.7
UBAT_LOW = 3.5
BAT_VOLTAGE_DIVIDER = 2.0
BAT_LED_BLINK_MS = 500

# ================================================================
# CONSTANTES - DÉTECTION
# ================================================================
DEBOUNCE_SAMPLES = 20
DEBOUNCE_DELAY_US = 1000

# ================================================================
# CONSTANTES - LED ACTIVITÉ
# ================================================================
ACTIVITY_LED_TIMEOUT_MS = 1000
ACTIVITY_LED_ON_MS = 100
ACTIVITY_LED_PERIOD_MS = 1000

# ================================================================
# CONSTANTES - HARDWARE PINS (WROVER-T7)
# ================================================================
# LED interne
LED_INTERNAL_PIN = 19

# Straps ID (BIT0-2)
BIT0_PIN = 27
BIT1_PIN = 25
BIT2_PIN = 32

# Status détecteur
DD_STATUS_PIN = 33

# Batterie et LEDs
BATTERY_ADC_PIN = 35
LED_RED_PIN = 22
LED_GREEN_PIN = 21
USB_POWER_PIN = 2

# UART Radio 433MHz
UART_INDEX = 2
UART_TX_PIN = 18
UART_RX_PIN = 23
UART_BAUD = 9600
UART_TIMEOUT_MS = 100

# ================================================================
# GESTION MODE RADIO
# ================================================================

def get_radio_mode():
    """
    Lit le mode radio depuis NVS
    
    Returns:
        int: RADIO_MODE_ESPNOW ou RADIO_MODE_433 (défaut: ESPNOW)
    """
    try:
        mode = nvs_utils.get_i32("DTD", "radio_mode", default=RADIO_MODE_ESPNOW)
        if mode in [RADIO_MODE_ESPNOW, RADIO_MODE_433]:
            return mode
        return RADIO_MODE_ESPNOW
    except:
        return RADIO_MODE_ESPNOW

def set_radio_mode(mode):
    """
    Enregistre le mode radio en NVS
    
    Args:
        mode (int): RADIO_MODE_ESPNOW ou RADIO_MODE_433
        
    Returns:
        bool: True si succès
    """
    if mode not in [RADIO_MODE_ESPNOW, RADIO_MODE_433]:
        print("[CONFIG] Mode invalide: {}".format(mode))
        return False
    
    try:
        nvs_utils.set_i32("DTD", "radio_mode", mode)
        print("[CONFIG] Mode radio enregistré: {}".format(get_mode_name(mode)))
        return True
    except Exception as e:
        print("[CONFIG] Erreur enregistrement mode:", e)
        return False

def get_mode_name(mode):
    """
    Retourne le nom du mode radio
    
    Args:
        mode (int): Mode radio
        
    Returns:
        str: Nom du mode
    """
    return MODE_NAMES.get(mode, "Inconnu")

# ================================================================
# AFFICHAGE CONFIGURATION
# ================================================================

def show_config():
    """Affiche la configuration complète du DD"""
    print()
    print("=" * 70)
    print("CONFIGURATION DD")
    print("=" * 70)
    print()
    
    # Mode radio
    mode = get_radio_mode()
    print("MODE RADIO")
    print("  Mode actuel: {}".format(get_mode_name(mode)))
    print()
    
    # Calibration batterie
    bat_cal = nvs_utils.get_battery_calibration()
    print("BATTERIE")
    print("  Facteur calibration: {:.3f}".format(bat_cal))
    
    # Tension batterie si possible
    try:
        from machine import ADC, Pin
        adc = ADC(Pin(BATTERY_ADC_PIN))
        try:
            adc.atten(ADC.ATTN_11DB)
        except:
            pass
        raw = adc.read()
        voltage_adc = (raw / 4095.0) * 3.3
        voltage_bat = voltage_adc * BAT_VOLTAGE_DIVIDER * bat_cal
        print("  Tension mesurée: {:.2f}V".format(voltage_bat))
    except:
        pass
    print()
    
    # MAC Terminal Admin
    ta_mac = nvs_utils.get_ta_mac()
    print("COMMUNICATION")
    if ta_mac:
        print("  MAC Terminal Admin: {}".format(ta_mac))
    else:
        print("  MAC Terminal Admin: NON CONFIGURÉ")
    print()
    
    print("=" * 70)

# ================================================================
# CONFIGURATION MODE RADIO
# ================================================================

def config_radio_mode():
    """Configuration interactive du mode radio"""
    print()
    print("=" * 70)
    print("CONFIGURATION MODE RADIO")
    print("=" * 70)
    print()
    
    # Afficher mode actuel
    current_mode = get_radio_mode()
    print("Mode actuel: {}".format(get_mode_name(current_mode)))
    print()
    
    # Menu
    print("Modes disponibles:")
    print("  1. ESP-NOW (sans fil 2.4GHz)")
    print("  2. Radio 433MHz (module GT38)")
    print("  3. Annuler")
    print()
    
    choice = input("Choisir (1-3): ").strip()
    
    if choice == "1":
        new_mode = RADIO_MODE_ESPNOW
    elif choice == "2":
        new_mode = RADIO_MODE_433
    elif choice == "3":
        print("Annulé.")
        return
    else:
        print("Choix invalide!")
        return
    
    # Vérifier si changement nécessaire
    if new_mode == current_mode:
        print("Le mode est déjà configuré sur: {}".format(get_mode_name(new_mode)))
        return
    
    # Confirmation
    print()
    print("Nouveau mode: {}".format(get_mode_name(new_mode)))
    confirm = input("Confirmer (o/n): ").strip().lower()
    
    if confirm not in ["o", "y"]:
        print("Annulé.")
        return
    
    # Enregistrement
    if set_radio_mode(new_mode):
        print()
        print("✓ Mode radio configuré: {}".format(get_mode_name(new_mode)))
        print()
        print("IMPORTANT: Redémarrer le DD pour appliquer")
        print()
        reboot = input("Redémarrer maintenant? (o/n): ").strip().lower()
        if reboot in ["o", "y"]:
            print("Redémarrage...")
            machine.reset()
    else:
        print("✗ Erreur lors de la configuration")

# ================================================================
# CONFIGURATION CALIBRATION BATTERIE
# ================================================================

def config_battery():
    """Configuration interactive calibration batterie"""
    print()
    print("=" * 70)
    print("CALIBRATION BATTERIE")
    print("=" * 70)
    print()
    
    # Valeur actuelle
    current = nvs_utils.get_battery_calibration()
    print("Facteur actuel: {:.3f}".format(current))
    print()
    
    # Afficher tension si possible
    try:
        from machine import ADC, Pin
        adc = ADC(Pin(BATTERY_ADC_PIN))
        try:
            adc.atten(ADC.ATTN_11DB)
        except:
            pass
        raw = adc.read()
        voltage_adc = (raw / 4095.0) * 3.3
        voltage_bat = voltage_adc * BAT_VOLTAGE_DIVIDER * current
        print("Tension mesurée: {:.2f}V (avec facteur {:.3f})".format(voltage_bat, current))
        print()
    except:
        pass
    
    print("Information:")
    print("  - Facteur par défaut: 1.000")
    print("  - Plage valide: 0.500 à 2.000")
    print("  - Calcul: facteur = tension_réelle / tension_mesurée")
    print("  - Exemple: Si mesure=3.6V mais réel=3.7V → 3.7/3.6=1.028")
    print()
    
    # Saisie nouvelle valeur
    try:
        value_str = input("Nouveau facteur (ou vide pour annuler): ").strip()
        if not value_str:
            print("Annulé.")
            return
        
        new_factor = float(value_str)
        
    except ValueError:
        print("Erreur: valeur invalide!")
        return
    
    # Enregistrement
    if nvs_utils.set_battery_calibration(new_factor):
        print()
        print("✓ Calibration enregistrée: {:.3f}".format(new_factor))
        print()
        
        # Afficher nouvelle tension si possible
        try:
            voltage_new = voltage_adc * BAT_VOLTAGE_DIVIDER * new_factor
            print("Nouvelle tension: {:.2f}V".format(voltage_new))
            print()
        except:
            pass
        
        print("IMPORTANT: Redémarrer le DD pour appliquer")
        print()
        reboot = input("Redémarrer maintenant? (o/n): ").strip().lower()
        if reboot in ["o", "y"]:
            print("Redémarrage...")
            machine.reset()
    else:
        print("✗ Erreur lors de la configuration")

# ================================================================
# CONFIGURATION MAC TERMINAL ADMIN
# ================================================================

def config_ta_mac():
    """Configuration interactive MAC Terminal Admin"""
    print()
    print("=" * 70)
    print("MAC TERMINAL ADMIN")
    print("=" * 70)
    print()
    
    # Valeur actuelle
    current = nvs_utils.get_ta_mac()
    if current:
        print("MAC actuel: {}".format(current))
    else:
        print("MAC actuel: NON CONFIGURÉ")
    print()
    
    print("Information:")
    print("  - Format: AA:BB:CC:DD:EE:FF")
    print("  - Requis pour communication ESP-NOW uniquement")
    print("  - Obtenir MAC du TA avec:")
    print("    >>> import network")
    print("    >>> sta = network.WLAN(network.STA_IF)")
    print("    >>> sta.active(True)")
    print("    >>> ':'.join('{:02X}'.format(b) for b in sta.config('mac'))")
    print()
    
    # Saisie nouvelle valeur
    mac_str = input("Nouvelle adresse MAC (ou vide pour annuler): ").strip()
    if not mac_str:
        print("Annulé.")
        return
    
    # Enregistrement
    if nvs_utils.set_ta_mac(mac_str):
        print()
        print("✓ MAC Terminal Admin enregistré: {}".format(mac_str))
        print()
        print("Le DD peut maintenant communiquer avec le TA via ESP-NOW")
    else:
        print("✗ Erreur lors de la configuration")

# ================================================================
# RÉINITIALISATION
# ================================================================

def reset_config():
    """Réinitialise toute la configuration"""
    print()
    print("=" * 70)
    print("RÉINITIALISATION CONFIGURATION")
    print("=" * 70)
    print()
    
    print("Cette opération va réinitialiser:")
    print("  - Mode radio → ESP-NOW")
    print("  - Calibration batterie → 1.000")
    print("  - MAC Terminal Admin → vide")
    print()
    
    confirm = input("Confirmer la réinitialisation (o/n): ").strip().lower()
    if confirm not in ["o", "y"]:
        print("Annulé.")
        return
    
    print()
    print("Réinitialisation en cours...")
    
    try:
        # Mode radio
        nvs_utils.set_i32("DTD", "radio_mode", RADIO_MODE_ESPNOW)
        print("  ✓ Mode radio → ESP-NOW")
        
        # Calibration batterie
        nvs_utils.set_f32("DTD", "bat_cal_factor", 1.0)
        print("  ✓ Calibration batterie → 1.000")
        
        # MAC TA
        nvs_utils.set_str("DTD", "ta_mac", "")
        print("  ✓ MAC Terminal Admin → vide")
        
        print()
        print("✓ Configuration réinitialisée")
        print()
        print("IMPORTANT: Redémarrer le DD")
        print()
        reboot = input("Redémarrer maintenant? (o/n): ").strip().lower()
        if reboot in ["o", "y"]:
            print("Redémarrage...")
            machine.reset()
            
    except Exception as e:
        print("✗ Erreur:", e)

# ================================================================
# MENU PRINCIPAL
# ================================================================

def main_menu():
    """Menu principal de configuration"""
    while True:
        print()
        print("=" * 70)
        print("CONFIGURATION DD v{}".format(__version__))
        print("=" * 70)
        print()
        print("1. Configurer mode radio (ESP-NOW / 433MHz)")
        print("2. Configurer calibration batterie")
        print("3. Configurer MAC Terminal Admin")
        print("4. Afficher configuration actuelle")
        print("5. Réinitialiser configuration")
        print("6. Redémarrer le DD")
        print("7. Quitter")
        print()
        
        choice = input("Choisir (1-7): ").strip()
        
        if choice == "1":
            config_radio_mode()
        elif choice == "2":
            config_battery()
        elif choice == "3":
            config_ta_mac()
        elif choice == "4":
            show_config()
        elif choice == "5":
            reset_config()
        elif choice == "6":
            print()
            confirm = input("Redémarrer maintenant? (o/n): ").strip().lower()
            if confirm in ["o", "y"]:
                print("Redémarrage...")
                machine.reset()
            else:
                print("Annulé.")
        elif choice == "7":
            print()
            print("Configuration terminée.")
            break
        else:
            print("Choix invalide!")

# ================================================================
# FONCTIONS RAPIDES (pour utilisation directe)
# ================================================================

def quick_set_mode(mode_name):
    """
    Change rapidement de mode depuis REPL
    
    Args:
        mode_name (str): 'espnow' ou '433'
    
    Example:
        >>> from dd_config import quick_set_mode
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
    print("Changement vers: {}".format(get_mode_name(mode)))
    
    if set_radio_mode(mode):
        print("✓ Mode enregistré!")
        print("Redémarrez le DD: import machine; machine.reset()")
        return True
    else:
        print("✗ Erreur")
        return False

def quick_set_battery(factor):
    """
    Configure rapidement la calibration batterie
    
    Args:
        factor (float): Facteur de calibration
        
    Example:
        >>> from dd_config import quick_set_battery
        >>> quick_set_battery(1.028)
    """
    if nvs_utils.set_battery_calibration(factor):
        print("✓ Calibration enregistrée: {:.3f}".format(factor))
        print("Redémarrez le DD: import machine; machine.reset()")
        return True
    else:
        return False

def quick_set_mac(mac_address):
    """
    Configure rapidement le MAC du TA
    
    Args:
        mac_address (str): Adresse MAC
        
    Example:
        >>> from dd_config import quick_set_mac
        >>> quick_set_mac('AA:BB:CC:DD:EE:FF')
    """
    if nvs_utils.set_ta_mac(mac_address):
        print("✓ MAC enregistré: {}".format(mac_address))
        return True
    else:
        return False

# ================================================================
# POINT D'ENTRÉE
# ================================================================

if __name__ == "__main__":
    main_menu()