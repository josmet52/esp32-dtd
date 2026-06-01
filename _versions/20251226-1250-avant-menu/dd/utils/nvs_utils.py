"""
nvs_utils.py v1.0.1 - Utilitaires NVS (Non-Volatile Storage)

Description:
    Wrapper simplifié pour l'accès au NVS (Non-Volatile Storage) de l'ESP32.
    Permet de stocker et récupérer des données persistantes entre les redémarrages.

Types supportés:
    - string (UTF-8, via blob)
    - int32 (entier signé 32 bits)
    - float32 (flottant simple précision, via blob)

Utilisation:
    import utils.nvs_utils as nvs_utils
    
    # Écriture
    nvs_utils.set_str("DTD", "DD-type", "WROVER-T7")
    nvs_utils.set_i32("DTD", "ota_mode", 1)
    nvs_utils.set_f32("DTD", "bat_cal_factor", 1.028)
    
    # Lecture avec valeur par défaut
    module_type = nvs_utils.get_str("DTD", "DD-type", default="UNKNOWN")
    ota_flag = nvs_utils.get_i32("DTD", "ota_mode", default=0)
    cal_factor = nvs_utils.get_f32("DTD", "bat_cal_factor", default=1.0)
    
    # Suppression
    nvs_utils.delete_key("DTD", "old_key")

Notes:
    - Les chaînes sont limitées à max_len (32 par défaut)
    - Les floats sont stockés en little-endian
    - Les erreurs retournent la valeur par défaut sans lever d'exception
    
Auteur: Système DTD
Version: 1.0.1
Date: 08/12/2025
"""

__version__ = "1.0.1"

import esp32
import struct

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