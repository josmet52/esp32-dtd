"""
project : DTD
Component : DD
file: dd_main_espnow.py
author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-dtd
v1.0.0 : 13.01.2026
"""

from machine import Pin, ADC
import time
import machine
import network
import espnow
try:
    import utils.dd_nvs_utils as nvs_utils
except:
    import dd_nvs_utils as nvs_utils

try:
    from machine import WDT
except ImportError:
    WDT = None

try:
    from time import ticks_ms, ticks_diff
except ImportError:
    def ticks_ms():
        return int(time.time() * 1000)
    def ticks_diff(a, b):
        return a - b

# ================================================================
# CONSTANTES
# ================================================================
DEV_MODE = False
WATCHDOG_ENABLED = False
WATCHDOG_MS = 30000
STAT_PERIOD = 5000

UBAT_HIGH = 4.0
UBAT_MID = 3.7
UBAT_LOW = 3.5

DEBOUNCE_SAMPLES = 20
DEBOUNCE_DELAY_US = 1000
BAT_LED_BLINK_MS = 500
BAT_VOLTAGE_DIVIDER = 2.0
AUTO_START = True

# Gestion LED interne sur activite
ACTIVITY_LED_TIMEOUT_MS = 1000
ACTIVITY_LED_ON_MS = 100
ACTIVITY_LED_PERIOD_MS = 1000

# ================================================================
# CONFIGURATION HARDWARE - WROVER-T7
# ================================================================
LED_INTERNAL_PIN = 19
BIT0_PIN = 27
BIT1_PIN = 25
BIT2_PIN = 32
DD_STATUS_PIN = 33

# Gestion batterie
BATTERY_ADC_PIN = 35
LED_RED_PIN = 22
LED_GREEN_PIN = 21
USB_POWER_PIN = 2

# ================================================================
# LECTURE DD_ID (Hardware Straps)
# ================================================================
def read_dd_id():
    """Lit l'ID hardware via les straps (0-7)"""
    try:
        p0 = Pin(BIT0_PIN, Pin.IN, Pin.PULL_UP)
        p1 = Pin(BIT1_PIN, Pin.IN, Pin.PULL_UP)
        p2 = Pin(BIT2_PIN, Pin.IN, Pin.PULL_UP)
        
        bit0 = 0 if p0.value() == 0 else 1
        bit1 = 0 if p1.value() == 0 else 1
        bit2 = 0 if p2.value() == 0 else 1
        
        return (bit2 << 2) | (bit1 << 1) | bit0
    except Exception as e:
        print("[ERREUR] Lecture DD_ID:", e)
        return 0

DD_ID = read_dd_id()

# ================================================================
# VARIABLES GLOBALES
# ================================================================
STATUS_PIN = Pin(DD_STATUS_PIN, Pin.IN, Pin.PULL_UP)

# Configuration batterie
BAT_ADC = ADC(Pin(BATTERY_ADC_PIN))
try:
    BAT_ADC.atten(ADC.ATTN_11DB)
except AttributeError:
    pass

LED_RED = Pin(LED_RED_PIN, Pin.OUT)
LED_GREEN = Pin(LED_GREEN_PIN, Pin.OUT)
LED_RED.value(0)
LED_GREEN.value(0)

USB_POWER = Pin(USB_POWER_PIN, Pin.IN, Pin.PULL_DOWN)
LED_INTERNAL = Pin(LED_INTERNAL_PIN, Pin.OUT)
LED_INTERNAL.value(0)

# Variables batterie et LEDs
blink_green = False
blink_red = False
blink_both = False
last_bat_blink_ms = ticks_ms()

# Variables LED activite
last_poll_time_ms = 0
last_activity_led_cycle_ms = ticks_ms()
activity_led_state = False

# Statistiques
stats_loop_count = 0
stats_poll_received = 0
stats_ack_sent = 0

battery_correction_factor = 1.0

