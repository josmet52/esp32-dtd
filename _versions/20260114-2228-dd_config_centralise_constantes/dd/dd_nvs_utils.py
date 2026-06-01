"""
project : DTD
Component : DD
file: dd_nvs_utils.py
author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-dtd
v1.0.0 : 13.01.2026
"""

__version__ = "1.0.0"

import esp32
import struct

# ================================================================
# FONCTIONS NVS DE BASE
# ================================================================

def set_str(namespace, key, value):
    """Écrit une chaîne UTF-8 dans NVS"""
    if not isinstance(value, str):
        raise TypeError("set_str() attend une chaîne (str)")
    
    nvs = esp32.NVS(namespace)
    nvs.set_blob(key, value.encode())
    nvs.commit()
    return True

def get_str(namespace, key, default="", max_len=32):
    """Lit une chaîne UTF-8 depuis NVS avec buffer"""
    try:
        nvs = esp32.NVS(namespace)
        buf = bytearray(max_len)
        n = nvs.get_blob(key, buf)
        return buf[:n].decode().rstrip("\x00")
    except:
        return default

def set_i32(namespace, key, value):
    """Écrit un int32 dans NVS"""
    if not isinstance(value, int):
        raise TypeError("set_i32() attend un int")
    
    nvs = esp32.NVS(namespace)
    nvs.set_i32(key, value)
    nvs.commit()
    return True

def get_i32(namespace, key, default=0):
    """Lit un int32 depuis NVS"""
    try:
        nvs = esp32.NVS(namespace)
        return nvs.get_i32(key)
    except:
        return default

def set_f32(namespace, key, value):
    """Écrit un float32 dans NVS (stocké comme blob)"""
    try:
        nvs = esp32.NVS(namespace)
        blob = struct.pack('f', float(value))
        nvs.set_blob(key, blob)
        nvs.commit()
        return True
    except:
        return False

def get_f32(namespace, key, default=0.0):
    """Lit un float32 depuis NVS"""
    try:
        nvs = esp32.NVS(namespace)
        buf = bytearray(4)
        n = nvs.get_blob(key, buf)
        if n >= 4:
            return struct.unpack('f', buf[:4])[0]
        return default
    except:
        return default

def delete_key(namespace, key):
    """Supprime une clé NVS"""
    try:
        nvs = esp32.NVS(namespace)
        nvs.erase_key(key)
        nvs.commit()
        return True
    except:
        return False

# ================================================================
# CONFIGURATION DD SPÉCIFIQUE
# ================================================================

NVS_NAMESPACE = "DTD"

def set_battery_calibration(factor):
    """
    Configure le facteur de calibration batterie
    
    Args:
        factor (float): Facteur de correction (0.5 - 2.0)
    
    Returns:
        bool: True si succès
    """
    if not isinstance(factor, (int, float)):
        print("[NVS] Erreur: facteur doit être numérique")
        return False
    
    if factor < 0.5 or factor > 2.0:
        print("[NVS] Erreur: facteur hors limites (0.5 - 2.0)")
        return False
    
    try:
        set_f32(NVS_NAMESPACE, "bat_cal_factor", factor)
        print("[NVS] Calibration batterie enregistrée: {:.3f}".format(factor))
        return True
    except Exception as e:
        print("[NVS] Erreur enregistrement calibration:", e)
        return False

def get_battery_calibration():
    """
    Lit le facteur de calibration batterie
    
    Returns:
        float: Facteur de correction (1.0 par défaut)
    """
    try:
        factor = get_f32(NVS_NAMESPACE, "bat_cal_factor", default=1.0)
        if 0.5 <= factor <= 2.0:
            return factor
        else:
            print("[NVS] Facteur invalide, utilisation défaut")
            return 1.0
    except:
        return 1.0

