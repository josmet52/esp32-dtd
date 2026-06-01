"""
Sniffer GT38 433MHz pour LilyGo T-Display-S3 v2.4
Capture les messages UART du module GT38 et les affiche à l'écran

Connexions module GT38:
- VCC -> 3.3V
- GND -> GND
- TXD -> GPIO 18 (ESP32 RX)
- RXD -> GPIO 17 (ESP32 TX)
- SET -> GPIO 43 (mode transparent = HIGH)

Changelog v2.4:
- Imports adaptés pour répertoire utils/
- DISPLAY_CYCLE_RATIO par défaut à 25 (au lieu de 100)
Changelog v2.3:
- Correction mesure idle: sauvegarde du temps d'inactivité au début du message
"""

from machine import UART, Pin, freq
import time
import uasyncio as asyncio

# Import des modules depuis le répertoire utils
# try:
#     from utils import tft_config
import utils.tft_config as tft_config
import utils.st7789s3 as st7789
# except ImportError:
#     # Fallback si pas dans utils
#     import tft_config
#     import st7789s3 as st7789

# Import des polices depuis utils
try:
    from utils import vga1_8x8 as font_small
    from utils import vga1_8x16 as font_medium
except ImportError:
    try:
        import vga1_8x8 as font_small
        import vga1_8x16 as font_medium
    except ImportError:
        print("ATTENTION: Polices non trouvées, utilisation de write() à la place")
        font_small = None
        font_medium = None

# =============================================================================
# CONFIGURATION
# =============================================================================

VERSION = "2.4"

# Configuration UART pour GT38
UART_INDEX = 1
UART_TX_PIN = 17
UART_RX_PIN = 18
GT38_SET_PIN = 43
BAUDRATE = 9600
UART_TIMEOUT = 10  # ms

# Interface utilisateur
MAX_MESSAGES = 8            # Afficher les 8 paires POLL:0-7 -> ACK:0-7
LINE_HEIGHT = 13            # Hauteur d'une ligne de texte
STATS_UPDATE_INTERVAL = 10  # Mettre à jour les stats tous les N messages

# Paramètres d'affichage par cycle
CYCLE_START_PATTERN = "POLL:00"  # Détecte le début d'un cycle
MAX_CYCLE_MESSAGES = 20          # Maximum de messages dans un cycle (sécurité)
DISPLAY_CYCLE_RATIO = 25         # Afficher 1 cycle sur 25 à l'écran

# =============================================================================
# CLASSE SNIFFER GT38
# =============================================================================

