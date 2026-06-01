"""
project : DTD
Component : TA
file: ta_app.py

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-dtd

v1.0.0 : 13.01.2026
"""

import ta_config as config
from ta_logger import get_logger
import time

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

try:
    from machine import WDT
except ImportError:
    WDT = None

try:
    from machine import ADC
except ImportError:
    ADC = None

from ta_ui_portrait import UIPortrait
from ta_buttons import ButtonManager
# Import radio supprimé, chargé dynamiquement par ta_main

STATE_UNKNOWN = config.RADIO["STATE_UNKNOWN"]
STATE_PRESENT = config.RADIO["STATE_PRESENT"]
STATE_ABSENT = config.RADIO["STATE_ABSENT"]

logger = get_logger()


class TaApp:
    def __init__(self, radio_module=None, tft=None, ui=None, radio=None, button_manager=None):

        # UI portrait uniquement
        self.ui = ui if ui else UIPortrait()

        # Boutons avec menu
        self.button_manager = button_manager if button_manager else ButtonManager()
        # Référence pour accès aux méthodes de l'app
        self.button_manager.app = self
        # Initialiser le menu UI
        self.button_manager.set_ui(self.ui)

        # Radio (chargée dynamiquement selon NVS)
        if radio:
            # Instance radio passee directement
            self.radio = radio
        elif radio_module:
            # Module radio passe par ta_main
            # Determiner la classe Radio du module
            if hasattr(radio_module, 'RadioESPNow'):
                RadioClass = radio_module.RadioESPNow
            elif hasattr(radio_module, 'Radio433'):
                RadioClass = radio_module.Radio433
            else:
                # Fallback
                from ta_radio_espnow import RadioESPNow as RadioClass
            
            self.radio = RadioClass(config.RADIO, logger, ui=self.ui)
        else:
            # Fallback si rien n'est passe
            from ta_radio_espnow import RadioESPNow as RadioClass
            self.radio = RadioClass(config.RADIO, logger, ui=self.ui)
        
        self.hw_ok = self.radio.check_hardware()
        
        if not self.hw_ok:
            logger.error("Hardware ESP-NOW non disponible - Arrêt", "app")
            # Message sur UI si pas déjà fait par radio
            if self.ui and not hasattr(self.radio, 'espnow_broken'):
                self.ui.status("ERREUR: Hardware ESP-NOW")

        # États des DD
        self.states = {dd_id: STATE_UNKNOWN for dd_id in config.RADIO["GROUP_IDS"]}

        # Test / debug
        self.testing_id = None

        # Initialisation affichage SEULEMENT si hardware OK
        if self.hw_ok:
            self._initialize_display()
        else:
            # Hardware en erreur - l'écran rouge reste visible
            logger.warning("Affichage normal non initialisé (hardware en erreur)", "app")

        # Watchdog
        self.wdt = None
        if config.MAIN.get("WATCHDOG_ENABLED", False) and WDT:
            try:
                self.wdt = WDT(timeout=config.MAIN.get("WATCHDOG_TIMEOUT_MS", 30000))
                logger.info("Watchdog activé", "app")
            except Exception as e:
                logger.error("Erreur watchdog: {}".format(e), "app")

        # Stats
        self.loop_count = 0
        self.error_count = 0
        self.last_status_update = 0

        # Message initial SEULEMENT si hardware OK
        if self.hw_ok:
            self.ui.status("Init OK - ESP-NOW")
        # Sinon l'écran d'erreur rouge reste visible
        
        # Initialisation ADC batterie
        self._init_battery_adc()

    def _initialize_display(self):
        """Initialise l'affichage avec tous les DD en état inconnu"""
        try:
            for idx, dd_id in enumerate(config.RADIO["GROUP_IDS"]):
                self.ui.update_group(idx, state=None)
            self.ui.render_dirty()
        except Exception as e:
            logger.error("Erreur initialisation affichage: {}".format(e), "app")

    def _init_battery_adc(self):
        """Initialise l'ADC pour la lecture de la batterie"""
        self.battery_adc = None
        if ADC:
            try:
                bat_config = config.HARDWARE.get("BATTERY", {})
                adc_pin = bat_config.get("ADC_PIN", 4)
                self.battery_adc = ADC(adc_pin)
                # Configuration de l'atténuation pour lire jusqu'à ~3.3V
                if hasattr(self.battery_adc, 'atten'):
                    self.battery_adc.atten(ADC.ATTN_11DB)  # 0-3.3V
                logger.info("ADC batterie initialise sur GPIO{}".format(adc_pin), "app")
            except Exception as e:
                logger.error("Erreur init ADC batterie: {}".format(e), "app")
                self.battery_adc = None

    def read_battery_voltage(self):
        """Lit la tension de la batterie et retourne le voltage"""
        if not self.battery_adc:
            return None
        
        try:
            bat_config = config.HARDWARE.get("BATTERY", {})
            voltage_divider = bat_config.get("VOLTAGE_DIVIDER", 2.0)
            vref = bat_config.get("VREF", 3.3)
            
            # Lecture de l'ADC (valeur 0-4095 sur ESP32)
            raw_value = self.battery_adc.read()
            
            # Conversion en tension
            voltage_adc = (raw_value / 4095.0) * vref
            voltage_bat = voltage_adc * voltage_divider
            
            return voltage_bat
        except Exception as e:
            logger.error("Erreur lecture batterie: {}".format(e), "app")
            return None

    def get_battery_percentage(self, voltage):
        """
        Calcule le pourcentage de charge basé sur la courbe de décharge réelle Li-Ion
        """
        if voltage is None:
            return None
        
        # Table de correspondance Voltage → Pourcentage
        voltage_table = [
            (4.20, 100), (4.15, 95), (4.11, 90), (4.08, 85), (4.02, 80),
            (3.98, 75), (3.95, 70), (3.91, 65), (3.87, 60), (3.85, 55),
            (3.84, 50), (3.82, 45), (3.80, 40), (3.79, 35), (3.77, 30),
            (3.75, 25), (3.73, 20), (3.71, 15), (3.69, 10), (3.61, 5),
            (3.27, 0)
        ]
        
        # Interpolation linéaire
        for i in range(len(voltage_table) - 1):
            v_high, pct_high = voltage_table[i]
            v_low, pct_low = voltage_table[i + 1]
            
            if voltage >= v_low:
                if voltage >= v_high:
                    return pct_high
                pct = pct_low + (pct_high - pct_low) * (voltage - v_low) / (v_high - v_low)
                return int(pct)
        
        return 0

    def display_battery_info(self):
        """Affiche les informations de batterie"""
        voltage = self.read_battery_voltage()
        if voltage is None:
            return
        
        percentage = self.get_battery_percentage(voltage)
        
        # Mettre à jour l'UI
        self.ui.update_battery_info(voltage)
        
        if percentage is not None:
            msg = "Bat: {:.2f}V ({}%)".format(voltage, percentage)
        else:
            msg = "Bat: {:.2f}V".format(voltage)
        
        logger.info(msg, "app")

    def feed_watchdog(self):
        """Nourrit le watchdog si activé"""
        if self.wdt:
            self.wdt.feed()

    # ========================================================================
    # GESTION TEST DD INDIVIDUEL
    # ========================================================================

    def start_testing_dd(self, dd_id):
        """Commence le test d'un DD spécifique"""
        if dd_id in config.RADIO["GROUP_IDS"]:
            self.testing_id = dd_id
            logger.info("Test DD{} démarré".format(dd_id), "app")
        else:
            logger.warning("DD{} non trouvé dans GROUP_IDS".format(dd_id), "app")

    def stop_testing_dd(self):
        """Arrête le test du DD"""
        if self.testing_id is not None:
            logger.info("Test DD{} arrêté".format(self.testing_id), "app")
            self.testing_id = None

    # ========================================================================
    # MISE À JOUR INTERFACE
    # ========================================================================

    def _update_status_message(self):
        """Met à jour le message de statut"""
        try:
            present_count = sum(1 for s in self.states.values() if s == STATE_PRESENT)
            absent_count = sum(1 for s in self.states.values() if s == STATE_ABSENT)
            unknown_count = sum(1 for s in self.states.values() if s == STATE_UNKNOWN)

            if self.testing_id:
                msg = "Test DD{} en cours...".format(self.testing_id)
            elif unknown_count == len(self.states):
                msg = "Scan {} detecteurs...".format(len(self.states))
            else:
                msg = "ON:{} OFF:{} ?:{}  L:{}".format(
                    present_count, absent_count, unknown_count, self.loop_count)

            # Ajouter RSSI moyen si disponible et mettre à jour l'UI
            if hasattr(self.radio, "get_stats"):
                stats = self.radio.get_stats()  # Appeler get_stats() pour avoir avg_rssi calculé
                if stats.get("error_count", 0) > 0:
                    msg += " ERR:{}".format(stats["error_count"])
                # Récupérer et passer RSSI moyen à l'UI
                avg_rssi = stats.get("avg_rssi")
                if avg_rssi:
                    msg += " RSSI:{}".format(avg_rssi)
                    # Mettre à jour l'UI avec RSSI moyen
                    self.ui.update_avg_rssi(avg_rssi)

            self.ui.status(msg)

        except Exception as e:
            logger.error("Erreur update_status_message: {}".format(e), "app")

    async def _print_stats(self):
        """Tâche périodique pour afficher les stats en mode debug"""
        while True:
            try:
                present = sum(1 for s in self.states.values() if s == STATE_PRESENT)
                absent = sum(1 for s in self.states.values() if s == STATE_ABSENT)
                unknown = sum(1 for s in self.states.values() if s == STATE_UNKNOWN)
                
                # Stats radio
                stats = self.radio.get_stats()
                avg_rssi = stats.get("avg_rssi", "N/A")
                
                logger.debug("STATS: P={} A={} U={} loops={} errors={} RSSI:{}".format(
                    present, absent, unknown, self.loop_count, self.error_count, avg_rssi
                ), "app")
            except Exception as e:
                logger.error("Erreur _print_stats: {}".format(e), "app")
            await asyncio.sleep_ms(2000)

    async def _refresh_ui(self):
        """Rafraîchit l'affichage de l'état des DD"""
        try:
            # Mettre à jour les états des DD
            for idx, dd_id in enumerate(config.RADIO["GROUP_IDS"]):
                st = self.states.get(dd_id, STATE_UNKNOWN)

                if st == STATE_PRESENT:
                    state = True
                elif st == STATE_ABSENT:
                    state = False
                else:
                    state = None

                self.ui.update_group(idx, state=state)

            # Basculer l'état du heartbeat
            if hasattr(self.ui, 'toggle_heartbeat'):
                self.ui.toggle_heartbeat()

            # Rafraîchir l'affichage
            self.ui.render_dirty()

        except Exception as e:
            logger.error("Erreur refresh UI: {}".format(e), "app")
            self.error_count += 1

    async def _update_states(self):
        """Lit les états depuis la radio"""
        statuses = await self.radio.poll_status()

        for st in statuses:
            old_state = self.states.get(st.dd_id, STATE_UNKNOWN)
            self.states[st.dd_id] = st.state

            # Mettre à jour RSSI dans l'UI
            rssi = self.radio.get_rssi(st.dd_id)
            if rssi is not None:
                self.ui.update_dd_rssi(st.dd_id, rssi)

            if old_state != st.state and st.state != STATE_UNKNOWN:
                state_name = "PRESENT" if st.state == STATE_PRESENT else "ABSENT"
                # Afficher RSSI si disponible
                rssi = self.radio.get_rssi(st.dd_id)
                if config.MAIN["DEBUG_MODE"]:
                    if rssi is not None:
                        logger.info("DD{}: {} RSSI:{}dBm (idx={})".format(
                            st.dd_id, state_name, rssi,
                            list(config.RADIO["GROUP_IDS"]).index(st.dd_id)), "app")
                    else:
                        logger.info("DD{}: {} (idx={})".format(
                            st.dd_id, state_name,
                            list(config.RADIO["GROUP_IDS"]).index(st.dd_id)), "app")

            await asyncio.sleep_ms(0)

    async def _handle_testing(self):
        """Gère la requête rapide si un DD est en test"""
        if self.testing_id is not None:
            await asyncio.sleep_ms(0)

    async def _update_battery_periodic(self):
        """Tâche périodique pour mettre à jour l'affichage de la batterie"""
        # Affichage initial après 2 secondes
        await asyncio.sleep_ms(2000)
        if not self.button_manager.is_menu_visible():
            self.display_battery_info()
        
        # Mise à jour toutes les 30 secondes (sauf si menu affiché)
        while True:
            await asyncio.sleep_ms(30000)
            if not self.button_manager.is_menu_visible():
                self.display_battery_info()

    async def run(self):
        """Boucle principale de l'application"""
        
        # Vérifier hardware avant de démarrer
        if not self.hw_ok:
            logger.error("Hardware non disponible - Blocage système", "app")
            self.ui.status("ERREUR HARDWARE - Voir écran")
            
            # Boucle infinie qui ne fait que nourrir le watchdog
            # L'écran reste sur le message d'erreur rouge
            while True:
                self.feed_watchdog()
                await asyncio.sleep_ms(1000)
            return

        # Tâche stats si debug
        if config.MAIN.get("DEBUG_MODE", False):
            asyncio.create_task(self._print_stats())

        # Tâche surveillance boutons
        asyncio.create_task(self.button_manager.check_buttons())
        
        # Tâche mise à jour batterie périodique
        asyncio.create_task(self._update_battery_periodic())

        logger.info("BOUCLE: Entrée dans while True", "app")
        self.ui.status("Demarrage scan ESP-NOW...")

        while True:
            # Log périodique
            if (self.loop_count % 10) == 0 and self.loop_count > 0:
                logger.info("BOUCLE: iteration {}".format(self.loop_count), "app")

            # Watchdog
            self.feed_watchdog()

            # Traitement principal
            await self._update_states()
            
            # Rafraîchir UI seulement si menu pas affiché
            if not self.button_manager.is_menu_visible():
                await self._refresh_ui()
            
            await self._handle_testing()

            self.loop_count += 1

            # Mise à jour du message de statut (sauf si menu affiché)
            if not self.button_manager.is_menu_visible():
                now = time.ticks_ms()
                if time.ticks_diff(now, self.last_status_update) > 500:
                    self._update_status_message()
                    self.last_status_update = now

            # Pause
            await asyncio.sleep_ms(10)