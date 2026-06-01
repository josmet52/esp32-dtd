"""
test_espnow_ta.py - Test ESP-NOW sur le TA avec RSSI
VERSION: 3.0.0

Changements v3.0.0:
- RSSI affiché si WiFi connecté
- Connexion WiFi optionnelle avant tests
"""

__version__ = "3.0.0"

import network
import espnow
import time

def get_version():
    """Affiche la version du script"""
    print("test_espnow_ta version: {}".format(__version__))
    return __version__

def connect_wifi(ssid=None, password=None):
    """
    Connecte le TA au WiFi pour activer le RSSI
    Si ssid/password non fournis, demande interactivement
    """
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    
    if not ssid:
        ssid = input("SSID WiFi (vide pour ignorer): ").strip()
        if not ssid:
            print("Pas de WiFi - RSSI indisponible")
            return False
        password = input("Mot de passe: ").strip()
    
    print("Connexion à '{}'...".format(ssid))
    sta.connect(ssid, password)
    
    for i in range(20):
        if sta.isconnected():
            print("✓ WiFi connecté: {}".format(sta.ifconfig()[0]))
            return True
        time.sleep(0.5)
    
    print("✗ WiFi non connecté - RSSI indisponible")
    return False

def get_ta_mac():
    """Affiche le MAC du TA"""
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    mac_bytes = sta.config('mac')
    mac_str = ':'.join('{:02X}'.format(b) for b in mac_bytes)
    print("MAC du TA: {}".format(mac_str))
    print("\nConfigurer ce MAC sur chaque DD avec:")
    print("nvs_utils.set_str('DTD', 'ta_mac', '{}')".format(mac_str))
    return mac_str

def get_rssi_safe(sta):
    """Récupère le RSSI si WiFi connecté, sinon retourne None"""
    if not sta.isconnected():
        return None
    try:
        return sta.status('rssi')
    except:
        return None

def test_basic():
    """Test de base ESP-NOW"""
    print("="*50)
    print("Test ESP-NOW de base v{}".format(__version__))
    print("="*50)
    
    # Init WiFi
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    print("✓ WiFi activé")
    
    # Init ESP-NOW
    esp = espnow.ESPNow()
    esp.active(True)
    print("✓ ESP-NOW activé")
    
    # Afficher MAC
    mac_str = get_ta_mac()
    
    # Ajouter peer broadcast
    broadcast_mac = b'\xff\xff\xff\xff\xff\xff'
    try:
        esp.add_peer(broadcast_mac)
        print("✓ Peer broadcast ajouté")
    except:
        pass
    
    # Test broadcast
    print("\nEnvoi d'un POLL en broadcast...")
    msg = b"POLL:00\n"
    esp.send(broadcast_mac, msg)
    print("✓ POLL envoyé")
    
    # Attendre réponse
    print("Attente de réponse (5s)...")
    
    for i in range(500):  # 500 x 10ms = 5s
        host, msg = esp.recv(0)
        if msg:
            mac_dd = ':'.join('{:02X}'.format(b) for b in host)
            rssi = get_rssi_safe(sta)
            
            print("\n✓ Réponse reçue!")
            print("  De: {}".format(mac_dd))
            print("  Message: {}".format(msg.decode().strip()))
            if rssi is not None:
                print("  RSSI: {} dBm".format(rssi))
            else:
                print("  RSSI: N/A (WiFi non connecté)")
            
            # Ajouter comme peer
            try:
                esp.add_peer(host)
                print("  → DD ajouté comme peer")
            except:
                pass
            break
        time.sleep(0.01)
    else:
        print("✗ Pas de réponse (timeout)")
    
    # Cleanup
    esp.active(False)
    print("\nTest terminé")

