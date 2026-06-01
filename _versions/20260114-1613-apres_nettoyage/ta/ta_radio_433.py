"""
project : DTD
Component : TA
file: ta_radio_433.py

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-dtd

v1.0.0 : 13.01.2026
"""

from machine import Pin, UART
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


class Radio433:
    """
    Gestion communication radio 433MHz via GT38
    Version 3.5.0 - MODE SÉQUENTIEL uniquement
    
    Compatibilité:
    - Méthode get_rssi() ajoutée (retourne None)
    - Compatible avec ta_app.py qui utilise ESP-NOW ou 433MHz
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
            "uart_errors": 0,
            "blocked_calls": 0,
            "flushed_bytes": 0,
            "parse_errors": 0,
            "max_loop_count": 0,
            "boot_messages": 0,
            "decode_errors": 0,
        }
        
        self.uart = None
        self.pin_set = None
        self.uart_config = None
        self.uart_broken = False
        
        self._init_hardware()
    
    def _init_hardware(self):
        """Initialise le hardware (UART + pin SET)"""
        self.uart_config = config.HARDWARE["UART_RADIO"]
        
        try:
            set_pin_num = self.uart_config.get("PIN_GT38_SET")
            if set_pin_num:
                self.pin_set = Pin(set_pin_num, Pin.OUT)
                self.pin_set.value(0)
                time.sleep_ms(50)
                self.pin_set.value(1)
                time.sleep_ms(50)
                self.logger.debug("Pin SET (GPIO{}) initialisée".format(set_pin_num), "radio")
            
            uart_index = self.uart_config.get("INDEX", 2)
            tx_pin = self.uart_config.get("TX", 43)
            rx_pin = self.uart_config.get("RX", 44)
            baud = self.uart_config.get("BAUD", 9600)
            timeout_ms = self.uart_config.get("TIMEOUT_MS", 100)
            
            rxbuf_size = 512
            
            self.uart = UART(
                uart_index,
                baudrate=baud,
                tx=Pin(tx_pin),
                rx=Pin(rx_pin),
                timeout=timeout_ms,
                rxbuf=rxbuf_size
            )
            
            self.logger.debug("UART{} initialisé: {}baud TX={} RX={} rxbuf={}".format(
                uart_index, baud, tx_pin, rx_pin, rxbuf_size), "radio")
                
        except Exception as e:
            self.logger.error("Erreur init UART: {}".format(e), "radio")
            self.uart_broken = True
    
    def check_hardware(self):
        """Vérifie que le hardware est OK"""
        if self.uart_broken:
            return False
        if self.uart is None:
            return False
        return True
    
    def _safe_decode(self, data):
        """Décodage sécurisé des bytes"""
        try:
            return data.decode('utf-8').strip()
        except:
            self.stats["decode_errors"] += 1
            return ""
    
    # ========================================================================
    # MODE SÉQUENTIEL
    # ========================================================================
    
    async def _send_poll(self, dd_id):
        """Envoie POLL:XX"""
        try:
            msg = "POLL:{:02d}\n".format(dd_id)
            written = self.uart.write(msg.encode())
            
            if written > 0:
                self.stats["tx_count"] += 1
                if DEBUG_MODE:
                    self.logger.debug("→ POLL:{:02d}".format(dd_id), "radio")
                return True
            else:
                self.logger.warning("Échec envoi POLL:{}".format(dd_id), "radio")
                return False
                
        except Exception as e:
            self.stats["uart_errors"] += 1
            self.logger.error("Erreur envoi POLL: {}".format(e), "radio")
            return False
    
    async def _wait_ack_sequential(self, dd_id, timeout_ms):
        """Attend ACK:XX:Y en mode séquentiel"""
        deadline = time.ticks_ms() + timeout_ms
        response_buffer = bytearray()
        
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            if self.uart and self.uart.any():
                chunk = self.uart.read(self.uart.any())
                if chunk:
                    response_buffer.extend(chunk)
                    
                    while b'\n' in response_buffer:
                        line_end = response_buffer.index(b'\n')
                        line = self._safe_decode(response_buffer[:line_end+1])
                        
                        if line.startswith("ACK:"):
                            try:
                                parts = line.split(":")
                                if len(parts) >= 3:
                                    recv_id = int(parts[1])
                                    state = int(parts[2])
                                    
                                    if recv_id == dd_id:
                                        self.stats["rx_count"] += 1
                                        if DEBUG_MODE:
                                            self.logger.debug("← ACK DD{:02d} state={}".format(
                                                dd_id, state), "radio")
                                        return state
                            except:
                                pass
                        
                        response_buffer = response_buffer[response_buffer.index(b'\n')+1:]
            
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
        return self.stats.copy()
    
    def reset_stats(self):
        """Réinitialise les statistiques"""
        for key in self.stats:
            self.stats[key] = 0
    
    def get_statistics(self):
        """Retourne statistiques détaillées (compatible avec ta_app.py)"""
        return dict(self.stats)
    
    def get_rssi(self, dd_id):
        """
        Retourne le RSSI pour un DD
        
        Args:
            dd_id (int): ID du détecteur
            
        Returns:
            None: Radio 433MHz n'a pas de RSSI
            
        Note:
            Cette méthode existe pour compatibilité avec les modules ESP-NOW.
            Le protocole 433MHz ne fournit pas d'information RSSI.
        """
        return None