def set_ta_mac(mac_address):
    """
    Configure l'adresse MAC du Terminal Admin
    
    Args:
        mac_address (str): Adresse MAC format "AA:BB:CC:DD:EE:FF"
    
    Returns:
        bool: True si succès
    """
    if not isinstance(mac_address, str):
        print("[NVS] Erreur: MAC doit être une chaîne")
        return False
    
    # Validation format MAC (simple)
    if len(mac_address) < 17:
        print("[NVS] Erreur: MAC invalide (format: AA:BB:CC:DD:EE:FF)")
        return False
    
    try:
        set_str(NVS_NAMESPACE, "ta_mac", mac_address)
        print("[NVS] MAC du TA enregistré: {}".format(mac_address))
        return True
    except Exception as e:
        print("[NVS] Erreur enregistrement MAC:", e)
        return False

def get_ta_mac():
    """
    Lit l'adresse MAC du Terminal Admin
    
    Returns:
        str: Adresse MAC ou chaîne vide si non configuré
    """
    try:
        mac = get_str(NVS_NAMESPACE, "ta_mac", default="")
        return mac
    except:
        return ""

def show_config():
    """Affiche la configuration NVS actuelle"""
    print("=" * 60)
    print("CONFIGURATION DD (NVS)")
    print("=" * 60)
    
    # Calibration batterie
    bat_cal = get_battery_calibration()
    print("Calibration batterie: {:.3f}".format(bat_cal))
    
    # MAC du TA
    ta_mac = get_ta_mac()
    if ta_mac:
        print("MAC Terminal Admin: {}".format(ta_mac))
    else:
        print("MAC Terminal Admin: NON CONFIGURÉ")
    
    print("=" * 60)

# ================================================================
# UTILITAIRE DE CONFIGURATION INTERACTIF
# ================================================================

def config_interactive():
    """Menu interactif de configuration"""
    while True:
        print()
        print("=" * 60)
        print("CONFIGURATION DD - NVS")
        print("=" * 60)
        print()
        print("1. Configurer calibration batterie")
        print("2. Configurer MAC Terminal Admin")
        print("3. Afficher configuration")
        print("4. Quitter")
        print()
        
        choice = input("Choisir (1-4): ").strip()
        
        if choice == "1":
            _config_battery()
        elif choice == "2":
            _config_ta_mac()
        elif choice == "3":
            show_config()
        elif choice == "4":
            print("Terminé.")
            break
        else:
            print("Choix invalide!")

def _config_battery():
    """Configuration interactive calibration batterie"""
    print()
    print("=" * 60)
    print("CALIBRATION BATTERIE")
    print("=" * 60)
    print()
    
    # Valeur actuelle
    current = get_battery_calibration()
    print("Facteur actuel: {:.3f}".format(current))
    print()
    print("Plage valide: 0.500 à 2.000")
    print("Exemple: Si tension mesurée = 3.6V mais réelle = 3.7V")
    print("         alors facteur = 3.7 / 3.6 = 1.028")
    print()
    
    # Nouvelle valeur
    try:
        value_str = input("Nouveau facteur (ou vide pour annuler): ").strip()
        if not value_str:
            print("Annulé.")
            return
        
        new_factor = float(value_str)
        
        if set_battery_calibration(new_factor):
            print("✓ Configuration enregistrée")
            print()
            print("Redémarrer le DD pour appliquer:")
            print("  >>> import machine")
            print("  >>> machine.reset()")
        else:
            print("✗ Échec de la configuration")
            
    except ValueError:
        print("Erreur: valeur invalide!")

def _config_ta_mac():
    """Configuration interactive MAC Terminal Admin"""
    print()
    print("=" * 60)
    print("MAC TERMINAL ADMIN")
    print("=" * 60)
    print()
    
    # Valeur actuelle
    current = get_ta_mac()
    if current:
        print("MAC actuel: {}".format(current))
    else:
        print("MAC actuel: NON CONFIGURÉ")
    print()
    print("Format: AA:BB:CC:DD:EE:FF")
    print()
    
    # Nouvelle valeur
    mac_str = input("Nouvelle adresse MAC (ou vide pour annuler): ").strip()
    if not mac_str:
        print("Annulé.")
        return
    
    if set_ta_mac(mac_str):
        print("✓ Configuration enregistrée")
        print()
        print("Le DD peut maintenant communiquer avec le TA via ESP-NOW")
    else:
        print("✗ Échec de la configuration")

# ================================================================
# POINT D'ENTRÉE
# ================================================================

if __name__ == "__main__":
    config_interactive()