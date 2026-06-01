"""
Project: DTD - ta_ui_portrait.py v1.6.6
Interface utilisateur en mode PORTRAIT pour LilyGO T-Display S3

NOUVEAUTÉ v1.6.6:
- Utilisation font_general (16x16) pour zone version (au lieu de font_small 8x8)
- Utilisation font_general (16x16) pour RSSI sur barres DD (meilleure lisibilité)
- Polices clarifiées: font_title=16x32, font_general=16x16, font_small=8x8

NOUVEAUTÉ v1.6.5:
- Zone version remontée et mieux espacée

Version: 1.6.6
Date: 25/12/2024
"""

__version__ = "1.6.6"

import ta_config as config
from ta_logger import get_logger

try:
    import amoled
    import tft_config_amoled as tft_config
    import fonts.vga2_bold_16x32 as font_title
    import fonts.vga2_16x16 as font_general
    # Police petite pour RSSI et batterie (si dispo, sinon on utilise font_general)
    try:
        import fonts.vga2_8x8 as font_small
    except ImportError:
        font_small = font_general  # Fallback sur 16x16
except ImportError:
    print("[WARN] amoled, tft_config ou fonts non trouvés - mode simulation")
    amoled = None
    tft_config = None
    font_general = None
    font_title = None
    font_small = None

logger = get_logger()

