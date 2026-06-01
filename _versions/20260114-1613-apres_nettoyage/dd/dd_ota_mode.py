"""
project : DTD
Component : DD
file: dd_ota_mode.py
author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-dtd
v1.0.0 : 13.01.2026
"""

__version__ = "1.0.0"

import network
import socket
import json
import os
import machine
import time
import gc

try:
    import dd_nvs_utils as nvs_utils
except ImportError:
    nvs_utils = None

class OTAMode:
    def __init__(self, dd_id):
        self.dd_id = dd_id
        self.wlan = None
        self.connected = False
        self.ta_ssid = "TA_OTA"
        self.ta_password = "12345678"
        self.ta_ip = "192.168.4.1"
        self.ota_port = 8080
        
        # Socket UDP pour ecouter les commandes du TA
        self.udp_listen_sock = None
        
    def enable_wifi(self):
        print("[OTA] DD{:02d} - WiFi...".format(self.dd_id))
        
        # CRITIQUE: Liberer memoire AVANT d'activer WiFi
        gc.collect()
        
        # Desactiver AP si actif (libere memoire)
        try:
            ap = network.WLAN(network.AP_IF)
            if ap.active():
                print("[OTA] Désactivation AP...")
                ap.active(False)
                time.sleep_ms(100)
                gc.collect()
        except:
            pass
        
        # Activer STA avec precautions
        try:
            self.wlan = network.WLAN(network.STA_IF)
            
            # Si deja actif, le desactiver d'abord
            if self.wlan.active():
                print("[OTA] Reset WiFi...")
                self.wlan.active(False)
                time.sleep_ms(200)
                gc.collect()
            
            # Activer maintenant
            self.wlan.active(True)
            time.sleep_ms(500)
            
        except Exception as e:
            print("[OTA] ERREUR activation WiFi:", e)
            return False
        
        print("[OTA] Connexion {}...".format(self.ta_ssid))
        
        try:
            self.wlan.connect(self.ta_ssid, self.ta_password)
        except Exception as e:
            print("[OTA] ERREUR connect:", e)
            return False
        
        for _ in range(10):
            if self.wlan.isconnected():
                self.connected = True
                print("[OTA] OK! IP: {}".format(self.wlan.ifconfig()[0]))
                return True
            time.sleep(1)
        
        print("[OTA] Échec WiFi")
        return False
    
    def announce_to_ta(self):
        if not self.connected:
            return False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            msg = json.dumps({
                "dd_id": self.dd_id,
                "status": "ready"
            })
            sock.sendto(msg.encode(), (self.ta_ip, 8081))
            sock.close()
            return True
        except Exception as e:
            print("[OTA] Annonce fail:", e)
            return False
    
    def start_udp_listener(self):
        """Demarre socket UDP pour ecouter commandes du TA"""
        try:
            self.udp_listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_listen_sock.bind(('', 8082))
            self.udp_listen_sock.settimeout(1.0)
            print("[OTA] UDP listener sur port 8082")
            return True
        except Exception as e:
            print("[OTA] Erreur UDP listener:", e)
            return False
    
    def check_udp_command(self):
        """
        Verifie commande UDP du TA
        Returns: True si "announce_request" recu
        """
        if not self.udp_listen_sock:
            return False
        
        try:
            data, addr = self.udp_listen_sock.recvfrom(128)
            cmd = data.decode().strip()
            
            if cmd == "announce_request":
                print("[OTA] Commande: announce_request de {}".format(addr))
                return True
                
        except OSError:
            pass
        
        return False
    
    def download_file(self):
        print("[OTA] Téléchargement...")
        
        try:
            sock = socket.socket()
            sock.connect((self.ta_ip, self.ota_port))
            
            # Envoyer requete HTTP
            request = "GET /download/{} HTTP/1.1\r\nHost: {}\r\n\r\n".format(
                self.dd_id, self.ta_ip)
            sock.send(request.encode())
            
            # Lire headers
            headers = b""
            while b"\r\n\r\n" not in headers:
                chunk = sock.recv(1)
                if not chunk:
                    print("[OTA] Connexion fermée")
                    sock.close()
                    return None
                headers += chunk
            
            # Parser headers
            headers_str = headers.decode()
            
            # Verifier status code
            if "200 OK" not in headers_str:
                print("[OTA] Erreur serveur")
                sock.close()
                return None
            
            # Extraire filename
            filename = None
            
            # Essayer X-Filename d'abord
            for line in headers_str.split('\r\n'):
                if line.startswith('X-Filename:'):
                    filename = line.split(':', 1)[1].strip()
                    break
            
            # Sinon essayer Content-Disposition
            if not filename:
                for line in headers_str.split('\r\n'):
                    if line.startswith('Content-Disposition:'):
                        parts = line.split('filename=')
                        if len(parts) > 1:
                            filename = parts[1].strip().strip('"')
                            break
            
            if not filename:
                filename = "update.bin"
            
            print("[OTA] Fichier: {}".format(filename))
            
            # Lire data
            data = b""
            while True:
                chunk = sock.recv(512)
                if not chunk:
                    break
                data += chunk
            
            sock.close()
            
            # Sauvegarder
            with open(filename, 'wb') as f:
                f.write(data)
            
            print("[OTA] OK: {} octets".format(len(data)))
            return filename
            
        except Exception as e:
            print("[OTA] Erreur download:", e)
            import sys
            sys.print_exception(e)
            return None
    
    def apply_update(self, filename):
        """Applique la mise a jour"""
        print("[OTA] Application...")
        
        try:
            # Verifier que le fichier existe
            if filename not in os.listdir():
                print("[OTA] Fichier introuvable:", filename)
                return False
            
            print("[OTA] ✓ Mise à jour installée")
            return True
            
        except Exception as e:
            print("[OTA] Erreur apply:", e)
            return False
    
    def cleanup_and_reboot(self):
        """Nettoie et redémarre en mode normal"""
        print("[OTA] Nettoyage...")
        
        # Effacer flag OTA en NVS
        if nvs_utils:
            print("[OTA] Effacement flag OTA...")
            nvs_utils.set_i32("DTD", "ota_mode", 0)
        
        # Desactiver WiFi
        if self.wlan:
            self.wlan.active(False)
        
        print("[OTA] Reboot en mode NORMAL...")
        time.sleep(1)
        machine.reset()