# ================================================================
# ESP-NOW - Communication sans fil
# ================================================================
class DD_Radio:
    """Gestion communication ESP-NOW"""
    
    def __init__(self, ta_mac_str):
        # Activer WiFi (necessaire pour ESP-NOW)
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(True)
        
        # Init ESP-NOW
        self.esp = espnow.ESPNow()
        self.esp.active(True)
        
        # Ajouter Terminal Admin comme peer
        self.ta_mac = bytes.fromhex(ta_mac_str.replace(':', ''))
        self.esp.add_peer(self.ta_mac)
        
        # Buffer reception
        self.rx_buffer = b""
        
        print("[RADIO] ESP-NOW initialisé")
        print("[RADIO] DD MAC: {}".format(self.get_mac()))
        print("[RADIO] TA MAC: {}".format(ta_mac_str))
    
    def get_mac(self):
        """Retourne MAC address du DD"""
        mac_bytes = self.sta.config('mac')
        return ':'.join('{:02X}'.format(b) for b in mac_bytes)
    
    def get_rssi(self):
        """Retourne RSSI du dernier paquet reçu"""
        try:
            return self.sta.status('rssi')
        except:
            # WiFi pas connecte a un reseau (normal pour ESP-NOW)
            return None
    
    def send(self, msg):
        """Envoie message au TA"""
        if isinstance(msg, str):
            msg = msg.encode()
        success = self.esp.send(self.ta_mac, msg, True)  # True = attendre ACK
        return success
    
    def recv(self, timeout_ms=0):
        """
        Reçoit message (non-bloquant)
        Retourne: (message_str, rssi) ou (None, None)
        """
        host, msg = self.esp.recv(timeout_ms)
        if msg:
            # Le RSSI n'est pas disponible de maniere fiable en ESP-NOW
            # sur ESP32 sans connexion WiFi active
            return msg.decode().strip(), None
        return None, None
    
    def check_line(self):
        """
        Vérifie si une ligne complète est disponible
        Retourne: (line_str, rssi) ou (None, None)
        """
        # Lire les donnees disponibles
        msg, rssi = self.recv(0)
        if msg:
            self.rx_buffer += msg.encode() + b'\n'
        
        # Chercher une ligne complete
        if b'\n' in self.rx_buffer:
            line, self.rx_buffer = self.rx_buffer.split(b'\n', 1)
            return line.decode().strip(), rssi
        
        return None, None

# Instance globale radio
radio = None