class GT38Sniffer:
    """Capture et décode les messages du module GT38 (cycle-aware)"""
    
    def __init__(self, uart_index, tx_pin, rx_pin, set_pin, baudrate, timeout):
        """
        Initialise le sniffer GT38
        
        Args:
            uart_index: Index de l'UART (1 ou 2)
            tx_pin: GPIO TX
            rx_pin: GPIO RX
            set_pin: GPIO SET (mode transparent)
            baudrate: Vitesse de communication
            timeout: Timeout en ms
        """
        # Configurer le pin SET en mode transparent
        self.set_pin = Pin(set_pin, Pin.OUT)
        self.set_pin.value(1)  # Mode transparent (normal)
        
        # Configurer l'UART
        self.uart = UART(
            uart_index,
            baudrate=baudrate,
            bits=8,
            parity=None,
            stop=1,
            tx=Pin(tx_pin),
            rx=Pin(rx_pin),
            timeout=timeout,
        )
        
        self.buffer = bytearray()
        self.msg_start_us = None
        self.last_message_end_us = None
        self.msg_count = 0
        self.current_idle_us = 0  # Sauvegarder le idle au début du message
        
        # Statistiques
        self.stats = {
            'total': 0,
            'poll': 0,
            'sync': 0,
            'data': 0,
            'errors': 0,
            'avg_duration_us': 0,
            'avg_idle_us': 0,
            'cycles': 0
        }
        self.duration_sum = 0
        self.idle_sum = 0
        
        # Gestion des cycles
        self.current_cycle = []      # Messages du cycle en cours
        self.complete_cycles = []    # Cycles complets prêts pour affichage
        self.in_cycle = False        # True si on est dans un cycle
        self.cycle_start_time_us = None  # Timestamp du début du cycle
        
        # Statistiques de temps de cycle
        self.cycle_times_ms = []     # Historique des temps de cycle
        self.avg_cycle_time_ms = 0   # Temps moyen de cycle
    
    async def read_message_async(self):
        """
        Lit un message complet depuis l'UART (version async)
        
        Returns:
            dict: Message ou None
        """
        # Laisser tourner l'event loop
        await asyncio.sleep_ms(0)
        
        return self.read_message()
    
    def read_message(self):
        """
        Lit un message complet depuis l'UART (octet par octet pour mesure précise)
        
        Returns:
            dict: {'text': str, 'duration_us': int, 'idle_us': int, 'raw': bytes}
                  ou None si pas de message complet
        """
        if not self.uart.any():
            return None
        
        # Lire UN SEUL octet à la fois pour mesurer la durée
        byte_data = self.uart.read(1)
        if not byte_data:
            return None
        
        now_us = time.ticks_us()
        
        # Premier octet du message
        if self.msg_start_us is None:
            self.msg_start_us = now_us
            self.buffer = bytearray()
            
            # Calculer le temps d'inactivité ET LE SAUVEGARDER
            if self.last_message_end_us is not None:
                self.current_idle_us = time.ticks_diff(self.msg_start_us, self.last_message_end_us)
            else:
                self.current_idle_us = 0
        
        # Ajouter l'octet au buffer
        self.buffer.extend(byte_data)
        
        # Chercher le caractère de fin de ligne
        if byte_data == b'\n':
            # Message complet reçu
            self.msg_count += 1
            duration_us = time.ticks_diff(now_us, self.msg_start_us)
            self.last_message_end_us = now_us
            
            # Récupérer le idle_us sauvegardé au début du message
            idle_us = self.current_idle_us
            
            # Le message est dans le buffer
            message_bytes = bytes(self.buffer)
            
            # Décoder le message
            try:
                text = message_bytes.decode('utf-8').rstrip()
            except:
                text = str(message_bytes)
            
            # Mettre à jour les statistiques
            self.stats['total'] += 1
            self.duration_sum += duration_us
            if idle_us > 0:
                self.idle_sum += idle_us
            
            # Classifier le message
            if "POLL" in text:
                self.stats['poll'] += 1
            elif "SYNC" in text:
                self.stats['sync'] += 1
            elif text:
                self.stats['data'] += 1
            
            # Calculer moyennes
            if self.stats['total'] > 0:
                self.stats['avg_duration_us'] = self.duration_sum // self.stats['total']
                if self.stats['total'] > 1:
                    self.stats['avg_idle_us'] = self.idle_sum // (self.stats['total'] - 1)
            
            # Réinitialiser pour le prochain message
            self.msg_start_us = None
            self.current_idle_us = 0
            
            # Créer l'objet message
            msg_obj = {
                'text': text,
                'duration_us': duration_us,
                'idle_us': idle_us,
                'raw': message_bytes,
                'id': self.msg_count
            }
            
            # Gestion des cycles
            self._process_cycle(msg_obj)
            
            return msg_obj
        
        return None
    
    def _process_cycle(self, msg):
        """
        Traite le message dans le contexte des cycles
        
        Args:
            msg: Message à traiter
        """
        text = msg['text']
        
        # Détection du début d'un cycle
        if CYCLE_START_PATTERN in text:
            # Si on était dans un cycle, le finaliser
            if self.in_cycle and self.current_cycle:
                self.complete_cycles.append(self.current_cycle[:])
                self.stats['cycles'] += 1
            
            # Démarrer un nouveau cycle
            self.current_cycle = [msg]
            self.in_cycle = True
            # Capturer le timestamp du début du cycle
            self.cycle_start_time_us = time.ticks_us()
        
        # Si on est dans un cycle, ajouter le message
        elif self.in_cycle:
            self.current_cycle.append(msg)
            
            # Sécurité: cycle trop long, le finaliser
            if len(self.current_cycle) >= MAX_CYCLE_MESSAGES:
                self.complete_cycles.append(self.current_cycle[:])
                self.stats['cycles'] += 1
                self.current_cycle = []
                self.in_cycle = False
                self.cycle_start_time_us = None
        
        # Sinon, message hors cycle (ignorer pour l'affichage écran)
    
    def record_cycle_time(self, cycle_time_ms):
        """
        Enregistre le temps d'un cycle et met à jour la moyenne
        
        Args:
            cycle_time_ms: Temps du cycle en millisecondes
        """
        self.cycle_times_ms.append(cycle_time_ms)
        
        # Garder seulement les 100 derniers cycles pour la moyenne
        if len(self.cycle_times_ms) > 100:
            self.cycle_times_ms.pop(0)
        
        # Calculer la moyenne
        if self.cycle_times_ms:
            self.avg_cycle_time_ms = sum(self.cycle_times_ms) // len(self.cycle_times_ms)
    
    def get_current_cycle_time_ms(self):
        """
        Calcule le temps écoulé depuis le début du cycle en cours
        
        Returns:
            int: Temps en millisecondes, ou 0 si pas de cycle en cours
        """
        if self.cycle_start_time_us is not None:
            elapsed_us = time.ticks_diff(time.ticks_us(), self.cycle_start_time_us)
            return elapsed_us // 1000  # Convertir en ms
        return 0
    
    def get_complete_cycle(self):
        """
        Récupère un cycle complet s'il y en a un
        
        Returns:
            list: Liste de messages du cycle, ou None
        """
        if self.complete_cycles:
            return self.complete_cycles.pop(0)
        return None