class UIPortrait:
    """Interface utilisateur TFT en mode portrait avec RSSI et batterie"""
    
    def __init__(self, tft=None):
        """Initialise l'UI en mode portrait"""
        self.tft = tft
        
        ui_cfg = config.UI
        
        # Dimensions portrait
        self.width = ui_cfg.get("WIDTH", 170)
        self.height = ui_cfg.get("HEIGHT", 320)
        self.rotation = ui_cfg.get("ROTATION", 0)
        
        # Zones de hauteur
        self.zone_title_height = ui_cfg.get("ZONE_TITLE_HEIGHT", 24)
        self.zone_dd_line_height = ui_cfg.get("ZONE_DD_LINE_HEIGHT", 20)
        self.zone_version_height = ui_cfg.get("ZONE_VERSION_HEIGHT", 70)  # 70 pour 3 lignes + marge
        self.zone_log_line_height = ui_cfg.get("ZONE_LOG_LINE_HEIGHT", 20)
        
        # Hauteur barre heartbeat
        self.heartbeat_height = 8
        
        # Marges
        self.margin_left = ui_cfg.get("MARGIN_LEFT", 5)
        self.margin_right = ui_cfg.get("MARGIN_RIGHT", 5)
        self.margin_top = ui_cfg.get("MARGIN_TOP", 2)
        self.line_spacing = ui_cfg.get("LINE_SPACING", 2)
        
        # Nombre de DD
        self.n_dd = len(config.RADIO["GROUP_IDS"])
        self.group_ids = config.RADIO["GROUP_IDS"]
        
        # Calcul positions Y
        self.y_title = 0
        self.y_dd_start = self.zone_title_height + self.margin_top
        self.y_heartbeat = self.height - self.heartbeat_height
        self.y_version = self.y_heartbeat - self.zone_version_height
        
        # Zone de log
        dd_zone_height = self.n_dd * (self.zone_dd_line_height + self.line_spacing)
        self.y_log_start = self.y_dd_start + dd_zone_height + self.margin_top
        self.log_zone_height = self.y_version - self.y_log_start
        self.n_log_lines = max(1, self.log_zone_height // self.zone_log_line_height)
        
        # État heartbeat
        self.heartbeat_on = False
        
        # RSSI par DD (dict: dd_id -> rssi_value)
        self.dd_rssi = {}
        
        # RSSI moyen global
        self.avg_rssi = None
        
        # États des DD (list: index -> state)
        self.dd_states = [None] * self.n_dd
        
        # Info batterie TA
        self.battery_voltage = None
        self.battery_percent = None
        
        # Flags dirty
        self._dirty_title = True
        self._dirty_dd = [True] * self.n_dd
        self._dirty_version = True
        self._dirty_log = True
        self._dirty_heartbeat = False
        
        # Initialisation TFT
        if not self.tft and amoled and tft_config:
            try:
                self.tft = tft_config.config(self.rotation)
                logger.info("TFT initialisé en mode portrait", "ui_portrait")
            except Exception as e:
                logger.error("Erreur init TFT: {}".format(e), "ui_portrait")
        
        # Effacer l'écran
        if self.tft:
            self.tft.fill(amoled.BLACK)
            self._draw_title()
            self._draw_version()
    
    def get_battery_percentage(self, voltage):
        """
        Calcule % charge basé sur courbe XMY 1020503 3.7V 1000mAh LiPo
        Courbe de décharge typique pour LiPo 3.7V 1000mAh
        """
        if voltage is None:
            return None
        
        # Table voltage → % pour LiPo 1000mAh
        # Basée sur décharge à 0.2C (200mA)
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
    
    def update_battery_info(self, voltage):
        """Met à jour les infos batterie du TA"""
        self.battery_voltage = voltage
        if voltage is not None:
            self.battery_percent = self.get_battery_percentage(voltage)
        else:
            self.battery_percent = None
        self._dirty_version = True  # Marquer dirty pour rafraîchir
    
    def update_dd_rssi(self, dd_id, rssi):
        """Met à jour le RSSI d'un DD"""
        if rssi is not None:
            self.dd_rssi[dd_id] = rssi
            # Marquer le DD comme dirty
            try:
                idx = self.group_ids.index(dd_id)
                self._dirty_dd[idx] = True
            except:
                pass
    
    def update_avg_rssi(self, avg_rssi):
        """Met à jour le RSSI moyen"""
        self.avg_rssi = avg_rssi
        self._dirty_version = True
    
    def _draw_title(self):
        """Dessine la barre de titre"""
        if not self.tft:
            return
        
        try:
            # Fond bleu
            self.tft.fill_rect(0, self.y_title, self.width,
                             self.zone_title_height, amoled.BLUE)
            
            app_name = getattr(config, "APP_NAME", "DTD")
            
            if font_title:
                text_width = len(app_name) * 16
                text_x = (self.width - text_width) // 2
                text_y = self.y_title + 2
                
                self.tft.text(font_title, app_name, text_x, text_y,
                            amoled.WHITE, amoled.BLUE)
            
            self._dirty_title = False
        
        except Exception as e:
            logger.error("Erreur draw title: {}".format(e), "ui_portrait")
    
    def _draw_dd_line(self, index, state):
        """
        Dessine une ligne DD avec RSSI sur la barre colorée
        
        Args:
            index: Index du DD (0 à n_dd-1)
            state: True (présent), False (absent), None (inconnu)
        """
        if not self.tft or index >= self.n_dd:
            return
        
        try:
            y_pos = self.y_dd_start + (index * (self.zone_dd_line_height + self.line_spacing))
            
            # Effacer ligne
            self.tft.fill_rect(0, y_pos, self.width,
                             self.zone_dd_line_height, amoled.BLACK)
            
            # Numéro DD
            dd_id = self.group_ids[index]
            dd_text = "DD{}".format(dd_id)
            
            # Couleur et texte selon état
            # True = présent (détection), False = absent (pas de détection), None = inconnu (pas de réponse)
            if state is True:
                indicator_color = amoled.GREEN  # Détection présente
                state_text = "ON"
                text_color = amoled.BLACK
            elif state is False:
                indicator_color = amoled.RED    # Pas de détection (mais DD répond)
                state_text = "OFF"
                text_color = amoled.YELLOW
            else:
                indicator_color = tft_config.color565(200, 200, 200)  # Gris CLAIR
                state_text = "no signal"
                text_color = amoled.WHITE  # Texte BLANC sur gris clair
            
            # Afficher "DDn"
            if font_title:
                text_x = self.margin_left
                text_y = y_pos + 4
                decalage = 7
                
                self.tft.text(font_title, dd_text, text_x, text_y + decalage,
                            amoled.WHITE, amoled.BLACK)
                
                # Barre colorée
                dd_text_width = len(dd_text) * 16
                indicator_x = text_x + dd_text_width + 10
                indicator_width = self.width - indicator_x - self.margin_right
                indicator_height = self.zone_dd_line_height - 5
                
                self.tft.fill_rect(indicator_x, text_y,
                                 indicator_width, indicator_height, indicator_color)
                
                # Texte état
                if font_title:
                    state_text_x = indicator_x + 10
                    state_text_y = text_y + 8
                    
                    self.tft.text(font_title, state_text, state_text_x, state_text_y,
                                text_color, indicator_color)
                
                # NOUVEAU: Afficher RSSI si disponible et DD répond (présent OU absent)
                # RSSI affiché quand state is True (vert) OU False (rouge)
                # Pas affiché quand state is None (gris "no signal")
                if state is not None and dd_id in self.dd_rssi:
                    rssi = self.dd_rssi[dd_id]
                    rssi_text = "{}dBm".format(rssi)
                    
                    # Positionner à droite de la barre avec font_general (16x16)
                    if font_general:
                        # Calculer position à droite avec largeur 16 pixels
                        rssi_text_width = len(rssi_text) * 16
                        rssi_x = self.width - self.margin_right - rssi_text_width - 5
                        rssi_y = text_y + 8
                        
                        self.tft.text(font_general, rssi_text, rssi_x, rssi_y,
                                    amoled.WHITE, indicator_color)
            
            self._dirty_dd[index] = False
        
        except Exception as e:
            logger.error("Erreur draw DD line {}: {}".format(index, e), "ui_portrait")
    
    def _draw_version(self):
        """
        Dessine la zone version sur 3 lignes :
        Ligne 1: Version (ex: "v2.5.0")
        Ligne 2: Batterie (ex: "3.7V 76%")
        Ligne 3: RSSI moyen (ex: "RSSI: -52dBm")
        
        Police utilisée: font_general = vga2_16x16 (16 pixels de large)
        """
        if not self.tft:
            return
        
        try:
            # Effacer zone version
            self.tft.fill_rect(0, self.y_version, self.width,
                             self.zone_version_height, amoled.BLACK)
            
            version = getattr(config, "APP_VERSION", "1.0.0")
            
            # Ligne 1: VERSION (font_general = 16x16)
            if font_general:
                text1 = "v{}".format(version)
                # font_general = vga2_16x16 donc 16 pixels de large
                text1_width = len(text1) * 16
                text1_x = (self.width - text1_width) // 2
                text1_y = self.y_version + 5  # Marge top
                
                self.tft.text(font_general, text1, text1_x, text1_y,
                            amoled.WHITE, amoled.BLACK)
            
            # Ligne 2: BATTERIE (font_general = 16x16)
            if self.battery_voltage is not None:
                if self.battery_percent is not None:
                    text2 = "{:.2f}V {}%".format(self.battery_voltage, self.battery_percent)
                else:
                    text2 = "{:.2f}V".format(self.battery_voltage)
                
                # 16 pixels de large
                text2_width = len(text2) * 16
                text2_x = (self.width - text2_width) // 2
                text2_y = self.y_version + 25  # 5 + 16 + 4
                
                if font_general:
                    self.tft.text(font_general, text2, text2_x, text2_y,
                                amoled.CYAN, amoled.BLACK)
            
            # Ligne 3: RSSI MOYEN (font_general = 16x16)
            if self.avg_rssi is not None:
                text3 = "RSSI: {}dBm".format(self.avg_rssi)
                text3_width = len(text3) * 16
                text3_x = (self.width - text3_width) // 2
                text3_y = self.y_version + 45  # 5 + 16 + 4 + 16 + 4
                
                if font_general:
                    self.tft.text(font_general, text3, text3_x, text3_y,
                                amoled.YELLOW, amoled.BLACK)
            
            self._dirty_version = False
        
        except Exception as e:
            logger.error("Erreur draw version: {}".format(e), "ui_portrait")
    
    def toggle_heartbeat(self):
        """Bascule l'état du heartbeat"""
        self.heartbeat_on = not self.heartbeat_on
        self._dirty_heartbeat = True
    
    def _draw_heartbeat(self):
        """Dessine la barre heartbeat"""
        if not self.tft:
            return
        
        try:
            color = amoled.CYAN if self.heartbeat_on else amoled.BLACK
            self.tft.fill_rect(0, self.y_heartbeat, self.width,
                             self.heartbeat_height, color)
            self._dirty_heartbeat = False
        
        except Exception as e:
            logger.error("Erreur draw heartbeat: {}".format(e), "ui_portrait")
    
    def update_group(self, index, state=None):
        """
        Met à jour l'état d'un groupe DD
        
        Args:
            index: Index du groupe (0 à n_dd-1)
            state: True (ON), False (OFF), None (inconnu)
        """
        if index < 0 or index >= self.n_dd:
            return
        
        self.dd_states[index] = state
        self._dirty_dd[index] = True
    
    def status(self, message):
        """Affiche un message de statut (dans les logs)"""
        # Pour l'instant, juste logger
        logger.debug("Status: {}".format(message), "ui_portrait")
    
    def render_dirty(self):
        """Rafraîchit uniquement les éléments marqués dirty"""
        if not self.tft:
            return
        
        try:
            if self._dirty_title:
                self._draw_title()
            
            for i in range(self.n_dd):
                if self._dirty_dd[i]:
                    # Utiliser l'état stocké
                    self._draw_dd_line(i, self.dd_states[i])
            
            if self._dirty_version:
                self._draw_version()
            
            if self._dirty_heartbeat:
                self._draw_heartbeat()
        
        except Exception as e:
            logger.error("Erreur render_dirty: {}".format(e), "ui_portrait")