def test_poll_dd(dd_id):
    """Test POLL d'un DD spécifique"""
    print("="*50)
    print("Test POLL DD{:02d} v{}".format(dd_id, __version__))
    print("="*50)
    
    # Init
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    
    esp = espnow.ESPNow()
    esp.active(True)
    
    # Ajouter peer broadcast
    broadcast_mac = b'\xff\xff\xff\xff\xff\xff'
    try:
        esp.add_peer(broadcast_mac)
    except:
        pass
    
    print("Envoi POLL:{:02d}...".format(dd_id))
    msg = "POLL:{:02d}\n".format(dd_id).encode()
    esp.send(broadcast_mac, msg)
    
    # Attendre ACK
    print("Attente ACK (2s)...")
    
    for i in range(200):  # 200 x 10ms = 2s
        host, msg = esp.recv(0)
        if msg:
            line = msg.decode().strip()
            if line.startswith("ACK:"):
                mac_dd = ':'.join('{:02X}'.format(b) for b in host)
                
                parts = line.split(":")
                recv_id = int(parts[1])
                state = int(parts[2])
                rssi = get_rssi_safe(sta)
                
                print("\n✓ ACK reçu!")
                print("  DD: {:02d}".format(recv_id))
                print("  État: {} ({})".format(state, "PRESENT" if state == 1 else "ABSENT"))
                print("  MAC: {}".format(mac_dd))
                if rssi is not None:
                    print("  RSSI: {} dBm".format(rssi))
                else:
                    print("  RSSI: N/A (WiFi non connecté)")
                break
        time.sleep(0.002)
    else:
        print("✗ Pas d'ACK (timeout)")
    
    esp.active(False)
    print("\nTest terminé")

def test_all_dd():
    """Test séquentiel de tous les DD"""
    print("="*50)
    print("Test séquentiel de tous les DD v{}".format(__version__))
    print("="*50)
    
    # Init
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    
    esp = espnow.ESPNow()
    esp.active(True)
    
    # Ajouter peer broadcast
    broadcast_mac = b'\xff\xff\xff\xff\xff\xff'
    try:
        esp.add_peer(broadcast_mac)
    except:
        pass
    
    # Tester DD 0 à 7
    for dd_id in range(8):
        print("\nPOLL DD{:02d}...".format(dd_id))
        msg = "POLL:{:02d}\n".format(dd_id).encode()
        esp.send(broadcast_mac, msg)
        
        # Attendre ACK
        found = False
        
        for i in range(50):  # 50 x 10ms = 500ms
            host, msg = esp.recv(0)
            if msg:
                line = msg.decode().strip()
                if line.startswith("ACK:"):
                    parts = line.split(":")
                    recv_id = int(parts[1])
                    state = int(parts[2])
                    
                    if recv_id == dd_id:
                        rssi = get_rssi_safe(sta)
                        if rssi is not None:
                            print("  ✓ DD{:02d}: {} (RSSI: {} dBm)".format(
                                dd_id, "PRESENT" if state == 1 else "ABSENT", rssi))
                        else:
                            print("  ✓ DD{:02d}: {}".format(
                                dd_id, "PRESENT" if state == 1 else "ABSENT"))
                        found = True
                        break
            time.sleep(0.002)
        
        if not found:
            print("  ✗ DD{:02d}: Pas de réponse".format(dd_id))
    
    esp.active(False)
    print("\nTest terminé")

if __name__ == "__main__":
    print("\n=== Tests ESP-NOW pour TA v{} ===\n".format(__version__))
    print("Commandes disponibles:")
    print("  get_version()      - Afficher version")
    print("  connect_wifi()     - Connecter WiFi (pour RSSI)")
    print("  test_basic()       - Test de base")
    print("  test_poll_dd(N)    - Test DD spécifique")
    print("  test_all_dd()      - Test tous les DD")
    print("  get_ta_mac()       - Afficher MAC du TA")
    print("\nExemple avec RSSI:")
    print(">>> import test_espnow_ta")
    print(">>> test_espnow_ta.connect_wifi('MonWiFi', 'password')")
    print(">>> test_espnow_ta.test_basic()")
    print("\nExemple sans RSSI:")
    print(">>> import test_espnow_ta")
    print(">>> test_espnow_ta.test_basic()")