# =============================================================================
# CLASSE INTERFACE UTILISATEUR
# =============================================================================

class SnifferUI:
    """Interface graphique pour le sniffer GT38 (cycle-based display)"""
    
    def __init__(self, display):
        """
        Initialise l'interface
        
        Args:
            display: Instance ST7789 configurée
        """
        self.tft = display
        self.messages = []
        
        # Couleurs
        self.C_BLACK = st7789.BLACK
        self.C_WHITE = st7789.WHITE
        self.C_GREEN = st7789.color565(0, 255, 0)
        self.C_YELLOW = st7789.color565(255, 255, 0)
        self.C_CYAN = st7789.color565(0, 255, 255)
        self.C_ORANGE = st7789.color565(255, 165, 0)
        self.C_BLUE = st7789.color565(0, 120, 255)
        self.C_MAGENTA = st7789.color565(255, 0, 255)
        self.C_GRAY = st7789.color565(128, 128, 128)
        
        self._last_stats = None
        
        self.init_display()
    
    def init_display(self):
        """Initialise l'affichage avec l'en-tête"""
        self.tft.fill(self.C_BLACK)
        
        # En-tête
        self.tft.fill_rect(0, 0, 320, 24, self.C_BLUE)
        
        if font_medium:
            self.tft.text(font_medium, f"GT38 SNIFFER v{VERSION}", 5, 4, self.C_WHITE, self.C_BLUE)
            self.tft.text(font_small, "POLL->ACK", 220, 8, self.C_CYAN, self.C_BLUE)
        else:
            self.tft.write(None, f"GT38 v{VERSION}", 5, 4, self.C_WHITE, self.C_BLUE)
            self.tft.write(None, "1:10", 240, 8, self.C_CYAN, self.C_BLUE)
        
        # Ligne de séparation
        self.tft.hline(0, 24, 320, self.C_WHITE)
        
        # Zone de statut initial
        self.update_stats(0, 0, 0, 0, 0, 0, 0)
    
    def display_cycle(self, cycle_messages):
        """
        Affiche un cycle complet avec les 8 paires POLL:0-7 -> ACK:0-7
        
        Args:
            cycle_messages: Liste de messages du cycle
        """
        # Créer un dictionnaire pour stocker les paires POLL:X -> ACK:X
        # On veut afficher POLL:00->ACK:00 jusqu'à POLL:07->ACK:07
        pairs = {}
        
        # Initialiser les 8 positions
        for i in range(8):
            pairs[i] = {
                'poll': None,
                'ack': None,
                'id': 0
            }
        
        # Parcourir tous les messages et extraire les paires
        for msg in cycle_messages:
            text = msg['text']
            
            # Détecter POLL:XX
            if 'POLL:' in text:
                try:
                    # Extraire le numéro (ex: POLL:03 -> 3)
                    poll_num = int(text.split('POLL:')[1].split()[0])
                    if 0 <= poll_num <= 7:
                        pairs[poll_num]['poll'] = msg
                        pairs[poll_num]['id'] = msg['id']
                except:
                    pass
            
            # Détecter ACK:XX
            elif 'ACK:' in text:
                try:
                    # Extraire le numéro (ex: ACK:03:1 -> 3)
                    ack_num = int(text.split('ACK:')[1].split(':')[0])
                    if 0 <= ack_num <= 7:
                        pairs[ack_num]['ack'] = msg
                except:
                    pass
        
        # Convertir en liste ordonnée (0 à 7)
        self.messages = [pairs[i] for i in range(8)]
        
        # Redessiner l'écran
        self.refresh_pairs()
    
    def refresh_pairs(self):
        """
        Redessine les 8 paires POLL:0-7 -> ACK:0-7
        """
        # Effacer la zone des messages
        self.tft.fill_rect(0, 48, 320, 122, self.C_BLACK)
        
        # Dessiner chaque paire (0 à 7)
        y = 48
        for idx, pair in enumerate(self.messages):
            if y > 165:
                break
            
            poll_text = f"POLL:0{idx}"
            
            if pair['poll']:
                # Utiliser le texte réel du POLL
                poll_text = pair['poll']['text'].strip()
            
            if pair['ack']:
                ack_text = pair['ack']['text'].strip()
                # Déterminer la couleur selon l'ACK
                if ':1' in ack_text:
                    color = self.C_GREEN  # ACK positif
                elif ':0' in ack_text:
                    color = self.C_ORANGE  # ACK négatif/erreur
                else:
                    color = self.C_YELLOW  # ACK inconnu
            else:
                ack_text = "NO_ACK"
                color = self.C_GRAY  # Pas d'ACK
            
            # Format: POLL:03 -> ACK:03:1
            line = f"{poll_text} -> {ack_text}"
            
            # Tronquer si trop long
            if len(line) > 28:
                line = line[:25] + "..."
            
            if font_small:
                self.tft.text(font_small, line, 5, y, color, self.C_BLACK)
            else:
                self.tft.write(None, line, 5, y, color, self.C_BLACK)
            
            y += LINE_HEIGHT
    
    def refresh_all_lines(self):
        """
        Redessine toutes les lignes de messages (utilisé après batch)
        """
        # Effacer la zone des messages une seule fois
        self.tft.fill_rect(0, 48, 320, 122, self.C_BLACK)
        
        # Redessiner toutes les lignes
        for i, msg in enumerate(self.messages[-MAX_MESSAGES:]):
            self.draw_message_line_fast(msg, i)
    
    def draw_message_line_fast(self, msg, index):
        """
        Dessine une ligne sans effacer (utilisé dans refresh_all_lines)
        
        Args:
            msg: Dictionnaire avec les données du message
            index: Index de la ligne
        """
        y = 48 + (index * LINE_HEIGHT)
        
        if y > 165:
            return
        
        text = msg['text']
        
        # Choisir la couleur selon le type de message
        if "POLL" in text:
            color = self.C_YELLOW
            prefix = "P"
        elif "SYNC" in text:
            color = self.C_MAGENTA
            prefix = "S"
        elif text.strip():
            color = self.C_GREEN
            prefix = "D"
        else:
            color = self.C_GRAY
            prefix = "?"
        
        # Formater l'affichage
        msg_id = msg['id']
        duration = msg['duration_us']
        
        # Tronquer le texte si trop long
        max_text_len = 28
        display_text = text[:max_text_len] if len(text) > max_text_len else text
        
        line = f"[{prefix}] #{msg_id:04d} {duration:4d}us {display_text}"
        
        # Dessiner directement (pas d'effacement, déjà fait par refresh_all_lines)
        if font_small:
            self.tft.text(font_small, line, 2, y, color, self.C_BLACK)
        else:
            self.tft.write(None, line, 2, y, color, self.C_BLACK)
    
    def draw_message_line(self, msg, index):
        """
        Dessine une seule ligne de message (sans effacer tout l'écran)
        
        Args:
            msg: Dictionnaire avec les données du message
            index: Index de la ligne (0 = première ligne après les stats)
        """
        y = 48 + (index * LINE_HEIGHT)
        
        if y > 165:  # Ne pas dépasser le bas de l'écran
            return
        
        text = msg['text']
        
        # Choisir la couleur selon le type de message
        if "POLL" in text:
            color = self.C_YELLOW
            prefix = "P"
        elif "SYNC" in text:
            color = self.C_MAGENTA
            prefix = "S"
        elif text.strip():
            color = self.C_GREEN
            prefix = "D"
        else:
            color = self.C_GRAY
            prefix = "?"
        
        # Formater l'affichage
        msg_id = msg['id']
        duration = msg['duration_us']
        
        # Tronquer le texte si trop long
        max_text_len = 28
        display_text = text[:max_text_len] if len(text) > max_text_len else text
        
        line = f"[{prefix}] #{msg_id:04d} {duration:4d}us {display_text}"
        
        # Effacer juste cette ligne avant de redessiner
        self.tft.fill_rect(0, y, 320, LINE_HEIGHT, self.C_BLACK)
        
        if font_small:
            self.tft.text(font_small, line, 2, y, color, self.C_BLACK)
        else:
            self.tft.write(None, line, 2, y, color, self.C_BLACK)
    
    def display_cycle_time(self, avg_cycle_time_ms):
        """
        Affiche le temps moyen de cycle et le ratio d'affichage au bas de l'écran
        
        Args:
            avg_cycle_time_ms: Temps moyen en millisecondes
        """
        # Position en bas de l'écran (juste au-dessus du bord)
        y = 158
        
        # Effacer la zone du bas
        self.tft.fill_rect(0, y, 320, 12, self.C_BLACK)
        
        # Afficher le temps moyen et le ratio
        text = f"Avg cycle: {avg_cycle_time_ms}ms on 1/{DISPLAY_CYCLE_RATIO} cycles"
        
        if font_small:
            self.tft.text(font_small, text, 5, y, self.C_CYAN, self.C_BLACK)
        else:
            self.tft.write(None, text, 5, y, self.C_CYAN, self.C_BLACK)
    
    def update_stats(self, total, poll, sync, data, avg_duration, avg_idle, cycles):
        """
        Met à jour les statistiques affichées (optimisé - seulement si changement)
        
        Args:
            total: Nombre total de messages
            poll: Nombre de POLL
            sync: Nombre de SYNC
            data: Nombre de données
            avg_duration: Durée moyenne en µs
            avg_idle: Idle moyen en µs
            cycles: Nombre de cycles complets
        """
        # Ne redessiner que si les valeurs ont changé
        if hasattr(self, '_last_stats'):
            if (self._last_stats == (total, poll, sync, data, avg_duration, avg_idle, cycles)):
                return  # Pas de changement, ne rien faire
        
        self._last_stats = (total, poll, sync, data, avg_duration, avg_idle, cycles)
        
        # Effacer la zone de statut
        self.tft.fill_rect(0, 26, 320, 20, self.C_BLACK)
        
        # Afficher les stats sur 2 lignes
        stats_line1 = f"Tot:{total} Cycles:{cycles} P:{poll} S:{sync}"
        stats_line2 = f"Dur:{avg_duration//1000}ms Idle:{avg_idle//1000}ms"
        
        if font_small:
            self.tft.text(font_small, stats_line1, 3, 27, self.C_CYAN, self.C_BLACK)
            self.tft.text(font_small, stats_line2, 3, 37, self.C_GRAY, self.C_BLACK)
        else:
            self.tft.write(None, stats_line1, 3, 27, self.C_CYAN, self.C_BLACK)
            self.tft.write(None, stats_line2, 3, 37, self.C_GRAY, self.C_BLACK)