# ================================================================
# ETAT DETECTEUR
# ================================================================
def measure_state():
    samples = 0
    for _ in range(DEBOUNCE_SAMPLES):
        if STATUS_PIN.value() == 0:
            samples += 1
        time.sleep_us(DEBOUNCE_DELAY_US)
    return 1 if samples >= (DEBOUNCE_SAMPLES // 2 + 1) else 0

# ================================================================
# BATTERIE
# ================================================================
def load_battery_calibration():
    global battery_correction_factor
    try:
        factor = nvs_utils.get_f32("DTD", "bat_cal_factor", default=1.0)
        if 0.5 <= factor <= 2.0:
            battery_correction_factor = factor
        else:
            battery_correction_factor = 1.0
    except Exception as e:
        battery_correction_factor = 1.0

def read_battery_voltage():
    try:
        raw = BAT_ADC.read()
        voltage_adc = (raw / 4095.0) * 3.3
        voltage_bat = voltage_adc * BAT_VOLTAGE_DIVIDER * battery_correction_factor
        return voltage_bat
    except:
        return None

def update_battery_leds(voltage):
    global blink_green, blink_red, blink_both
    
    if voltage is None:
        return
    
    usb_present = USB_POWER.value()
    
    if not usb_present:
        blink_green = False
        blink_red = False
        blink_both = False
        
        if voltage >= UBAT_MID:
            LED_GREEN.value(1)
            LED_RED.value(0)
        elif voltage >= UBAT_LOW:
            LED_GREEN.value(1)
            LED_RED.value(1)
        else:
            LED_GREEN.value(0)
            LED_RED.value(1)
    else:
        if voltage > UBAT_HIGH:
            blink_green = False
            blink_red = False
            blink_both = False
            LED_GREEN.value(1)
            LED_RED.value(0)
        elif voltage >= UBAT_MID:
            blink_green = True
            blink_red = False
            blink_both = False
            LED_RED.value(0)
        elif voltage >= UBAT_LOW:
            blink_green = False
            blink_red = False
            blink_both = True
        else:
            blink_green = False
            blink_red = True
            blink_both = False
            LED_GREEN.value(0)

def update_blinking_leds():
    global last_bat_blink_ms
    
    now = ticks_ms()
    if ticks_diff(now, last_bat_blink_ms) < BAT_LED_BLINK_MS:
        return
    last_bat_blink_ms = now
    
    if blink_both:
        new_state = 0 if LED_GREEN.value() else 1
        LED_GREEN.value(new_state)
        LED_RED.value(new_state)
    else:
        if blink_green:
            LED_GREEN.value(0 if LED_GREEN.value() else 1)
        if blink_red:
            LED_RED.value(0 if LED_RED.value() else 1)

def update_activity_led():
    global last_activity_led_cycle_ms, activity_led_state
    
    now = ticks_ms()
    
    if last_poll_time_ms > 0 and ticks_diff(now, last_poll_time_ms) < ACTIVITY_LED_TIMEOUT_MS:
        time_in_cycle = ticks_diff(now, last_activity_led_cycle_ms)
        
        if time_in_cycle >= ACTIVITY_LED_PERIOD_MS:
            if DEV_MODE:
                print("[LED] Nouveau cycle à t={}ms".format(now))
            last_activity_led_cycle_ms = now
            time_in_cycle = 0
        
        should_be_on = (time_in_cycle < ACTIVITY_LED_ON_MS)
        
        if should_be_on != activity_led_state:
            LED_INTERNAL.value(1 if should_be_on else 0)
            activity_led_state = should_be_on
            if DEV_MODE:
                print("[LED] Changement: {} à time_in_cycle={}ms".format("ON" if should_be_on else "OFF", time_in_cycle))
    else:
        if activity_led_state:
            LED_INTERNAL.value(0)
            activity_led_state = False
            if DEV_MODE:
                print("[LED] Extinction (pas d'activité)")
        last_activity_led_cycle_ms = now

def check_battery_and_stats(loop_count):
    global stats_loop_count, stats_poll_received, stats_ack_sent
    
    if stats_poll_received > 0:
        pct = (stats_ack_sent / stats_poll_received) * 100
    else:
        pct = 0.0
    
    voltage = read_battery_voltage()
    update_battery_leds(voltage)
    
    if DEV_MODE:
        if voltage is not None:
            print("[STATS] Iter:{} POLL:{} ACK:{} Taux:{:.1f}% [bat]{:.2f}V"
                  .format(stats_loop_count, stats_poll_received,
                         stats_ack_sent, pct, voltage))
        else:
            print("[STATS] Iter:{} POLL:{} ACK:{} Taux:{:.1f}%"
                  .format(stats_loop_count, stats_poll_received,
                         stats_ack_sent, pct))

# ================================================================
# TRAITEMENT COMMANDES
# ================================================================
def handle_poll_sequential(line):
    global stats_ack_sent, last_poll_time_ms, last_activity_led_cycle_ms
    
    try:
        req_id = int(line[5:])
    except:
        return
    
    if req_id == DD_ID:
        # Marquer activite et redemarrer cycle LED
        last_poll_time_ms = ticks_ms()
        last_activity_led_cycle_ms = last_poll_time_ms
        
        state = measure_state()
        response = "ACK:{:02d}:{}\n".format(DD_ID, state)
        
        success = radio.send(response)
        if success:
            stats_ack_sent += 1
        
        if DEV_MODE:
            print("[POLL] DD{:02d} state={} → ACK {}".format(
                DD_ID, state, "OK" if success else "FAIL"))

def handle_mode_command(line):
    """
    Traite commande de changement de mode envoyée par le TA
    
    Args:
        line (str): "MODE:ESPNOW" ou "MODE:433MHZ"
    """
    try:
        # Extraire le mode apres "MODE:"
        mode_str = line[5:].strip()
        
        print("[MODE] Commande reçue du TA: {}".format(mode_str))
        
        if mode_str == "ESPNOW":
            # Changement vers ESP-NOW
            try:
                from dd_config import set_radio_mode, RADIO_MODE_ESPNOW
            except:
                print("[MODE] ⚠ dd_config non disponible")
                return
            
            print("[MODE] → Changement vers ESP-NOW")
            
            if set_radio_mode(RADIO_MODE_ESPNOW):
                print("[MODE] ✓ Mode enregistré en NVS")
                print("[MODE] Reboot dans 500ms...")
                time.sleep_ms(500)
                machine.reset()
            else:
                print("[MODE] ✗ Erreur enregistrement NVS")
        
        elif mode_str == "433MHZ":
            # Changement vers 433MHz
            try:
                from dd_config import set_radio_mode, RADIO_MODE_433
            except:
                print("[MODE] ⚠ dd_config non disponible")
                return
            
            print("[MODE] → Changement vers 433MHz")
            
            if set_radio_mode(RADIO_MODE_433):
                print("[MODE] ✓ Mode enregistré en NVS")
                print("[MODE] Reboot dans 500ms...")
                time.sleep_ms(500)
                machine.reset()
            else:
                print("[MODE] ✗ Erreur enregistrement NVS")
        
        else:
            print("[MODE] ⚠ Mode inconnu: {}".format(mode_str))
    
    except Exception as e:
        print("[MODE] ✗ Erreur traitement: {}".format(e))
        import sys
        sys.print_exception(e)

def enter_ota_via_reboot():
    """Entre en mode OTA via flag NVS + reboot"""
    
    # Envoyer ACK OTA
    try:
        radio.send("OTA:ACK:{:02d}\n".format(DD_ID))
    except:
        pass
    
    print(">>> OTA MODE <<<")
    print("[OTA] Flag NVS + Reboot...")
    
    # Ecrire flag OTA en NVS
    nvs_utils.set_i32("DTD", "ota_mode", 1)
    
    time.sleep_ms(250)
    machine.reset()

# ================================================================
# BOUCLE PRINCIPALE
# ================================================================
def main():
    global stats_loop_count, stats_poll_received, radio
    
    load_battery_calibration()
    
    # Charger MAC du TA depuis NVS
    ta_mac = nvs_utils.get_str("DTD", "ta_mac", default="")
    if not ta_mac or len(ta_mac) < 17:
        print("[ERREUR] MAC du TA non configuré en NVS!")
        print("[ERREUR] Utiliser: nvs_utils.set_str('DTD', 'ta_mac', 'AA:BB:CC:DD:EE:FF')")
        time.sleep(5)
        machine.reset()
    
    # Initialiser ESP-NOW
    radio = DD_Radio(ta_mac)
    
    if WATCHDOG_ENABLED and WDT is not None:
        wdt = WDT(timeout=WATCHDOG_MS)
    else:
        wdt = None
    
    print("-" * 70)
    print("DTD v1.0.0 ESP-NOW | ID={:02d} | Module: WROVER-T7".format(DD_ID))
    print("DD_ID = {:02d} | MODE SÉQUENTIEL | COMMUNICATION: ESP-NOW".format(DD_ID))
    print("DEV={} | STAT_PERIOD={} | WATCHDOG={}".format(DEV_MODE, STAT_PERIOD, WATCHDOG_ENABLED))
    print("-" * 70)
    
    # Etat batterie au boot
    voltage = read_battery_voltage()
    if voltage is not None:
        update_battery_leds(voltage)
        print("[BOOT] Batterie: {:.2f}V | USB: {}".format(voltage, "OUI" if USB_POWER.value() else "NON"))
        print("-" * 70)
    
    loop_count = 0
    
    while True:
        loop_count += 1
        stats_loop_count = loop_count
        
        # Verifier messages ESP-NOW
        line, rssi = radio.check_line()
        if line:
            # === TRAITEMENT DES COMMANDES ===
            if line.startswith("POLL:"):
                stats_poll_received += 1
                handle_poll_sequential(line)
            
            elif line.startswith("MODE:"):
                # Commande de changement de mode du TA
                handle_mode_command(line)
            
            elif "OTA:START" in line:
                enter_ota_via_reboot()
                # Ne revient jamais
        
        if wdt is not None:
            wdt.feed()
        
        if loop_count % STAT_PERIOD == 0:
            check_battery_and_stats(loop_count)
        
        # Mise a jour LEDs
        update_blinking_leds()
        update_activity_led()
        
        time.sleep_ms(1)

# ================================================================
# POINT D'ENTREE
# ================================================================
if AUTO_START:
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Arrêt demandé")
    except Exception as e:
        print("\n[ERREUR CRITIQUE]", e)
        import sys
        sys.print_exception(e)