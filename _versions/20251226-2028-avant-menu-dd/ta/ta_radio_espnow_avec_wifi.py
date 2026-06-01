"""
ta_radio_espnow.py - Module radio ESP-NOW (v5.1.2 - AVEC WiFi et RSSI)
Communication sans fil avec les DD via ESP-NOW

VERSION AVEC WiFi:
- Connexion WiFi OBLIGATOIRE au démarrage
- RSSI disponible pour tous les messages
- Message sur écran si WiFi non disponible

Changements v5.1.2:
- Correction affichage écran d'erreur (effacement complet)
- Utilisation amoled.RED et amoled.BLACK
- Police plus grande et plus visible

Changements v5.1.1:
- Gestion erreur WiFi avec affichage sur écran
- Réinitialisation WiFi après échec connexion
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
        """
        Initialise ESP-NOW AVEC connexion WiFi OBLIGATOIRE
        VERSION AVEC WiFi - RSSI disponible
        """
        try:
            # Activer WiFi
            self.sta = network.WLAN(network.STA_IF)
            self.sta.active(True)
            
            # Connexion WiFi OBLIGATOIRE
            wifi_config = config.HARDWARE.get("WIFI", {})
            ssid = wifi_config.get("SSID", "")
            password = wifi_config.get("PASSWORD", "")
            
            if not ssid or not password:
                msg = "ERREUR: Config WiFi manquante !"
                self.logger.error(msg, "radio")
                self.logger.error("Cette version nécessite WiFi pour RSSI", "radio")
                self.logger.error("Configurez SSID/PASSWORD dans ta_config.py", "radio")
                self.logger.error("OU utilisez version SANS WiFi (v5.0.0)", "radio")
                
                # Afficher message sur écran
                if self.ui:
                    self._display_error_screen(
                        "Config WiFi",
                        "manquante !",
                        "Editez ta_config.py",
                        "OU version v5.0.0"
                    )
                
                self.espnow_broken = True
                return
            
            self.logger.info("Connexion WiFi OBLIGATOIRE pour RSSI...", "radio")
            
            try:
                self.sta.connect(ssid, password)
                
                # Attendre connexion (max 15s)
                for i in range(30):
                    if self.sta.isconnected():
                        self.wifi_connected = True
                        self.logger.info("WiFi connecté: {}".format(self.sta.ifconfig()[0]), "radio")
                        break
                    time.sleep_ms(500)
            
            except Exception as e:
                self.logger.warning("Exception pendant connexion WiFi: {}".format(e), "radio")
                self.wifi_connected = False
            
            if not self.wifi_connected:
                self.logger.error("ERREUR: WiFi non connecté !", "radio")
                self.logger.error("Vérifiez que le router est allumé", "radio")
                self.logger.error("SSID: '{}'".format(ssid), "radio")
                
                # CRITIQUE: Réinitialiser WiFi pour éviter "Wifi Internal State Error"
                self.logger.info("Réinitialisation WiFi...", "radio")
                try:
                    self.sta.disconnect()
                except:
                    pass
                time.sleep_ms(100)
                self.sta.active(False)
                time.sleep_ms(100)
                self.sta.active(True)
                time.sleep_ms(100)
                
                # Afficher message sur écran
                if self.ui:
                    self._display_error_screen(
                        "WiFi requis !",
                        "Allumez router:",
                        ssid,
                        "puis rebootez TA"
                    )
                
                self.espnow_broken = True
                return
            
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
            self.logger.info("ESP-NOW v5.1.2 initialisé (AVEC WiFi + RSSI)", "radio")
            self.logger.info("TA MAC: {}".format(ta_mac), "radio")
            
        except Exception as e:
            self.logger.error("Erreur init ESP-NOW: {}".format(e), "radio")
            
            # Afficher message sur écran
            if self.ui:
                self._display_error_screen(
                    "Erreur WiFi !",
                    str(e)[:20],
                    "Allumez router",
                    "puis rebootez TA"
                )
            
            self.espnow_broken = True
    
    def _display_error_screen(self, line1, line2, line3, line4):
        """
        Affiche un message d'erreur sur l'écran
        
        Args:
            line1, line2, line3, line4: Lignes de texte à afficher
        """
        if not self.ui or not self.ui.tft:
            return
        
        try:
            import amoled
            try:
                import fonts.vga2_bold_16x32 as font_big
            except:
                try:
                    import fonts.vga2_16x32 as font_big
                except:
                    try:
                        import fonts.vga2_16x16 as font_big
                    except:
                        return
            
            # IMPORTANT: Effacer complètement l'écran AVANT d'afficher
            # Utiliser amoled.BLACK puis remplir en rouge
            self.ui.tft.fill(amoled.BLACK)
            time.sleep_ms(100)  # Laisser le temps à l'écran de se rafraîchir
            self.ui.tft.fill(amoled.RED)
            time.sleep_ms(100)
            
            # Position de départ (centré verticalement)
            y_start = 120
            y_spacing = 40
            
            # Afficher les 4 lignes en BLANC sur fond ROUGE
            lines = [line1, line2, line3, line4]
            for i, line in enumerate(lines):
                if line:
                    # Calculer position centrée
                    text_width = len(line) * 16  # 16 pixels par caractère
                    x = max(0, (self.ui.width - text_width) // 2)
                    y = y_start + (i * y_spacing)
                    
                    # Effacer la zone du texte en rouge pour être sûr
                    self.ui.tft.fill_rect(0, y - 2, self.ui.width, 36, amoled.RED)
                    
                    # Afficher texte blanc sur fond rouge
                    self.ui.tft.text(font_big, line, x, y, amoled.WHITE, amoled.RED)
            
        except Exception as e:
            self.logger.error("Erreur affichage écran: {}".format(e), "radio")
    
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
