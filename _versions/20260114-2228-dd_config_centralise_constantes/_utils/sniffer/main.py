"""
Sniffer HC-12 433MHz pour LilyGo T-Display-S3 v3.4
Capture les messages UART du module HC-12 et les affiche à l'écran
Support modes: SEQUENTIEL (POLL/ACK) et BROADCAST (SYNC/ACK)

Connexions module HC-12:
- VCC -> 3.3V
- GND -> GND
- TXD -> GPIO 18 (ESP32 RX)
- RXD -> GPIO 17 (ESP32 TX)
- SET -> GPIO 43 (mode transparent = HIGH)

Changelog v3.4:
- Correction comptage : compte PRESENT→ABSENT (comme TA)
- Ne compte pas None→ABSENT ni ABSENT→ABSENT (comme TA qui ignore UNKNOWN)
- Alignement parfait : compte TOUS les changements sauf vers UNKNOWN
Changelog v3.3:
- Suppression comptage automatique des NO_ACK
- Changements comptés UNIQUEMENT via ACK explicites (S=0 ou S=1)
- Alignement parfait avec TA qui ne compte pas changements vers UNKNOWN
Changelog v3.2:
- Comptage changements compatible avec ta_app.py
- Compte premier changement depuis None (None→0 ou None→1)
- Évite recomptage pour DD toujours absents (0→0)
- Alignement exact avec méthode TA pour fiabilité
Changelog v3.1:
- Alignement BRO/SEQ à la même position pour esthétique cohérente
Changelog v3.0:
- Déplacement compteurs 40px vers la gauche (x=250) pour affichage complet
- Alignement cohérent de tous les indicateurs de changements
Changelog v2.9:
- Compteurs de changements alignés à droite en jaune
- Correction détection changements mode SEQUENTIAL
- Affichage mode actif (BRO/SEQ) dans le titre
Changelog v2.8:
- Suppression des messages de debug [PARSE]
- Version finale avec tous les indicateurs (changements, temps moyens)
Changelog v2.7:
- Ajout compteur de changements de statut par DD
- Ajout compteur total de changements sur ligne avg cycle
- Ajout temps moyen de réception par DD
- Indicateurs de fiabilité individuelle et globale
Changelog v2.6:
- Correction détection fin de cycle en mode BROADCAST (ACK|ID=07)
- Avg cycle maintenant mis à jour dans les deux modes
Changelog v2.5:
- Support mode BROADCAST (SYNC -> ACK:00-07)
- Détection automatique du mode (POLL:00 ou SYNC)
- Affichage adapté selon le mode détecté
"""

from machine import UART, Pin, freq
import time
import uasyncio as asyncio

# Import des modules depuis le répertoire utils
try:
    from utils import tft_config
    import utils.st7789s3 as st7789
except ImportError:
    # Fallback si pas dans utils
    import tft_config
    import st7789s3 as st7789

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

VERSION = "3.4"

# Configuration UART pour HC-12
UART_INDEX = 1
UART_TX_PIN = 17
UART_RX_PIN = 18
HC12_SET_PIN = 43
BAUDRATE = 9600
UART_TIMEOUT = 10  # ms

# Interface utilisateur
MAX_MESSAGES = 8            # Afficher les 8 paires POLL:0-7 -> ACK:0-7
LINE_HEIGHT = 13            # Hauteur d'une ligne de texte
STATS_UPDATE_INTERVAL = 10  # Mettre à jour les stats tous les N messages

# Paramètres d'affichage par cycle
CYCLE_START_PATTERN_SEQUENTIAL = "POLL:00"  # Mode séquentiel
CYCLE_START_PATTERN_BROADCAST = "SYNC"      # Mode broadcast
MAX_CYCLE_MESSAGES = 20                     # Maximum de messages dans un cycle (sécurité)
DISPLAY_CYCLE_RATIO = 25                    # Afficher 1 cycle sur 25 à l'écran

# Modes de fonctionnement
MODE_SEQUENTIAL = "SEQUENTIAL"  # POLL:00-07 -> ACK:00-07
MODE_BROADCAST = "BROADCAST"    # SYNC -> ACK:00-07

