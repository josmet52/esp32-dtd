"""
ta_menu_ui.py - Interface utilisateur du menu de configuration
Version: 1.1.1
Date: 26.12.2025

Affichage du menu de sélection de mode radio sur l'écran AMOLED.

v1.1.1:
- Espacements réduits pour tout afficher (titre 15px, items 26px)
- Instructions repositionnées (35px du bas)

v1.1.0:
- Passage en mode paysage (landscape)
- Rotation automatique
"""

import amoled
import tft_config_amoled as tft_config
from ta_logger import get_logger

logger = get_logger()

# Entrées du menu
MENU_ESP_NORMAL = 0
MENU_ESP_RSSI = 1
MENU_433MHZ = 2
MENU_OTA = 3
MENU_REBOOT = 4

class MenuUI:
    """Gestionnaire d'affichage du menu"""
    
    def __init__(self, ui):
        """
        Initialise le menu UI
        
        Args:
            ui: Instance de UIPortrait pour accès à l'écran
        """
        self.ui = ui
        self.tft = ui.tft if ui else None
        
        # Sauvegarder orientation et dimensions originales (portrait)
        self.original_rotation = None
        self.portrait_width = ui.width if ui else 240
        self.portrait_height = ui.height if ui else 536
        
        # Dimensions paysage (inversées)
        self.landscape_width = self.portrait_height
        self.landscape_height = self.portrait_width
        
        # Dimensions courantes (changent selon rotation)
        self.width = self.portrait_width
        self.height = self.portrait_height
        
        # Import des polices
        try:
            import fonts.vga2_bold_16x32 as font_title
            import fonts.vga2_16x16 as font_item
            self.font_title = font_title
            self.font_item = font_item
        except:
            try:
                import fonts.vga2_16x32 as font_title
                import fonts.vga2_16x16 as font_item
                self.font_title = font_title
                self.font_item = font_item
            except:
                logger.error("Polices non disponibles", "menu_ui")
                self.font_title = None
                self.font_item = None
        
        # Options du menu
        self.menu_items = [
            "1. ESP-NOW Normal",
            "2. ESP-NOW RSSI",
            "3. Radio 433MHz",
            "4. OTA Update",
            "5. Reboot"
        ]
    
    def _switch_to_landscape(self):
        """Passe l'écran en mode paysage"""
        if not self.tft:
            return
        
        try:
            # Sauvegarder rotation actuelle
            # rotation() sans argument retourne la rotation actuelle
            # Valeurs: 0=portrait, 1=paysage, 2=portrait inversé, 3=paysage inversé
            try:
                self.original_rotation = self.tft.rotation()
            except:
                self.original_rotation = 0  # Défaut portrait
            
            # Passer en paysage (rotation 1 ou 3 selon le hardware)
            # Rotation 1 = paysage standard (largeur > hauteur)
            self.tft.rotation(1)
            
            # Mettre à jour dimensions
            self.width = self.landscape_width
            self.height = self.landscape_height
            
            logger.info("Écran en mode paysage: {}x{}".format(self.width, self.height), "menu_ui")
            
        except Exception as e:
            logger.error("Erreur passage paysage: {}".format(e), "menu_ui")
    
    def _switch_to_portrait(self):
        """Restaure l'écran en mode portrait"""
        if not self.tft:
            return
        
        try:
            # Restaurer rotation originale (normalement 0 = portrait)
            if self.original_rotation is not None:
                self.tft.rotation(self.original_rotation)
            else:
                self.tft.rotation(0)  # Défaut portrait
            
            # Restaurer dimensions
            self.width = self.portrait_width
            self.height = self.portrait_height
            
            logger.info("Écran en mode portrait: {}x{}".format(self.width, self.height), "menu_ui")
            
        except Exception as e:
            logger.error("Erreur retour portrait: {}".format(e), "menu_ui")
    
    def show_menu(self, selected_index=0):
        """
        Affiche le menu de configuration EN MODE PAYSAGE
        
        Args:
            selected_index (int): Index de l'option sélectionnée (0-4)
        """
        if not self.tft or not self.font_title or not self.font_item:
            logger.error("Impossible d'afficher le menu", "menu_ui")
            return
        
        try:
            # PASSER EN MODE PAYSAGE
            self._switch_to_landscape()
            
            # Fond bleu foncé
            bg_color = tft_config.color565(0, 0, 80)
            self.tft.fill(bg_color)
            
            # Titre
            title = "CONFIGURATION"
            title_width = len(title) * 16
            title_x = (self.width - title_width) // 2
            title_y = 15  # Réduit de 20 à 15
            self.tft.text(self.font_title, title, title_x, title_y, 
                         amoled.WHITE, bg_color)
            
            # Ligne sous le titre
            line_y = title_y + 30  # Réduit de 35 à 30
            self.tft.hline(20, line_y, self.width - 40, amoled.WHITE)
            
            # Position de départ des items
            items_start_y = line_y + 15  # Réduit de 20 à 15
            item_spacing = 26  # Réduit de 30 à 26
            
            # Afficher chaque option
            for i, item in enumerate(self.menu_items):
                y_pos = items_start_y + (i * item_spacing)
                
                # Couleurs selon sélection
                if i == selected_index:
                    # Option sélectionnée : fond vert, texte blanc
                    bg = tft_config.color565(0, 100, 0)
                    fg = amoled.WHITE
                    
                    # Rectangle de sélection (hauteur réduite)
                    self.tft.fill_rect(10, y_pos - 3, self.width - 20, 22, bg)
                else:
                    # Option non sélectionnée : fond bleu, texte blanc
                    bg = bg_color
                    fg = amoled.WHITE
                
                # Texte de l'option
                item_x = 20
                self.tft.text(self.font_item, item, item_x, y_pos, fg, bg)
            
            # Instructions en bas (position ajustée)
            help_y = self.height - 35  # Réduit de 40 à 35
            self.tft.text(self.font_item, "Court: Suivant  |  Long: Valider", 20, help_y, 
                         amoled.YELLOW, bg_color)
            
        except Exception as e:
            logger.error("Erreur affichage menu: {}".format(e), "menu_ui")
    
    def show_confirmation(self, item_index):
        """
        Affiche un écran de confirmation avant activation EN MODE PAYSAGE
        
        Args:
            item_index (int): Index de l'option sélectionnée
        """
        if not self.tft or not self.font_title or not self.font_item:
            return
        
        try:
            # Déjà en paysage normalement, mais on s'assure
            if self.width != self.landscape_width:
                self._switch_to_landscape()
            
            # Fond orange
            bg_color = tft_config.color565(150, 80, 0)
            self.tft.fill(bg_color)
            
            # Message de confirmation
            messages = [
                "Activation:",
                self.menu_items[item_index],
                "",
                "Redemarrage..."
            ]
            
            y_start = 60
            y_spacing = 35
            
            for i, msg in enumerate(messages):
                if msg:
                    msg_width = len(msg) * 16
                    msg_x = (self.width - msg_width) // 2
                    msg_y = y_start + (i * y_spacing)
                    
                    font = self.font_title if i <= 1 else self.font_item
                    self.tft.text(font, msg, msg_x, msg_y, amoled.WHITE, bg_color)
            
        except Exception as e:
            logger.error("Erreur affichage confirmation: {}".format(e), "menu_ui")
    
    def hide_menu(self):
        """Masque le menu et restaure l'affichage normal en portrait"""
        # Restaurer mode portrait
        self._switch_to_portrait()
        
        if self.ui:
            # Laisser l'UI normale se redessiner
            pass