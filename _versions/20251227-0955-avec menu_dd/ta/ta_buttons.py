"""
Project: DTD - ta_buttons.py v3.2.1
Gestion du bouton unique avec menu de configuration

v3.2.1:
- Correction mode OTA: notification DD avant lancement serveur
- Ajout _notify_dd_ota_mode() pour synchronisation OTA
- Attente 3s pour reboot DD avant lancement serveur OTA TA

v3.2.0:
- Ajout notification automatique DD lors changement mode radio
- Méthodes _notify_dd_mode_change(), _notify_dd_espnow(), _notify_dd_433()
- Synchronisation automatique TA ↔ DD

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
        
        # === NOTIFIER LES DD AVANT CHANGEMENT MODE RADIO ===
        if self.menu_selected_index in [MENU_ESP_NORMAL, MENU_ESP_RSSI, MENU_433MHZ]:
            await self._notify_dd_mode_change(self.menu_selected_index)
        
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
            await self._enter_ota_mode()
            
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
    
    async def _notify_dd_mode_change(self, menu_index):
        """
        Notifie tous les DD du changement de mode radio
        
        Args:
            menu_index (int): Index menu sélectionné (MENU_ESP_NORMAL, MENU_ESP_RSSI, MENU_433MHZ)
        
        Cette méthode envoie une commande MODE: à tous les DD pour qu'ils
        changent automatiquement de mode AVANT que le TA ne reboot.
        """
        # Déterminer la commande à envoyer
        if menu_index in [MENU_ESP_NORMAL, MENU_ESP_RSSI]:
            command = "MODE:ESPNOW\n"
            mode_name = "ESP-NOW"
        elif menu_index == MENU_433MHZ:
            command = "MODE:433MHZ\n"
            mode_name = "433MHz"
        else:
            return  # Pas de notification pour OTA/Reboot
        
        logger.info("Notification DD: changement vers {}".format(mode_name), "buttons")
        
        # Vérifier que l'app et le radio sont disponibles
        if not self.app or not hasattr(self.app, 'radio'):
            logger.warning("App ou radio non disponible pour notification DD", "buttons")
            return
        
        try:
            # Déterminer la méthode d'envoi selon le type de radio
            radio = self.app.radio
            radio_type = type(radio).__name__
            
            if 'ESPNow' in radio_type or 'espnow' in radio_type.lower():
                # Mode ESP-NOW : envoyer via ESP-NOW
                await self._notify_dd_espnow(command, mode_name)
            
            elif '433' in radio_type:
                # Mode 433MHz : envoyer via UART
                await self._notify_dd_433(command, mode_name)
            
            else:
                logger.warning("Type radio inconnu: {}".format(radio_type), "buttons")
        
        except Exception as e:
            logger.error("Erreur notification DD: {}".format(e), "buttons")
            # Continuer quand même (pas bloquant)
    
    async def _notify_dd_espnow(self, command, mode_name):
        """Envoie notification via ESP-NOW"""
        import ta_config as config
        
        # Envoyer à tous les DD configurés
        dd_ids = config.RADIO.get("GROUP_IDS", [0, 1, 2])
        
        for dd_id in dd_ids:
            try:
                # Envoyer la commande
                success = self.app.radio.send_to_dd(dd_id, command)
                
                if success:
                    logger.debug("DD{}: commande {} envoyée".format(dd_id, mode_name), "buttons")
                else:
                    logger.warning("DD{}: échec envoi commande".format(dd_id), "buttons")
                
                # Délai entre envois
                await asyncio.sleep_ms(100)
            
            except Exception as e:
                logger.warning("DD{}: erreur envoi - {}".format(dd_id, e), "buttons")
        
        logger.info("Notification ESP-NOW terminée, attente DD reboot (2s)...", "buttons")
        await asyncio.sleep_ms(2000)  # Attendre que les DD rebootent
    
    async def _notify_dd_433(self, command, mode_name):
        """Envoie notification via 433MHz UART"""
        import ta_config as config
        
        # Envoyer à tous les DD configurés
        dd_ids = config.RADIO.get("GROUP_IDS", [0, 1, 2])
        
        for dd_id in dd_ids:
            try:
                # Envoyer la commande via UART
                if hasattr(self.app.radio, 'uart') and self.app.radio.uart:
                    self.app.radio.uart.write(command.encode())
                    logger.debug("DD{}: commande {} envoyée".format(dd_id, mode_name), "buttons")
                
                # Délai entre envois
                await asyncio.sleep_ms(100)
            
            except Exception as e:
                logger.warning("DD{}: erreur envoi - {}".format(dd_id, e), "buttons")
        
        logger.info("Notification 433MHz terminée, attente DD reboot (2s)...", "buttons")
        await asyncio.sleep_ms(2000)  # Attendre que les DD rebootent
    
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
    
    async def _enter_ota_mode(self):
        """
        Entre en mode OTA après avoir notifié les DD
        
        Séquence:
        1. Envoyer "OTA:START" à tous les DD
        2. Attendre que les DD rebootent en mode OTA (3s)
        3. Lancer le mode OTA du TA
        """
        logger.info("="*50, "buttons")
        logger.info("PASSAGE EN MODE OTA", "buttons")
        logger.info("="*50, "buttons")
        
        # === ÉTAPE 1: NOTIFIER LES DD ===
        logger.info("Notification DD: passage en mode OTA...", "buttons")
        await self._notify_dd_ota_mode()
        
        # === ÉTAPE 2: ATTENDRE LES DD ===
        logger.info("Attente reboot DD (3 secondes)...", "buttons")
        await asyncio.sleep_ms(3000)
        
        # === ÉTAPE 3: LANCER MODE OTA TA ===
        logger.info("Lancement mode OTA TA...", "buttons")
        
        try:
            from ta_ota import enter_ota_mode
            enter_ota_mode()
            
        except Exception as e:
            logger.error("Erreur passage mode OTA: {}".format(e), "buttons")
    
    async def _notify_dd_ota_mode(self):
        """
        Notifie tous les DD de passer en mode OTA
        
        Envoie la commande "OTA:START" qui déclenche:
        - Enregistrement flag OTA en NVS
        - Reboot du DD
        - Lancement ota_mode.py au boot
        """
        if not self.app or not hasattr(self.app, 'radio'):
            logger.warning("App ou radio non disponible pour notification DD", "buttons")
            return
        
        try:
            # Déterminer la méthode d'envoi selon le type de radio
            radio = self.app.radio
            radio_type = type(radio).__name__
            
            if 'ESPNow' in radio_type or 'espnow' in radio_type.lower():
                # Mode ESP-NOW
                await self._notify_dd_ota_espnow()
            
            elif '433' in radio_type:
                # Mode 433MHz
                await self._notify_dd_ota_433()
            
            else:
                logger.warning("Type radio inconnu: {}".format(radio_type), "buttons")
        
        except Exception as e:
            logger.error("Erreur notification DD OTA: {}".format(e), "buttons")
    
    async def _notify_dd_ota_espnow(self):
        """Envoie notification OTA via ESP-NOW"""
        import ta_config as config
        
        dd_ids = config.RADIO.get("GROUP_IDS", [0, 1, 2])
        
        for dd_id in dd_ids:
            try:
                # Envoyer commande OTA:START
                command = "OTA:START\n"
                
                # Utiliser méthode d'envoi disponible
                if hasattr(self.app.radio, 'send_to_dd'):
                    success = self.app.radio.send_to_dd(dd_id, command)
                elif hasattr(self.app.radio, 'esp'):
                    # Broadcast ESP-NOW
                    if isinstance(command, str):
                        command = command.encode()
                    self.app.radio.esp.send(None, command, False)
                    success = True
                else:
                    success = False
                
                if success:
                    logger.info("DD{}: commande OTA envoyée".format(dd_id), "buttons")
                else:
                    logger.warning("DD{}: échec envoi OTA".format(dd_id), "buttons")
                
                # Attendre ACK ou timeout
                await asyncio.sleep_ms(200)
            
            except Exception as e:
                logger.warning("DD{}: erreur OTA - {}".format(dd_id, e), "buttons")
        
        logger.info("Notification OTA ESP-NOW terminée", "buttons")
    
    async def _notify_dd_ota_433(self):
        """Envoie notification OTA via 433MHz UART"""
        import ta_config as config
        
        dd_ids = config.RADIO.get("GROUP_IDS", [0, 1, 2])
        
        # En 433MHz, on broadcast la commande (pas d'adressage individuel)
        try:
            command = "OTA:START\n"
            if hasattr(self.app.radio, 'uart') and self.app.radio.uart:
                self.app.radio.uart.write(command.encode())
                logger.info("Commande OTA envoyée via UART", "buttons")
            
            # Attendre un peu pour que tous les DD reçoivent
            await asyncio.sleep_ms(500)
        
        except Exception as e:
            logger.error("Erreur envoi OTA UART: {}".format(e), "buttons")
        
        logger.info("Notification OTA 433MHz terminée", "buttons")
    
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