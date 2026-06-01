"""
ta_radio_espnow.py - Module radio ESP-NOW v6.1.0
Communication sans fil avec les DD via ESP-NOW

CARACTERISTIQUES:
- Communication ESP-NOW pure (sans WiFi)
- Performance maximale
- Pas de mesure RSSI (mode WiFi supprime)
- Code simplifie et robuste

Changements v6.1.0 (27.12.2025):
- Ajout methode send_to_dd() pour notification changement mode
- Support synchronisation automatique TA → DD

Changements v6.0.0 (27.12.2025):
- Fichier unique pour ESP-NOW (fusion de _normal et _rssi)
- Suppression complete du mode RSSI
- Simplification de l'architecture

Changements v5.0.0:
- Suppression complete de la gestion WiFi
- ESP-NOW uniquement
- Code simplifie et robuste
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
        
        # Pas de RSSI dans cette version
        
        self.sta = None
        self.esp = None
        self.espnow_broken = False
        
        self._init_hardware()
    
    def _init_hardware(self):
        """
        Initialise ESP-NOW SANS connexion WiFi
        VERSION SANS WiFi - Pas de RSSI
        """
        try:
            # Activer WiFi (nécessaire pour ESP-NOW mais pas de connexion réseau)
            self.sta = network.WLAN(network.STA_IF)
            self.sta.active(True)
            
            self.logger.info("WiFi actif (pas de connexion réseau)", "radio")
            
            # Init ESP-NOW
            self.esp = espnow.ESPNow()
            self.esp.active(True)
            
            # Ajouter peer broadcast
            broadcast_mac = b'\xff\xff\xff\xff\xff\xff'
            try:
                self.esp.add_peer(broadcast_mac)
                self.logger.debug("Peer broadcast ajouté", "radio")
            except:
                pass
            
            # MAC du TA
            ta_mac = self.get_mac()
            self.logger.info("ESP-NOW v5.0.0 initialisé (SANS WiFi)", "radio")
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
        VERSION SANS WiFi: RSSI non disponible
        Retourne toujours None
        """
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
                                # Pas de RSSI dans cette version
                                
                                self.stats["rx_count"] += 1
                                if DEBUG_MODE:
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
        """Retourne les statistiques (sans RSSI)"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Réinitialise les statistiques"""
        for key in self.stats:
            self.stats[key] = 0
    
    def get_statistics(self):
        """Retourne statistiques detaillees (compatible avec ta_app.py)"""
        return self.get_stats()
    
    def send_to_dd(self, dd_id, command):
        """
        Envoie une commande a un DD specifique (pour notification changement mode)
        
        Args:
            dd_id (int): ID du DD cible (utilise pour logs uniquement)
            command (str): Commande a envoyer (ex: "MODE:ESPNOW\n")
        
        Returns:
            bool: True si envoi reussi, False sinon
        
        Note: La commande est envoyee en broadcast car tous les DD doivent
        recevoir la meme commande MODE: pour se synchroniser avec le TA.
        """
        try:
            # Broadcast la commande (tous les DD recevront et executeront)
            broadcast_mac = b'\xff\xff\xff\xff\xff\xff'
            
            # Envoyer la commande directement (ex: "MODE:ESPNOW\n")
            self.esp.send(broadcast_mac, command.encode())
            
            self.logger.debug("Commande broadcast: {}".format(command.strip()), "radio")
            return True
            
        except Exception as e:
            self.logger.error("Erreur envoi commande: {}".format(e), "radio")
            return False