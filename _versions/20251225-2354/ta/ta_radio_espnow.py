"""
ta_radio_espnow.py - Module radio ESP-NOW (v4.1.0)
Communication sans fil avec les DD via ESP-NOW

Changements v4.1.0:
- RSSI fonctionnel via connexion WiFi du TA
- Le TA se connecte à un réseau WiFi pour obtenir le RSSI
- Configuration WiFi via ta_config.py

Changements v4.0.1:
- Correction gestion RSSI (peut retourner None)

Changements v4.0.0:
- Remplacement UART 433MHz par ESP-NOW
- Protocole identique: POLL:XX → ACK:XX:Y
"""

import network
import espnow
import time

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import ta_config as config

STATE_UNKNOWN = config.RADIO["STATE_UNKNOWN"]
STATE_PRESENT = config.RADIO["STATE_PRESENT"]
STATE_ABSENT = config.RADIO["STATE_ABSENT"]
DEBUG_MODE = config.MAIN["DEBUG_MODE"]


class RadioESPNow:
    """
    Gestion communication ESP-NOW
    Version 4.1.0 - MODE SÉQUENTIEL avec RSSI
    """
    
    def __init__(self, radio_config, logger, ui=None):
        self.first_pass = True
        self.config = radio_config
        self.logger = logger
        self.ui = ui
        
        # Statistiques
        self.stats = {
            "tx_count": 0,
            "rx_count": 0,
            "timeout_count": 0,
            "error_count": 0,
            "parse_errors": 0,
            "decode_errors": 0,
        }
        
        # RSSI par DD
        self.rssi_values = {}
        
        self.sta = None
        self.esp = None
        self.espnow_broken = False
        self.wifi_connected = False
        
        self._init_hardware()
    
    def _init_hardware(self):
        """Initialise ESP-NOW et connexion WiFi pour RSSI"""
        try:
            # Activer WiFi
            self.sta = network.WLAN(network.STA_IF)
            self.sta.active(True)
            
            # Tenter connexion WiFi pour RSSI (optionnel)
            wifi_config = config.HARDWARE.get("WIFI", {})
            ssid = wifi_config.get("SSID", "")
            password = wifi_config.get("PASSWORD", "")
            
            if ssid and password:
                self.logger.info("Connexion WiFi pour RSSI...", "radio")
                self.sta.connect(ssid, password)
                
                # Attendre connexion (max 10s)
                for i in range(20):
                    if self.sta.isconnected():
                        self.wifi_connected = True
                        self.logger.info("WiFi connecté: {}".format(self.sta.ifconfig()[0]), "radio")
                        break
                    time.sleep_ms(500)
                
                if not self.wifi_connected:
                    self.logger.warning("WiFi non connecté - RSSI indisponible", "radio")
            else:
                self.logger.info("Pas de config WiFi - RSSI indisponible", "radio")
            
            # Init ESP-NOW
            self.esp = espnow.ESPNow()
            self.esp.active(True)
            
            # Ajouter peer broadcast pour pouvoir envoyer en broadcast
            broadcast_mac = b'\xff\xff\xff\xff\xff\xff'
            try:
                self.esp.add_peer(broadcast_mac)
                self.logger.debug("Peer broadcast ajouté", "radio")
            except:
                pass
            
            # Récupérer MAC du TA
            ta_mac = self.get_mac()
            self.logger.info("ESP-NOW v4.1.0 initialisé", "radio")
            self.logger.info("TA MAC: {}".format(ta_mac), "radio")
            
        except Exception as e:
            self.logger.error("Erreur init ESP-NOW: {}".format(e), "radio")
            self.espnow_broken = True
    
    def get_mac(self):
        """Retourne MAC address du TA"""
        if self.sta:
            mac_bytes = self.sta.config('mac')
            return ':'.join('{:02X}'.format(b) for b in mac_bytes)
        return "UNKNOWN"
    
    def check_hardware(self):
        """Vérifie que le hardware est OK"""
        if self.espnow_broken:
            return False
        if self.esp is None:
            return False
        return True
    
    def _safe_decode(self, data):
        """Décodage sécurisé des bytes"""
        try:
            return data.decode('utf-8').strip()
        except:
            self.stats["decode_errors"] += 1
            return ""
    
    def get_rssi(self, dd_id=None):
        """
        Retourne RSSI du dernier paquet reçu
        Si dd_id spécifié, retourne RSSI de ce DD
        Fonctionne uniquement si WiFi connecté
        """
        if dd_id is not None:
            return self.rssi_values.get(dd_id, None)
        
        if not self.wifi_connected:
            return None
        
        try:
            return self.sta.status('rssi') if self.sta else None
        except:
            return None
    
    # ========================================================================
    # MODE SÉQUENTIEL ESP-NOW
    # ========================================================================
    
    async def _send_poll(self, dd_id):
        """Envoie POLL:XX via ESP-NOW broadcast"""
        try:
            msg = "POLL:{:02d}\n".format(dd_id)
            
            # Broadcast (tous les DD reçoivent, seul le bon répond)
            broadcast_mac = b'\xff\xff\xff\xff\xff\xff'
            self.esp.send(broadcast_mac, msg.encode())
            
            self.stats["tx_count"] += 1
            if DEBUG_MODE:
                self.logger.debug("→ POLL:{:02d}".format(dd_id), "radio")
            return True
                
        except Exception as e:
            self.stats["error_count"] += 1
            self.logger.error("Erreur envoi POLL: {}".format(e), "radio")
            return False
    
    async def _wait_ack_sequential(self, dd_id, timeout_ms):
        """Attend ACK:XX:Y en mode séquentiel"""
        deadline = time.ticks_ms() + timeout_ms
        
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            # Essayer de recevoir un message
            host, msg = self.esp.recv(0)  # Non-bloquant
            
            if msg:
                # Ajouter le DD comme peer si pas déjà fait
                try:
                    # Vérifier si déjà peer
                    peers = [p[0] for p in self.esp.get_peers()]
                    if host not in peers:
                        self.esp.add_peer(host)
                        mac_str = ':'.join('{:02X}'.format(b) for b in host)
                        self.logger.info("DD ajouté: {}".format(mac_str), "radio")
                except:
                    pass
                
                line = self._safe_decode(msg)
                
                if line.startswith("ACK:"):
                    try:
                        parts = line.split(":")
                        if len(parts) >= 3:
                            recv_id = int(parts[1])
                            state = int(parts[2])
                            
                            if recv_id == dd_id:
                                # Récupérer et stocker RSSI si WiFi connecté
                                rssi = None
                                if self.wifi_connected:
                                    try:
                                        rssi = self.sta.status('rssi')
                                        self.rssi_values[dd_id] = rssi
                                    except:
                                        pass
                                
                                self.stats["rx_count"] += 1
                                if DEBUG_MODE:
                                    if rssi is not None:
                                        self.logger.debug("← ACK DD{:02d} state={} RSSI:{}dBm".format(
                                            dd_id, state, rssi), "radio")
                                    else:
                                        self.logger.debug("← ACK DD{:02d} state={}".format(
                                            dd_id, state), "radio")
                                return state
                    except:
                        self.stats["parse_errors"] += 1
            
            await asyncio.sleep_ms(2)
        
        self.stats["timeout_count"] += 1
        return None
    
    async def poll_dd_sequential(self, dd_id):
        """Interroge un DD en mode séquentiel"""
        poll_sent = await self._send_poll(dd_id)
        if not poll_sent:
            return STATE_UNKNOWN
        
        timeout_ms = self.config.get("REPLY_TIMEOUT_MS", 300)
        state = await self._wait_ack_sequential(dd_id, timeout_ms)
        
        if state is None:
            return STATE_UNKNOWN
        elif state == 1:
            return STATE_PRESENT
        else:
            return STATE_ABSENT
    
    # ========================================================================
    # Interface unifiée pour compatibilité avec ta_app.py
    # ========================================================================
    
    async def poll_status(self):
        """
        Point d'entrée unifié - compatible avec ta_app.py
        Retourne: Liste de DDStatus (objets avec .dd_id et .state)
        """
        class DDStatus:
            def __init__(self, dd_id, state):
                self.dd_id = dd_id
                self.state = state
        
        # Mode séquentiel
        results = []
        for dd_id in config.RADIO["GROUP_IDS"]:
            state = await self.poll_dd_sequential(dd_id)
            results.append(DDStatus(dd_id, state))
        return results
    
    async def poll_all(self):
        """
        Interface alternative: retourne dict au lieu de liste
        Mode séquentiel
        """
        states = {}
        for dd_id in config.RADIO["GROUP_IDS"]:
            states[dd_id] = await self.poll_dd_sequential(dd_id)
        return states
    
    def get_stats(self):
        """Retourne les statistiques"""
        stats = self.stats.copy()
        # Ajouter info RSSI moyen si disponible
        if self.rssi_values:
            avg_rssi = sum(self.rssi_values.values()) / len(self.rssi_values)
            stats["avg_rssi"] = int(avg_rssi)
        stats["wifi_connected"] = self.wifi_connected
        return stats
    
    def reset_stats(self):
        """Réinitialise les statistiques"""
        for key in self.stats:
            self.stats[key] = 0
        self.rssi_values.clear()
    
    def get_statistics(self):
        """Retourne statistiques détaillées (compatible avec ta_app.py)"""
        return self.get_stats()