# =============================================================================
# TÂCHES ASYNCHRONES
# =============================================================================

async def uart_reader_task(sniffer):
    """
    Tâche prioritaire: lecture UART en continu (jamais bloquée)
    Affiche TOUS les messages sur REPL avec séparation après ACK:07
    """
    print("[UART Task] Démarré - lecture en continu")
    
    while True:
        msg = await sniffer.read_message_async()
        
        if msg:
            # Afficher TOUS les messages sur le REPL (rapide)
            print(f"{msg['id']:05d} | recv={msg['duration_us']:7d}us | ",
                  f"idle={msg['idle_us']:7d}us | {msg['text']}")
            
            # Ligne de séparation après chaque ACK:07 (fin de cycle)
            if "ACK:07" in msg['text']:
                # Calculer le temps total du cycle
                cycle_time_ms = sniffer.get_current_cycle_time_ms()
                
                # Enregistrer le temps pour calculer la moyenne
                sniffer.record_cycle_time(cycle_time_ms)
                
                print("-"*51)
                print(f"Cycle time: {cycle_time_ms}ms")
                print("-"*51)
        
        # Laisser l'event loop respirer
        await asyncio.sleep_ms(1)

async def display_updater_task(sniffer, ui):
    """
    Tâche d'affichage: affiche le premier cycle immédiatement, puis 1 sur 100
    Met à jour les stats uniquement lors du rafraîchissement écran
    """
    print(f"[Display Task] Démarré - 1er cycle immédiat, puis 1/{DISPLAY_CYCLE_RATIO}")
    
    cycle_count = 0
    displayed_count = 0
    first_cycle_displayed = False
    
    while True:
        # Vérifier s'il y a un cycle complet
        cycle = sniffer.get_complete_cycle()
        
        if cycle:
            cycle_count += 1
            
            # Afficher le PREMIER cycle immédiatement
            should_display = False
            if not first_cycle_displayed:
                should_display = True
                first_cycle_displayed = True
                print("="*60)
                print(f"PREMIER CYCLE #{cycle_count} - Affichage immédiat")
                print("="*60)
            # Puis afficher seulement 1 cycle sur DISPLAY_CYCLE_RATIO
            elif cycle_count % DISPLAY_CYCLE_RATIO == 0:
                should_display = True
                print("="*60)
                print(f"CYCLE #{cycle_count} AFFICHÉ (1/{DISPLAY_CYCLE_RATIO})")
                print("="*60)
            
            if should_display:
                displayed_count += 1
                
                # Afficher le cycle sur l'écran
                ui.display_cycle(cycle)
                
                # Afficher le temps moyen de cycle au bas de l'écran
                ui.display_cycle_time(sniffer.avg_cycle_time_ms)
                
                # Mettre à jour les stats EN MÊME TEMPS que l'affichage
                ui.update_stats(
                    sniffer.stats['total'],
                    sniffer.stats['poll'],
                    sniffer.stats['sync'],
                    sniffer.stats['data'],
                    sniffer.stats['avg_duration_us'],
                    sniffer.stats['avg_idle_us'],
                    sniffer.stats['cycles']
                )
        
        # Attendre un peu avant de revérifier
        await asyncio.sleep_ms(50)