# =============================================================================
# CLASSE SNIFFER HC-12
# =============================================================================

class HC12Sniffer:
    """Capture et décode les messages du module HC-12 (cycle-aware)"""
    
    def __init__(self, uart_index, tx_pin, rx_pin, set_pin, baudrate, timeout):
        """
        Initialise le sniffer HC-12
        
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
        
        # Détection automatique du mode
        self.mode = None             # MODE_SEQUENTIAL ou MODE_BROADCAST
        self.sync_frame_num = None   # Numéro de trame SYNC pour broadcast
        
        # Statistiques de temps de cycle
        self.cycle_times_ms = []     # Historique des temps de cycle
        self.avg_cycle_time_ms = 0   # Temps moyen de cycle
        
        # Suivi des changements de statut (nouveau v2.7)
        self.dd_last_status = {}     # {dd_id: status} - dernier statut connu de chaque DD
        self.dd_status_changes = {}  # {dd_id: count} - nombre de changements par DD
        self.total_status_changes = 0  # Compteur total de changements
        
        # Suivi des temps de réception moyens par DD (nouveau v2.7)
        self.dd_duration_sum = {}    # {dd_id: sum} - somme des durées de réception
        self.dd_duration_count = {}  # {dd_id: count} - nombre de mesures
        self.dd_avg_duration_ms = {} # {dd_id: avg_ms} - temps moyen en ms
        
        # Initialiser les compteurs pour DD 0-7
        for dd_id in range(8):
            self.dd_last_status[dd_id] = None
            self.dd_status_changes[dd_id] = 0
            self.dd_duration_sum[dd_id] = 0
            self.dd_duration_count[dd_id] = 0
            self.dd_avg_duration_ms[dd_id] = 0
    
    def update_dd_status(self, dd_id, status):
        """
        Met à jour le statut d'un DD et compte les changements
        Compatible avec ta_app.py : compte tous les changements y compris depuis None
        
        Args:
            dd_id: ID du DD (0-7)
            status: Nouveau statut (0 ou 1)
        """
        old_status = self.dd_last_status[dd_id]
        
        # Vérifier si c'est un changement (même depuis None)
        if old_status != status:
            # Changement détecté
            self.dd_status_changes[dd_id] += 1
            self.total_status_changes += 1
            
            old_str = "None" if old_status is None else str(old_status)
            print(f"[STATUS CHANGE] DD:{dd_id} {old_str}→{status} (Total DD:{dd_id}={self.dd_status_changes[dd_id]}, Global={self.total_status_changes})")
        
        # Mettre à jour le dernier statut
        self.dd_last_status[dd_id] = status
    
    def update_dd_duration(self, dd_id, duration_us):
        """
        Met à jour le temps de réception moyen d'un DD
        
        Args:
            dd_id: ID du DD (0-7)
            duration_us: Durée de réception en microsecondes
        """
        if 0 <= dd_id <= 7:
            self.dd_duration_sum[dd_id] += duration_us
            self.dd_duration_count[dd_id] += 1
            # Calculer la moyenne en ms
            self.dd_avg_duration_ms[dd_id] = (self.dd_duration_sum[dd_id] // self.dd_duration_count[dd_id]) // 1000
    
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
                self.stats['avg_idle_us'] = self.idle_sum // self.stats['total']
            
            # Préparer le message avec ID
            msg = {
                'id': self.msg_count,
                'text': text,
                'duration_us': duration_us,
                'idle_us': idle_us,
                'raw': message_bytes
            }
            
            # Gérer les cycles
            self._process_cycle_message(msg)
            
            # Extraire et mettre à jour le statut DD si c'est un ACK
            self._extract_and_update_dd_status(text, duration_us)
            
            # Réinitialiser pour le prochain message
            self.msg_start_us = None
            self.buffer = bytearray()
            
            return msg
        
        return None
    
    def _extract_and_update_dd_status(self, text, duration_us):
        """
        Extrait le DD ID et le statut d'un message ACK et met à jour le suivi
        
        Args:
            text: Texte du message (ex: "ACK:03:1" ou "ACK|ID=03|S=1|T=...")
            duration_us: Durée de réception du message en microsecondes
        """
        try:
            dd_id = None
            status = None
            
            # Mode SEQUENTIAL: ACK:DD:STATUS
            if "ACK:" in text and text.count(":") >= 2 and "|" not in text:
                parts = text.split(":")
                if len(parts) >= 3:
                    dd_id = int(parts[1])
                    status = int(parts[2])
            
            # Mode BROADCAST avec |S=: ACK|ID=DD|S=STATUS|T=...
            if "ACK|ID=" in text and "|S=" in text:
                # Extraire ID
                id_start = text.find("ID=") + 3
                id_end = text.find("|", id_start)
                dd_id = int(text[id_start:id_end])
                
                # Extraire S
                s_start = text.find("S=") + 2
                s_end = text.find("|", s_start)
                if s_end == -1:
                    s_end = len(text)
                status = int(text[s_start:s_end])
            
            # Mode BROADCAST avec |VAL=: ACK|ID=DD|VAL=STATUS
            if "ACK|ID=" in text and "|VAL=" in text:
                # Extraire ID
                id_start = text.find("ID=") + 3
                id_end = text.find("|", id_start)
                dd_id = int(text[id_start:id_end])
                
                # Extraire VAL
                val_start = text.find("VAL=") + 4
                val_end = text.find("|", val_start)
                if val_end == -1:
                    val_end = len(text)
                status = int(text[val_start:val_end])
            
            # Si on a extrait un DD et un statut valides, mettre à jour
            if dd_id is not None and status is not None:
                if 0 <= dd_id <= 7 and status in [0, 1]:
                    self.update_dd_status(dd_id, status)
                    # Mettre à jour le temps de réception moyen pour ce DD
                    self.update_dd_duration(dd_id, duration_us)
        
        except (ValueError, IndexError):
            # Ignorer les messages mal formés
            pass
    
    def _process_cycle_message(self, msg):
        """
        Traite un message dans le contexte d'un cycle
        
        Args:
            msg: Message reçu
        """
        text = msg['text']
        
        # Détecter le mode si pas encore fait
        if self.mode is None:
            if CYCLE_START_PATTERN_SEQUENTIAL in text:
                self.mode = MODE_SEQUENTIAL
                print(f"[MODE] Détecté: {self.mode}")
            elif CYCLE_START_PATTERN_BROADCAST in text:
                self.mode = MODE_BROADCAST
                print(f"[MODE] Détecté: {self.mode}")
        
        # Gestion selon le mode détecté
        if self.mode == MODE_SEQUENTIAL:
            self._process_sequential_cycle(msg, text)
        elif self.mode == MODE_BROADCAST:
            self._process_broadcast_cycle(msg, text)
    
    def _process_sequential_cycle(self, msg, text):
        """
        Traite un message en mode SEQUENTIAL (POLL:00-07 -> ACK:00-07)
        
        Args:
            msg: Message reçu
            text: Texte du message
        """
        # Début d'un nouveau cycle
        if CYCLE_START_PATTERN_SEQUENTIAL in text:
            if self.in_cycle and len(self.current_cycle) > 0:
                # Cycle précédent incomplet, le sauvegarder quand même
                self._finalize_cycle()
            
            # Commencer un nouveau cycle
            self.in_cycle = True
            self.current_cycle = [msg]
            self.cycle_start_time_us = time.ticks_us()
        
        # Message dans un cycle en cours
        elif self.in_cycle:
            self.current_cycle.append(msg)
            
            # Fin du cycle (ACK:07)
            if "ACK:07" in text:
                self._finalize_cycle()
            
            # Sécurité: éviter les cycles trop longs
            elif len(self.current_cycle) >= MAX_CYCLE_MESSAGES:
                print(f"[WARN] Cycle trop long ({len(self.current_cycle)} messages), finalisation forcée")
                self._finalize_cycle()
    
    def _process_broadcast_cycle(self, msg, text):
        """
        Traite un message en mode BROADCAST (SYNC -> ACK:00-07)
        
        Args:
            msg: Message reçu
            text: Texte du message
        """
        # Début d'un nouveau cycle (SYNC)
        if CYCLE_START_PATTERN_BROADCAST in text:
            if self.in_cycle and len(self.current_cycle) > 0:
                # Cycle précédent incomplet, le sauvegarder quand même
                self._finalize_cycle()
            
            # Extraire le numéro de trame du SYNC
            try:
                # Format: SYNC|FRAME=XXX
                frame_start = text.find("FRAME=") + 6
                frame_end = text.find("|", frame_start) if "|" in text[frame_start:] else len(text)
                self.sync_frame_num = int(text[frame_start:frame_end])
            except (ValueError, IndexError):
                self.sync_frame_num = None
            
            # Commencer un nouveau cycle
            self.in_cycle = True
            self.current_cycle = [msg]
            self.cycle_start_time_us = time.ticks_us()
        
        # Message dans un cycle en cours
        elif self.in_cycle:
            self.current_cycle.append(msg)
            
            # Fin du cycle (ACK|ID=07)
            if "ACK|ID=07" in text:
                self._finalize_cycle()
            
            # Sécurité: éviter les cycles trop longs
            elif len(self.current_cycle) >= MAX_CYCLE_MESSAGES:
                print(f"[WARN] Cycle trop long ({len(self.current_cycle)} messages), finalisation forcée")
                self._finalize_cycle()
    
    def _finalize_cycle(self):
        """Finalise le cycle en cours et le place dans la liste des cycles complets"""
        if len(self.current_cycle) > 0:
            # Calculer le temps du cycle AVANT de réinitialiser cycle_start_time_us
            if self.cycle_start_time_us is not None:
                cycle_time_us = time.ticks_diff(time.ticks_us(), self.cycle_start_time_us)
                cycle_time_ms = cycle_time_us // 1000
                # Enregistrer le temps pour calculer la moyenne
                self.record_cycle_time(cycle_time_ms)
            
            # Vérifier quels DD ont répondu dans ce cycle
            responded_dds = set()
            
            for msg in self.current_cycle:
                text = msg['text']
                # Extraire les DD qui ont répondu
                try:
                    if "ACK|ID=" in text:
                        id_start = text.find("ID=") + 3
                        id_end = text.find("|", id_start)
                        dd_id = int(text[id_start:id_end])
                        if 0 <= dd_id <= 7:
                            responded_dds.add(dd_id)
                    elif "ACK:" in text and text.count(":") >= 2:
                        parts = text.split(":")
                        if len(parts) >= 2:
                            dd_id = int(parts[1])
                            if 0 <= dd_id <= 7:
                                responded_dds.add(dd_id)
                except:
                    pass
            
            # Les DD qui n'ont pas répondu et qui étaient présents (statut 1) passent à absent (statut 0)
            # Compatible avec TA : compte les changements VERS ABSENT mais pas VERS UNKNOWN
            # Interprétation : si DD était présent (1) et ne répond plus -> ABSENT (0) [compté]
            #                  si DD était absent (0) ou inconnu (None) et ne répond pas -> reste UNKNOWN [non compté]
            for dd_id in range(8):
                if dd_id not in responded_dds:
                    last_status = self.dd_last_status.get(dd_id)
                    # Seulement compter si le DD était explicitement présent (1)
                    if last_status == 1:
                        self.update_dd_status(dd_id, 0)
                        print(f"[NO_ACK] DD:{dd_id} était présent, maintenant absent -> statut=0")
            
            self.complete_cycles.append(self.current_cycle.copy())
            self.stats['cycles'] += 1
        
        self.current_cycle = []
        self.in_cycle = False
        self.cycle_start_time_us = None
    
    def get_complete_cycle(self):
        """
        Récupère le prochain cycle complet (FIFO)
        
        Returns:
            list: Liste de messages du cycle ou None
        """
        if len(self.complete_cycles) > 0:
            return self.complete_cycles.pop(0)
        return None
    
    def get_current_cycle_time_ms(self):
        """
        Calcule le temps écoulé depuis le début du cycle en cours
        
        Returns:
            int: Temps en millisecondes
        """
        if self.cycle_start_time_us is not None:
            elapsed_us = time.ticks_diff(time.ticks_us(), self.cycle_start_time_us)
            return elapsed_us // 1000
        return 0
    
    def record_cycle_time(self, cycle_time_ms):
        """
        Enregistre le temps d'un cycle et calcule la moyenne
        
        Args:
            cycle_time_ms: Temps du cycle en millisecondes
        """
        self.cycle_times_ms.append(cycle_time_ms)
        
        # Garder seulement les 100 derniers cycles pour la moyenne
        if len(self.cycle_times_ms) > 100:
            self.cycle_times_ms.pop(0)
        
        # Calculer la moyenne
        if len(self.cycle_times_ms) > 0:
            self.avg_cycle_time_ms = sum(self.cycle_times_ms) // len(self.cycle_times_ms)

# =============================================================================
# CLASSE INTERFACE UTILISATEUR
# =============================================================================

class SnifferUI:
    """Gère l'affichage sur l'écran TFT"""
    
    # Palette de couleurs
    C_BLACK = st7789.BLACK
    C_WHITE = st7789.WHITE
    C_RED = st7789.RED
    C_GREEN = st7789.GREEN
    C_BLUE = st7789.BLUE
    C_CYAN = st7789.CYAN
    C_YELLOW = st7789.YELLOW
    C_ORANGE = 0xFD20  # Orange RGB565
    C_GRAY = 0x8410    # Gris moyen
    
    def __init__(self, tft):
        """
        Initialise l'interface utilisateur
        
        Args:
            tft: Instance de l'écran TFT configuré
        """
        self.tft = tft
        self._last_stats = None  # Cache pour éviter de redessiner inutilement
        self._last_cycle_display = None  # Cache pour le cycle
        self._current_mode = None  # Mode actuel affiché
        
        # Effacer l'écran et afficher le titre
        self.tft.fill(self.C_BLACK)
        
        title = f"HC-12 Sniffer v{VERSION}"
        if font_medium:
            self.tft.text(font_medium, title, 3, 3, self.C_CYAN, self.C_BLACK)
        else:
            self.tft.write(None, title, 3, 3, self.C_CYAN, self.C_BLACK)
        
        # Ligne de séparation
        self.tft.hline(0, 22, 320, self.C_CYAN)
    
    def display_cycle(self, cycle_messages):
        """
        Affiche un cycle complet sur l'écran
        Optimisé: ne redessine que si le contenu change
        
        Args:
            cycle_messages: Liste des messages du cycle
        """
        # Créer une signature du cycle pour détecter les changements
        cycle_signature = tuple((msg['text'], msg['duration_us'], msg['idle_us']) 
                               for msg in cycle_messages)
        
        # Ne redessiner que si le contenu change
        if cycle_signature == self._last_cycle_display:
            return
        
        self._last_cycle_display = cycle_signature
        
        # Zone d'affichage des messages: y=50 à y=170 environ
        y_start = 50
        self.tft.fill_rect(0, y_start, 320, 120, self.C_BLACK)
        
        # Afficher les 8 messages (POLL:0->ACK:0 ... POLL:7->ACK:7)
        # ou (ACK|ID=0 ... ACK|ID=7) en mode BROADCAST
        
        # Détecter le mode
        first_msg = cycle_messages[0]['text'] if len(cycle_messages) > 0 else ""
        is_broadcast = "SYNC" in first_msg
        
        if is_broadcast:
            self._display_broadcast_cycle(cycle_messages, y_start)
        else:
            self._display_sequential_cycle(cycle_messages, y_start)
    
    def _display_sequential_cycle(self, cycle_messages, y_start):
        """
        Affiche un cycle en mode SEQUENTIAL (POLL:X -> ACK:X)
        
        Args:
            cycle_messages: Messages du cycle
            y_start: Position Y de départ
        """
        # Regrouper les messages par paires POLL->ACK
        pairs = {}  # {dd_id: {'poll': msg, 'ack': msg}}
        
        for msg in cycle_messages:
            text = msg['text']
            
            # POLL:XX
            if "POLL:" in text:
                try:
                    dd_id = int(text.split(":")[1])
                    if dd_id not in pairs:
                        pairs[dd_id] = {}
                    pairs[dd_id]['poll'] = msg
                except:
                    pass
            
            # ACK:XX:Y
            elif "ACK:" in text:
                try:
                    parts = text.split(":")
                    dd_id = int(parts[1])
                    if dd_id not in pairs:
                        pairs[dd_id] = {}
                    pairs[dd_id]['ack'] = msg
                except:
                    pass
        
        # Afficher les 8 paires DD 0-7
        for dd_id in range(8):
            y = y_start + (dd_id * LINE_HEIGHT)
            
            if dd_id in pairs:
                poll_msg = pairs[dd_id].get('poll')
                ack_msg = pairs[dd_id].get('ack')
                
                # Extraire le statut de l'ACK
                status = "?"
                color = self.C_YELLOW
                if ack_msg:
                    text = ack_msg['text']
                    try:
                        # Mode SEQUENTIAL: ACK:XX:Y
                        if ':' in text:
                            parts = text.split(":")
                            if len(parts) >= 3:
                                status = parts[2]
                        # Mode avec S=
                        if '|S=' in text:
                            status = text.split('|S=')[1].split('|')[0]
                        
                        # Définir la couleur
                        if status == '1':
                            color = self.C_GREEN
                        elif status == '0':
                            color = self.C_ORANGE
                    except:
                        pass
                
                # Récupérer le temps moyen pour ce DD
                avg_time_ms = getattr(self, '_dd_avg_duration_ms', {}).get(dd_id, 0)
                changes = getattr(self, '_dd_status_changes', {}).get(dd_id, 0)
                
                # Format: "DD:0X S=Y T=ZZZ" puis [WW] aligné à droite
                line = f"DD:0{dd_id} S={status} T={avg_time_ms}"
                counter = f"[{changes}]"
                
                # Position fixe à droite pour le compteur (décalé de 5 caractères = 40 pixels)
                x_counter = 275
                
                if font_small:
                    self.tft.text(font_small, line, 5, y, color, self.C_BLACK)
                    self.tft.text(font_small, counter, x_counter, y, self.C_YELLOW, self.C_BLACK)
                else:
                    self.tft.write(None, line, 5, y, color, self.C_BLACK)
                    self.tft.write(None, counter, x_counter, y, self.C_YELLOW, self.C_BLACK)
            else:
                # Pas de données pour ce DD
                changes = getattr(self, '_dd_status_changes', {}).get(dd_id, 0)
                line = f"DD:0{dd_id} NO_ACK"
                counter = f"[{changes}]"
                
                # Position fixe à droite pour le compteur
                x_counter = 275
                
                if font_small:
                    self.tft.text(font_small, line, 5, y, self.C_GRAY, self.C_BLACK)
                    self.tft.text(font_small, counter, x_counter, y, self.C_YELLOW, self.C_BLACK)
                else:
                    self.tft.write(None, line, 5, y, self.C_GRAY, self.C_BLACK)
                    self.tft.write(None, counter, x_counter, y, self.C_YELLOW, self.C_BLACK)
    
    def _display_broadcast_cycle(self, cycle_messages, y_start):
        """
        Affiche un cycle en mode BROADCAST (SYNC -> ACK|ID=X)
        
        Args:
            cycle_messages: Messages du cycle
            y_start: Position Y de départ
        """
        # Regrouper les ACK par ID
        acks = {}  # {dd_id: msg}
        sync_msg = None
        
        for msg in cycle_messages:
            text = msg['text']
            
            # SYNC
            if "SYNC" in text:
                sync_msg = msg
            
            # ACK|ID=XX|VAL=Y
            elif "ACK|ID=" in text:
                try:
                    # Extraire l'ID
                    id_start = text.find("ID=") + 3
                    id_end = text.find("|", id_start)
                    dd_id = int(text[id_start:id_end])
                    acks[dd_id] = msg
                except:
                    pass
        
        # Afficher les 8 ACK DD 0-7
        for dd_id in range(8):
            y = y_start + (dd_id * LINE_HEIGHT)
            
            if dd_id in acks:
                ack_msg = acks[dd_id]
                text = ack_msg['text']
                
                # Extraire le statut (S= ou VAL=)
                status = '?'
                color = self.C_YELLOW
                try:
                    if '|S=' in text:
                        status = text.split('|S=')[1].split('|')[0]
                    elif '|VAL=' in text:
                        status = text.split('|VAL=')[1].split('|')[0]
                    
                    # Définir la couleur
                    if status == '1':
                        color = self.C_GREEN
                    elif status == '0':
                        color = self.C_ORANGE
                except:
                    pass
                
                # Récupérer le temps moyen pour ce DD
                avg_time_ms = getattr(self, '_dd_avg_duration_ms', {}).get(dd_id, 0)
                changes = getattr(self, '_dd_status_changes', {}).get(dd_id, 0)
                
                # Format: "DD:0X S=Y T=ZZZ" puis [WW] aligné à droite
                line = f"DD:0{dd_id} S={status} T={avg_time_ms}"
                counter = f"[{changes}]"
                
                # Position fixe à droite pour le compteur (décalé de 5 caractères = 40 pixels)
                x_counter = 275
                
                if font_small:
                    self.tft.text(font_small, line, 5, y, color, self.C_BLACK)
                    self.tft.text(font_small, counter, x_counter, y, self.C_YELLOW, self.C_BLACK)
                else:
                    self.tft.write(None, line, 5, y, color, self.C_BLACK)
                    self.tft.write(None, counter, x_counter, y, self.C_YELLOW, self.C_BLACK)
            else:
                # Pas d'ACK reçu
                changes = getattr(self, '_dd_status_changes', {}).get(dd_id, 0)
                line = f"DD:0{dd_id} NO_ACK"
                counter = f"[{changes}]"
                
                # Position fixe à droite pour le compteur
                x_counter = 275
                
                if font_small:
                    self.tft.text(font_small, line, 5, y, self.C_GRAY, self.C_BLACK)
                    self.tft.text(font_small, counter, x_counter, y, self.C_YELLOW, self.C_BLACK)
                else:
                    self.tft.write(None, line, 5, y, self.C_GRAY, self.C_BLACK)
                    self.tft.write(None, counter, x_counter, y, self.C_YELLOW, self.C_BLACK)
    
    def update_dd_status_changes(self, dd_status_changes):
        """
        Met à jour les compteurs de changements de statut
        
        Args:
            dd_status_changes: Dictionnaire {dd_id: count}
        """
        self._dd_status_changes = dd_status_changes
    
    def update_dd_avg_durations(self, dd_avg_duration_ms):
        """
        Met à jour les temps moyens de réception par DD
        
        Args:
            dd_avg_duration_ms: Dictionnaire {dd_id: avg_ms}
        """
        self._dd_avg_duration_ms = dd_avg_duration_ms
    
    def update_mode_display(self, mode):
        """
        Met à jour l'affichage du mode dans le titre
        
        Args:
            mode: MODE_SEQUENTIAL ou MODE_BROADCAST
        """
        # Ne redessiner que si le mode change
        if self._current_mode == mode:
            return
        
        self._current_mode = mode
        
        # Effacer la zone du mode (coin droit du titre)
        self.tft.fill_rect(260, 3, 60, 16, self.C_BLACK)
        
        # Afficher le mode à la même position pour BRO et SEQ
        if mode == MODE_SEQUENTIAL:
            mode_text = "SEQ"
            x_pos = 275  # Décalé vers la droite pour aligner avec BRO
        elif mode == MODE_BROADCAST:
            mode_text = "BRO"
            x_pos = 275
        else:
            mode_text = "---"
            x_pos = 275
        
        if font_medium:
            self.tft.text(font_medium, mode_text, x_pos, 3, self.C_YELLOW, self.C_BLACK)
        else:
            self.tft.write(None, mode_text, x_pos, 3, self.C_YELLOW, self.C_BLACK)
    
    def display_cycle_time(self, avg_cycle_time_ms, total_changes):
        """
        Affiche le temps moyen de cycle et le nombre total de changements
        
        Args:
            avg_cycle_time_ms: Temps moyen en ms
            total_changes: Nombre total de changements de statut
        """
        # Position en bas de l'écran
        y = 155
        
        # Effacer la ligne
        self.tft.fill_rect(0, y, 320, LINE_HEIGHT, self.C_BLACK)
        
        # Afficher le temps moyen et le ratio (sans le compteur)
        text = f"Avg cycle: {avg_cycle_time_ms}ms on 1/{DISPLAY_CYCLE_RATIO}"
        counter = f"[{total_changes}]"
        
        # Position fixe à droite pour le compteur total (décalé de 5 caractères = 40 pixels)
        x_counter = 275
        
        if font_small:
            self.tft.text(font_small, text, 5, y, self.C_CYAN, self.C_BLACK)
            self.tft.text(font_small, counter, x_counter, y, self.C_YELLOW, self.C_BLACK)
        else:
            self.tft.write(None, text, 5, y, self.C_CYAN, self.C_BLACK)
            self.tft.write(None, counter, x_counter, y, self.C_YELLOW, self.C_BLACK)
    
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
            
            # Ligne de séparation après chaque fin de cycle
            # Mode SEQUENTIAL: ACK:07
            # Mode BROADCAST: ACK|ID=07
            is_end_of_cycle = ("ACK:07" in msg['text'] or "ACK|ID=07" in msg['text'])
            
            if is_end_of_cycle:
                print("-"*51)
                print(f"Cycle time: {sniffer.avg_cycle_time_ms}ms | Total changes: {sniffer.total_status_changes}")
                print("-"*51)
        
        # Laisser l'event loop respirer
        await asyncio.sleep_ms(1)

async def display_updater_task(sniffer, ui):
    """
    Tâche d'affichage: affiche le premier cycle immédiatement, puis 1 sur 100
    Met à jour les stats uniquement lors du rafraîchissement écran
    """
    print(f"[Display Task] Démarré - 1er cycle immédial, puis 1/{DISPLAY_CYCLE_RATIO}")
    
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
                
                # Mettre à jour le mode affiché
                ui.update_mode_display(sniffer.mode)
                
                # Mettre à jour les compteurs de changements dans l'UI
                ui.update_dd_status_changes(sniffer.dd_status_changes)
                
                # Mettre à jour les temps moyens dans l'UI
                ui.update_dd_avg_durations(sniffer.dd_avg_duration_ms)
                
                # Afficher le cycle sur l'écran
                ui.display_cycle(cycle)
                
                # Afficher le temps moyen de cycle au bas de l'écran avec le total de changements
                ui.display_cycle_time(sniffer.avg_cycle_time_ms, sniffer.total_status_changes)
                
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
    print(f"HC-12 Sniffer - LilyGo T-Display-S3 v{VERSION} (Cycle Mode)")
    print("="*60)
    
    # Augmenter la fréquence CPU pour meilleures performances
    freq(240000000)  # 240MHz
    print(f"CPU: {freq() // 1000000} MHz")
    
    # Initialiser l'écran
    print("Initialisation de l'écran...")
    tft = tft_config.config(rotation=1)
    
    # Initialiser l'interface
    ui = SnifferUI(tft)
    
    # Initialiser le sniffer HC-12
    print(f"Initialisation du sniffer HC-12...")
    print(f"  UART: {UART_INDEX}, TX: {UART_TX_PIN}, RX: {UART_RX_PIN}")
    print(f"  SET: {HC12_SET_PIN}, BAUD: {BAUDRATE}")
    
    sniffer = HC12Sniffer(
        UART_INDEX,
        UART_TX_PIN,
        UART_RX_PIN,
        HC12_SET_PIN,
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
    print("  Fiabilité: [XX] = nb changements par DD, total sur avg cycle")
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
        print(f"\nChangements de statut:")
        print(f"  Total:            {sniffer.total_status_changes}")
        for dd_id in range(8):
            changes = sniffer.dd_status_changes[dd_id]
            print(f"  DD {dd_id}:            {changes}")
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