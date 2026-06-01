"""
Project: DTD - ta_buttons.py v3.1.2
Gestion du bouton unique avec menu de configuration

v3.1.2:
- Restauration portrait avant reboot/OTA
- Temps confirmation augmenté (1s)

v3.1.1:
- Ajout is_menu_visible() pour bloquer rafraîchissement UI
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
from ta_nvs_config import NVSConfig, RADIO_MODE_ESP_NORMAL, RADIO_MODE_ESP_RSSI, RADIO_MODE_433
from ta_menu_ui import MenuUI, MENU_ESP_NORMAL, MENU_ESP_RSSI, MENU_433MHZ, MENU_OTA, MENU_REBOOT

logger = get_logger()

# États du gestionnaire de boutons
STATE_NORMAL = 0    # Fonctionnement normal
STATE_MENU = 1      # Menu affiché

class ButtonManager:
    """Gestionnaire des boutons avec menu de configuration"""
    
    def __init__(self):
        """Initialise le gestionnaire de boutons"""
        # Configuration boutons
        btn_config = config.HARDWARE.get("BUTTONS", {})
        self.pin_up = btn_config.get("PIN_UP", 0)
        self.pin_down = btn_config.get("PIN_DOWN", 21)
        
        # Timings (bouton unique)
        self.short_press_ms = 50           # Minimum pour pression courte
        self.long_press_ms = 1500          # 1.5s pour menu ou validation
        self.debounce_ms = 50
        
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
        
        # État du menu
        self.state = STATE_NORMAL
        self.menu_selected_index = 0
        self.menu_ui = None
        
        # Référence à l'app (sera set par l'app)
        self.app = None
    
    def is_menu_visible(self):
        """
        Retourne True si le menu est actuellement affiché
        
        Returns:
            bool: True si menu visible, False sinon
        """
        return self.state == STATE_MENU
    
    def set_ui(self, ui):
        """
        Définit l'UI pour l'affichage du menu
        
        Args:
            ui: Instance de UIPortrait
        """
        self.menu_ui = MenuUI(ui)
    
    def _is_pressed(self, pin):
        """Vérifie si un bouton est pressé (actif à LOW avec pull-up)"""
        if not pin:
            return False
        return pin.value() == 0
    
    async def check_buttons(self):
        """Tâche async de surveillance du bouton unique (UP)"""
        if not self.btn_up:
            logger.warning("Bouton non disponible", "buttons")
            return
        
        while True:
            try:
                current_time = time.ticks_ms()
                
                # === BOUTON UP (unique bouton actif) ===
                up_pressed = self._is_pressed(self.btn_up)
                
                if up_pressed and self.last_up_state == 1:
                    # Début de pression
                    self.btn_up_pressed_time = current_time
                    self.last_up_state = 0
                    logger.debug("Bouton: Appui détecté", "buttons")
                
                elif not up_pressed and self.last_up_state == 0:
                    # Fin de pression
                    press_duration = time.ticks_diff(current_time, self.btn_up_pressed_time)
                    self.last_up_state = 1
                    
                    if press_duration > self.debounce_ms:
                        await self._handle_button_release(press_duration)
                
                # Check toutes les 50ms
                await asyncio.sleep_ms(50)
                
            except Exception as e:
                logger.error("Erreur check_buttons: {}".format(e), "buttons")
                await asyncio.sleep_ms(100)
    
    async def _handle_button_release(self, press_duration):
        """
        Gère le relâchement du bouton selon l'état
        
        Args:
            press_duration (int): Durée de la pression en ms
        """
        if self.state == STATE_NORMAL:
            # Mode normal
            if press_duration >= self.long_press_ms:
                # Pression longue → Afficher menu
                logger.info("Pression longue ({}ms) → MENU".format(
                    press_duration), "buttons")
                await self._show_menu()
                
            else:
                # Pression courte → Ignorée en mode normal
                logger.debug("Pression courte ({}ms) - ignorée".format(
                    press_duration), "buttons")
        
        elif self.state == STATE_MENU:
            # Menu affiché
            if press_duration >= self.long_press_ms:
                # Pression longue → Valider sélection
                logger.info("Menu: Validation option {}".format(
                    self.menu_selected_index), "buttons")
                await self._validate_menu_selection()
                
            else:
                # Pression courte → Sélection suivante
                logger.info("Menu: Sélection suivante", "buttons")
                await self._menu_next_item()
    
    async def _show_menu(self):
        """Affiche le menu de configuration"""
        if not self.menu_ui:
            logger.error("Menu UI non disponible", "buttons")
            return
        
        self.state = STATE_MENU
        self.menu_selected_index = 0
        
        # Afficher le menu
        self.menu_ui.show_menu(self.menu_selected_index)
        logger.info("Menu affiché", "buttons")
    
    async def _menu_next_item(self):
        """Passe à l'option suivante du menu (cyclique)"""
        self.menu_selected_index = (self.menu_selected_index + 1) % 5
        
        # Rafraîchir l'affichage
        self.menu_ui.show_menu(self.menu_selected_index)
        logger.debug("Menu: Sélection {}".format(self.menu_selected_index), "buttons")
    
    async def _validate_menu_selection(self):
        """Valide et exécute l'option sélectionnée du menu"""
        # Afficher confirmation
        self.menu_ui.show_confirmation(self.menu_selected_index)
        await asyncio.sleep_ms(1000)  # 1s pour voir la confirmation
        
        # Restaurer mode portrait avant reboot/OTA
        self.menu_ui.hide_menu()
        
        # Revenir en mode normal
        self.state = STATE_NORMAL
        
        # Exécuter l'action
        if self.menu_selected_index == MENU_ESP_NORMAL:
            logger.info("Activation: ESP-NOW Normal", "buttons")
            self._set_radio_mode_and_reboot(RADIO_MODE_ESP_NORMAL)
            
        elif self.menu_selected_index == MENU_ESP_RSSI:
            logger.info("Activation: ESP-NOW RSSI", "buttons")
            self._set_radio_mode_and_reboot(RADIO_MODE_ESP_RSSI)
            
        elif self.menu_selected_index == MENU_433MHZ:
            logger.info("Activation: Radio 433MHz", "buttons")
            self._set_radio_mode_and_reboot(RADIO_MODE_433)
            
        elif self.menu_selected_index == MENU_OTA:
            logger.info("Activation: OTA Update", "buttons")
            self._enter_ota_mode()
            
        elif self.menu_selected_index == MENU_REBOOT:
            logger.info("Activation: Reboot", "buttons")
            self._reboot()
        
        # Si on arrive ici (pas de reboot), restaurer UI
        # Note: Normalement on ne devrait pas arriver ici car les actions rebootent
        if self.app and hasattr(self.app, 'ui'):
            self.app.ui.status("Menu ferme")
            # Forcer un rafraîchissement complet
            if hasattr(self.app, '_initialize_display'):
                self.app._initialize_display()
                self.app._initialize_display()
    
    def _set_radio_mode_and_reboot(self, mode):
        """
        Enregistre le mode radio en NVS et redémarre
        
        Args:
            mode (int): Mode radio à activer
        """
        logger.info("Enregistrement mode radio: {}".format(
            NVSConfig.get_mode_name(mode)), "buttons")
        
        # Enregistrer en NVS
        if NVSConfig.set_radio_mode(mode):
            logger.info("Mode enregistré avec succès", "buttons")
            # Redémarrer
            self._reboot()
        else:
            logger.error("Erreur enregistrement mode", "buttons")
    
    def _enter_ota_mode(self):
        """Entre en mode OTA"""
        logger.info("="*50, "buttons")
        logger.info("PASSAGE EN MODE OTA - Reboot...", "buttons")
        logger.info("="*50, "buttons")
        
        try:
            import time
            time.sleep(1)
            
            from ta_ota import enter_ota_mode
            enter_ota_mode()
            
        except Exception as e:
            logger.error("Erreur passage mode OTA: {}".format(e), "buttons")
    
    def _reboot(self):
        """Redémarre le système"""
        logger.info("="*50, "buttons")
        logger.info("REBOOT SYSTÈME...", "buttons")
        logger.info("="*50, "buttons")
        
        try:
            import machine
            import time
            time.sleep(1)
            machine.reset()
            
        except Exception as e:
            logger.error("Erreur reboot: {}".format(e), "buttons")