# =============================================================================
# PROGRAMME PRINCIPAL
# =============================================================================

async def main_async():
    """Boucle principale asynchrone"""
    
    print("="*60)
    print(f"GT38 Sniffer - LilyGo T-Display-S3 v{VERSION} (Cycle Mode)")
    print("="*60)
    
    # Augmenter la fréquence CPU pour meilleures performances
    freq(240000000)  # 240MHz
    print(f"CPU: {freq() // 1000000} MHz")
    
    # Initialiser l'écran
    print("Initialisation de l'écran...")
    tft = tft_config.config(rotation=1)
    
    # Initialiser l'interface
    ui = SnifferUI(tft)
    
    # Initialiser le sniffer GT38
    print(f"Initialisation du sniffer GT38...")
    print(f"  UART: {UART_INDEX}, TX: {UART_TX_PIN}, RX: {UART_RX_PIN}")
    print(f"  SET: {GT38_SET_PIN}, BAUD: {BAUDRATE}")
    
    sniffer = GT38Sniffer(
        UART_INDEX,
        UART_TX_PIN,
        UART_RX_PIN,
        GT38_SET_PIN,
        BAUDRATE,
        UART_TIMEOUT
    )
    
    print("\n" + "="*60)
    print("MODE CYCLE (POLL:00 -> ACK:07)")
    print("  REPL: 100% des messages + ligne après ACK:07")
    print(f"  Écran: 1er cycle immédiat, puis 1/{DISPLAY_CYCLE_RATIO}")
    print("         (8 paires POLL:0-7->ACK:0-7)")
    print("  Stats: Mises à jour uniquement lors du refresh écran")
    print("  Couleurs: VERT=ACK:X:1, ORANGE=ACK:X:0")
    print("="*60)
    print("\nSniffer en écoute... (Ctrl+C pour arrêter)\n")
    
    try:
        # Créer les tâches asynchrones
        uart_task = asyncio.create_task(uart_reader_task(sniffer))
        display_task = asyncio.create_task(display_updater_task(sniffer, ui))
        
        # Exécuter les tâches en parallèle
        await asyncio.gather(uart_task, display_task)
        
    except KeyboardInterrupt:
        print("\n\nArrêt du sniffer...")
        
        # Afficher les statistiques finales
        print("\n" + "="*60)
        print("STATISTIQUES FINALES")
        print("="*60)
        print(f"Messages totaux:    {sniffer.stats['total']}")
        print(f"  - POLL:           {sniffer.stats['poll']}")
        print(f"  - SYNC:           {sniffer.stats['sync']}")
        print(f"  - DATA:           {sniffer.stats['data']}")
        print(f"Cycles complets:    {sniffer.stats['cycles']}")
        print(f"Durée moyenne:      {sniffer.stats['avg_duration_us']}us ",
              f"({sniffer.stats['avg_duration_us']//1000}ms)")
        print(f"Idle moyen:         {sniffer.stats['avg_idle_us']}us ",
              f"({sniffer.stats['avg_idle_us']//1000}ms)")
        print("="*60)
    
    except Exception as e:
        error_msg = f"Erreur: {str(e)}"
        print(f"\n[ERROR] {error_msg}")
        import sys
        sys.print_exception(e)

def main():
    """Point d'entrée - lance la boucle async"""
    asyncio.run(main_async())

# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    main()