def enter_ota_mode(dd_id):
    """Point d'entrée principal du mode OTA"""
    print("\n" + "="*50)
    print("MODE OTA ACTIF - DD{:02d}".format(dd_id))
    print("="*50)
    
    ota = OTAMode(dd_id)
    
    # Connexion WiFi
    if not ota.enable_wifi():
        print("[OTA] Échec WiFi - Abandon")
        time.sleep(2)
        if nvs_utils:
            nvs_utils.set_i32("DTD", "ota_mode", 0)
        machine.reset()
    
    # Demarrer listener UDP
    if not ota.start_udp_listener():
        print("[OTA] Échec UDP listener")
    
    # Boucle d'annonce periodique
    last_announce = time.time()
    announce_interval = 30
    
    print("[OTA] Attente mise à jour...")
    print("[OTA] Annonces toutes les {}s".format(announce_interval))
    
    while True:
        # Verifier commande UDP
        if ota.check_udp_command():
            print("[OTA] Annonce immédiate demandée")
            ota.announce_to_ta()
            last_announce = time.time()
        
        # Annonce periodique
        now = time.time()
        if now - last_announce >= announce_interval:
            print("[OTA] Annonce périodique...")
            ota.announce_to_ta()
            last_announce = now
        
        time.sleep(1)
    
    # Note: Cette partie n'est jamais atteinte dans le fonctionnement normal
    # Le TA doit fermer la connexion ou envoyer une commande speciale
    # pour declencher le telechargement