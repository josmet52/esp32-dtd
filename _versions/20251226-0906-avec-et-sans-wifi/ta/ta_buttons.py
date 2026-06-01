"""
Project: DTD - ta_buttons.py v2.1.0
Gestion des boutons - MODE PORTRAIT UNIQUEMENT

Fonctionnalités:
- Détection pression courte/longue
- Debouncing
- Passage en mode OTA (UP long 3s)
- Bouton DOWN disponible pour future fonctionnalité

v2.1.0:
- Suppression du switch landscape/portrait
- UP pression longue (3s) → Passage en mode OTA
- DOWN pression → Pas d'action (disponible pour futur)

Auteur: jom52
Date: 09.12.2025
Version: 2.1.0
"""

try:
    from machine import Pin
    import time
except ImportError:
    Pin = None
    time = None

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import ta_config as config
from ta_logger import get_logger

logger = get_logger()

class ButtonManager:
    """Gestionnaire des boutons simplifié - Mode portrait uniquement"""
    
    def __init__(self):
        """
        Initialise le gestionnaire de boutons
        """
        # Configuration boutons
        btn_config = config.HARDWARE.get("BUTTONS", {})
        self.pin_up = btn_config.get("PIN_UP", 0)
        self.pin_down = btn_config.get("PIN_DOWN", 21)
        
        # Timings
        btn_timing = config.BUTTONS if hasattr(config, "BUTTONS") else {}
        self.long_press_ms = btn_timing.get("LONG_MS", 800)
        self.ota_press_ms = 100  # 3 secondes pour mode OTA
        self.debounce_ms = btn_timing.get("DEBOUNCE_MS", 50)
        
        # Initialisation des pins
        self.btn_up = None
        self.btn_down = None
        
        if Pin:
            try:
                # Boutons avec pull-up (actif à LOW)
                self.btn_up = Pin(self.pin_up, Pin.IN, Pin.PULL_UP)
                self.btn_down = Pin(self.pin_down, Pin.IN, Pin.PULL_UP)
            except Exception as e:
                logger.error("Erreur init boutons: {}".format(e), "buttons")
        
        # État des boutons
        self.btn_up_pressed_time = 0
        self.btn_down_pressed_time = 0
        self.last_up_state = 1
        self.last_down_state = 1
    
    def _is_pressed(self, pin):
        """Vérifie si un bouton est pressé (actif à LOW avec pull-up)"""
        if not pin:
            return False
        return pin.value() == 0
    
    async def check_buttons(self):
        """
        Tâche async de surveillance des boutons

        Comportement:
        - UP court: Pas d'action
        - UP long (>3s): PASSAGE EN MODE OTA (reboot)
        - DOWN court: Pas d'action (disponible pour future fonctionnalité)
        - DOWN long: Pas d'action (disponible pour future fonctionnalité)
        """
        if not self.btn_up or not self.btn_down:
            logger.warning("Boutons non disponibles", "buttons")
            return
        
        while True:
            try:
                current_time = time.ticks_ms()
                
                # === BOUTON UP ===
                up_pressed = self._is_pressed(self.btn_up)
                
                if up_pressed and self.last_up_state == 1:
                    # Début de pression
                    self.btn_up_pressed_time = current_time
                    self.last_up_state = 0
                    logger.debug("UP: Appui détecté", "buttons")
                
                elif not up_pressed and self.last_up_state == 0:
                    # Fin de pression
                    press_duration = time.ticks_diff(current_time, self.btn_up_pressed_time)
                    self.last_up_state = 1

                    if press_duration > self.debounce_ms:
                        if press_duration >= self.ota_press_ms:
                            logger.info("UP: Pression TRÈS longue ({}ms) → MODE OTA".format(
                                press_duration), "buttons")
                            # Passage en mode OTA
                            self._enter_ota_mode()
                        elif press_duration >= self.long_press_ms:
                            logger.info("UP: Pression longue ({}ms) - ignorée".format(
                                press_duration), "buttons")
                        else:
                            logger.debug("UP: Pression courte ({}ms) - ignorée".format(
                                press_duration), "buttons")
                
                # === BOUTON DOWN ===
                down_pressed = self._is_pressed(self.btn_down)
                
                if down_pressed and self.last_down_state == 1:
                    # Début de pression
                    self.btn_down_pressed_time = current_time
                    self.last_down_state = 0
                    logger.debug("DOWN: Appui détecté", "buttons")
                
                elif not down_pressed and self.last_down_state == 0:
                    # Fin de pression
                    press_duration = time.ticks_diff(current_time, self.btn_down_pressed_time)
                    self.last_down_state = 1
                    
                    if press_duration > self.debounce_ms:
                        logger.info("DOWN: Pression ({}ms) - ignorée (fonctionnalité future)".format(
                            press_duration), "buttons")
                        # TODO: Action DOWN (future fonctionnalité)
                
                # Check toutes les 50ms
                await asyncio.sleep_ms(50)
                
            except Exception as e:
                logger.error("Erreur check_buttons: {}".format(e), "buttons")
                await asyncio.sleep_ms(100)

    def _enter_ota_mode(self):
        """
        Entre en mode OTA
        Arrête l'application normale et lance ta_ota
        """
        logger.info("="*50, "buttons")
        logger.info("PASSAGE EN MODE OTA - Reboot...", "buttons")
        logger.info("="*50, "buttons")

        try:
            import machine
            import time
            time.sleep(1)

            # Reboot - boot.py démarrera en normal, mais on peut lancer OTA ici
            from ta_ota import enter_ota_mode
            enter_ota_mode()

        except Exception as e:
            logger.error("Erreur passage mode OTA: {}".format(e), "buttons")