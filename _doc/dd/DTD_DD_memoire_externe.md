# DTD — DD : Mémoire Externe
**Projet : DTD (Détecteur de Tension à Distance)**
**Composant : DD (Détecteur Distant) — v1.0.2 — 14.01.2026**
GitHub : https://github.com/JOM52/esp32-dtd

---

## C'EST QUOI CE COMPOSANT, DÉJÀ ?

Le DD est le **capteur distant**. Il y en a jusqu'à 8 (DD0 à DD7). Chacun surveille un signal physique (une entrée numérique) et répond quand le TA l'interroge. Il tourne sur un **WROVER-T7** (ESP32).

```
         TA (interroge)
            │
            │  "POLL:03"
            ▼
         DD3 (répond)
            │
            │  "ACK:03:1"  (1=présent, 0=absent)
            ▼
         TA (met à jour l'écran)
```

Son ID (0 à 7) est **câblé en hardware** via des straps (cavaliers sur 3 GPIO). Pas de configuration logicielle de l'ID — c'est physique.

---

## HARDWARE EN UN COUP D'ŒIL

**Carte :** WROVER-T7 (ESP32)

| Ce que ça fait | GPIO | Détail |
|---|---|---|
| Strap ID — bit 0 | 27 | PULL_UP. Cavalier → GND = 0, ouvert = 1 |
| Strap ID — bit 1 | 25 | PULL_UP. Cavalier → GND = 0, ouvert = 1 |
| Strap ID — bit 2 | 32 | PULL_UP. Cavalier → GND = 0, ouvert = 1 |
| Signal détecté | 33 | PULL_UP. État mesuré avec anti-rebond |
| LED interne (activité) | 19 | Clignote 100ms/1s si POLL reçu récemment |
| LED rouge | 22 | Indicateur batterie |
| LED verte | 21 | Indicateur batterie / charge |
| Batterie (ADC) | 35 | ATTN_11DB, diviseur ×2, corrigé par facteur NVS |
| USB power détect | 2 | PULL_DOWN. 1 = USB branché |
| UART TX → HC-12 | 18 | Mode 433MHz seulement |
| UART RX ← HC-12 | 23 | Mode 433MHz seulement |

### Comment calculer l'ID depuis les straps

```
BIT2 (GPIO32) | BIT1 (GPIO25) | BIT0 (GPIO27) → ID
   ouvert     |    ouvert     |    ouvert     →  7  (111)
   ouvert     |    ouvert     |   → GND       →  6  (110)
   ...
   → GND      |    → GND     |   → GND       →  0  (000)
```

**Exemple DD3 :** BIT2=ouvert, BIT1=→GND, BIT0=→GND → 0·4 + 1·2 + 1·1 = ... non. Relire :  
`(bit2 << 2) | (bit1 << 1) | bit0` avec bit=0 si cavalier fermé (→GND), bit=1 si ouvert.  
DD3 = binaire 011 → BIT2=ouvert(1→non), BIT1=fermé(→GND=0→... 

**Plus simple en pratique :**

| ID | BIT2 (32) | BIT1 (25) | BIT0 (27) |
|----|-----------|-----------|-----------|
| 0  | → GND | → GND | → GND |
| 1  | → GND | → GND | ouvert |
| 2  | → GND | ouvert | → GND |
| 3  | → GND | ouvert | ouvert |
| 4  | ouvert | → GND | → GND |
| 5  | ouvert | → GND | ouvert |
| 6  | ouvert | ouvert | → GND |
| 7  | ouvert | ouvert | ouvert |

### LEDs batterie — signification

| Situation | LED Verte | LED Rouge |
|---|---|---|
| Sur batterie, charge OK (≥3.7V) | ON fixe | OFF |
| Sur batterie, faible (3.5–3.7V) | ON fixe | ON fixe |
| Sur batterie, critique (<3.5V) | OFF | ON fixe |
| USB branché, batterie pleine (>4.0V) | ON fixe | OFF |
| USB branché, en charge (3.7–4.0V) | Clignote | OFF |
| USB branché, charge lente (3.5–3.7V) | Clignote | Clignote |
| USB branché, très faible (<3.5V) | OFF | Clignote |

**LED interne (GPIO19) :** clignote brièvement (100ms toutes les secondes) tant que des POLL sont reçus. S'éteint si plus aucun POLL depuis 1 seconde → permet de voir visuellement si le DD est "vu" par le TA.

---

## LES FICHIERS ET CE QU'ILS FONT

```
boot.py            ← Premier fichier exécuté. Lit l'ID hardware + vérifie flag OTA.
                     Si flag OTA=1 en NVS → lance dd_ota_mode. Sinon → lance dd_main.
dd_main.py         ← Loader : lit le mode radio en NVS, charge dd_main_espnow OU dd_main_433
dd_main_espnow.py  ← Programme complet mode ESP-NOW (boucle principale, mesure, ACK)
dd_main_433.py     ← Programme complet mode 433MHz/HC-12 (boucle principale, mesure, ACK)
dd_config.py       ← TOUTE la configuration + fonctions utilitaires + menus REPL
dd_nvs_utils.py    ← Lecture/écriture NVS : mode radio, MAC TA, calibration batterie
dd_ota_mode.py     ← Mise à jour firmware Over The Air
```

**Règle d'or : toutes les constantes hardware et comportement sont dans `dd_config.py`.**

---

## COMMENT ÇA DÉMARRE (séquence de boot)

```
boot.py
  ├── lit DD_ID via straps GPIO 27/25/32
  ├── vérifie NVS "DTD/ota_mode"
  │     ├── si = 1 → dd_ota_mode.enter_ota_mode(DD_ID)  [ne revient pas]
  │     └── si = 0 → import dd_main
  │
dd_main.py
  ├── lit mode radio depuis NVS "DTD/radio_mode"
  ├── si RADIO_MODE_ESPNOW (0) → import dd_main_espnow
  └── si RADIO_MODE_433   (1) → import dd_main_433
        │
        └── main()
              ├── load_battery_calibration()   ← lit facteur NVS
              ├── [ESP-NOW] charge MAC TA depuis NVS → init DD_Radio
              ├── [433MHz]  init UART2 (9600 baud, TX=18, RX=23)
              └── while True:
                    ├── vérifie message entrant (ESP-NOW ou UART)
                    │     ├── "POLL:XX"    → mesure état + envoie ACK:XX:Y
                    │     ├── "MODE:..."   → change mode NVS + reboot
                    │     └── "OTA:START"  → flag NVS ota_mode=1 + reboot
                    ├── watchdog.feed() (si activé)
                    ├── stats tous les STAT_PERIOD itérations
                    ├── update LEDs batterie (clignotement)
                    ├── update LED activité (GPIO19)
                    └── sleep 1ms
```

---

## LES DEUX MODES RADIO

Le mode est stocké en **NVS** namespace `"DTD"`, clé `"radio_mode"`.

| Mode | Constante | Valeur NVS | Fichier chargé |
|---|---|---|---|
| ESP-NOW | `RADIO_MODE_ESPNOW` | 0 | `dd_main_espnow.py` |
| 433MHz HC-12 | `RADIO_MODE_433` | 1 | `dd_main_433.py` |

**Mode par défaut :** ESP-NOW (si rien en NVS).

### Différence importante entre les deux modes

**Mode ESP-NOW :**
- Nécessite que le **MAC du TA soit configuré en NVS** (`"DTD/ta_mac"`). Sans ça, le DD reboot en boucle au démarrage avec le message `[ERREUR] MAC du TA non configuré en NVS!`
- Le DD répond uniquement au TA (unicast), pas en broadcast
- Le TA ajoute le DD comme peer automatiquement au premier ACK reçu

**Mode 433MHz :**
- Pas de MAC à configurer
- Communication via UART2 (HC-12), 9600 baud
- Le DD reçoit tous les POLL sur le bus partagé et ne répond qu'à son propre ID

### Mesure de l'état (identique dans les deux modes)

```python
# Anti-rebond : 20 échantillons espacés de 1ms chacun
# Majorité (>50%) → état retenu
samples = 0
for _ in range(20):
    if STATUS_PIN.value() == 0:
        samples += 1
    sleep_us(1000)
state = 1 if samples >= 11 else 0
```

GPIO33 avec PULL_UP : `0` = détection présente (circuit fermé), `1` = pas de détection.  
La réponse envoie : `ACK:XX:1` (présent) ou `ACK:XX:0` (absent).

---

## CONFIGURATION INITIALE D'UN NOUVEAU DD (à ne pas oublier)

Avant le premier démarrage en mode ESP-NOW, il faut configurer le **MAC du TA** en NVS. Sans ça, le DD plante au boot.

**Étape 1 — Obtenir le MAC du TA** (depuis le REPL du TA) :
```python
import network
sta = network.WLAN(network.STA_IF)
sta.active(True)
print(':'.join('{:02X}'.format(b) for b in sta.config('mac')))
# Exemple : 'A4:CF:12:34:56:78'
```

**Étape 2 — Configurer le MAC sur le DD** (depuis le REPL du DD) :
```python
from dd_config import quick_set_mac
quick_set_mac('A4:CF:12:34:56:78')  # ← MAC du TA
import machine; machine.reset()
```

**Étape 3 — Vérifier l'ID hardware** (cavaliers bien positionnés) :
```python
import boot  # lit les straps et affiche DD_ID au boot
# ou :
from boot import read_dd_id
print(read_dd_id())
```

---

## PARAMÈTRES QUE TU VAS SÛREMENT VOULOIR TOUCHER

Tout est dans **`dd_config.py`** :

```python
DEV_MODE = False          # True = logs détaillés dans le terminal série
WATCHDOG_ENABLED = False  # True = reset auto si freeze (timeout 30s)
STAT_PERIOD = 5000        # Affiche stats toutes les N itérations de boucle

# Seuils batterie (en Volts)
UBAT_HIGH = 4.0           # Batterie pleine (USB)
UBAT_MID  = 3.7           # Batterie OK
UBAT_LOW  = 3.5           # Batterie faible

# Anti-rebond signal détecté
DEBOUNCE_SAMPLES  = 20    # Nombre d'échantillons
DEBOUNCE_DELAY_US = 1000  # Délai entre échantillons (µs)

# LED activité (GPIO19)
ACTIVITY_LED_TIMEOUT_MS = 1000  # S'éteint si pas de POLL depuis 1s
ACTIVITY_LED_ON_MS      = 100   # Durée allumage par cycle
ACTIVITY_LED_PERIOD_MS  = 1000  # Période du cycle
```

---

## COMMANDES REPL UTILES

```python
# Voir toute la configuration actuelle
from dd_config import show_config
show_config()

# Changer de mode radio
from dd_config import quick_set_mode
quick_set_mode('espnow')   # ou '433'
import machine; machine.reset()

# Configurer le MAC du TA (mode ESP-NOW)
from dd_config import quick_set_mac
quick_set_mac('AA:BB:CC:DD:EE:FF')

# Calibrer la batterie (si la tension affichée est fausse)
# Formule : facteur = tension_réelle / tension_mesurée
from dd_config import quick_set_battery
quick_set_battery(1.028)   # exemple si mesuré=3.6V mais réel=3.7V

# Menu interactif complet
from dd_config import main_menu
main_menu()

# Voir le mode radio actuel
from dd_config import get_radio_mode, get_mode_name
print(get_mode_name(get_radio_mode()))

# Forcer le mode OTA au prochain reboot
import dd_nvs_utils as nvs
nvs.set_i32("DTD", "ota_mode", 1)
import machine; machine.reset()
```

---

## DEBUGGING — PAR OÙ COMMENCER

### Le DD reboot en boucle au démarrage (mode ESP-NOW)
→ MAC du TA non configuré. Message : `[ERREUR] MAC du TA non configuré en NVS!`  
→ Solution : `quick_set_mac('...')` depuis le REPL (voir section configuration initiale).

### Le DD ne répond pas aux POLL
→ Activer `DEV_MODE = True` dans `dd_config.py` pour voir les POLL reçus et les ACK envoyés.  
→ Vérifier que le mode radio du DD correspond au mode du TA (`show_config()`).  
→ En ESP-NOW : vérifier que le MAC du TA en NVS est correct.  
→ En 433MHz : vérifier le câblage HC-12 (TX=18, RX=23) et que l'HC-12 du TA est bien sur la même fréquence.

### La LED interne ne clignote jamais
→ Le DD ne reçoit aucun POLL. Problème radio ou ID erroné (vérifier les straps / `read_dd_id()`).

### La tension batterie semble fausse
→ Calibrer avec `quick_set_battery(facteur)`. Facteur = tension_multimètre / tension_affichée.

### Voir les stats en direct
Activer `DEV_MODE = True`. Les stats s'affichent toutes les `STAT_PERIOD` itérations de boucle :
```
[STATS] Iter:5000 POLL:45 ACK:45 Taux:100.0% [bat]3.82V
```

---

## CE QUI N'EXISTE PAS ENCORE / PISTES FUTURES

- **Envoi proactif** : le DD ne fait que répondre, il n'envoie jamais spontanément. Si un état change entre deux POLL, ça ne sera vu qu'au prochain cycle.
- **Watchdog** : présent dans le code (`WATCHDOG_ENABLED = False`). À activer si des freezes sont observés en production.
- **RSSI** : `get_rssi()` existe dans `DD_Radio` mais retourne souvent `None` en ESP-NOW sans connexion WiFi active.
- **Retour d'état OTA** : `OTA:ACK:XX` est envoyé au TA avant le reboot OTA, mais le TA ne gère pas encore ce message dans sa boucle.

---

## RAPPEL : ARCHITECTURE DU CODE (pourquoi c'est structuré comme ça)

**Même logique que le TA :** le module radio est chargé dynamiquement selon le mode NVS. `dd_main_espnow.py` et `dd_main_433.py` sont deux programmes complets et indépendants — ils partagent la même logique (mesure, LEDs, batterie, stats, commandes MODE/OTA) mais avec des couches radio différentes.

**Particularité du DD vs TA :** le DD tourne en boucle **synchrone** (pas d'asyncio), avec un `sleep_ms(1)` à chaque itération. C'est volontaire : la latence de réponse doit être minimale, et la boucle asyncio introduirait des délais imprévisibles. Une itération de boucle = ~1ms → le DD peut répondre dans les 2ms suivant la réception d'un POLL.

**NVS namespace unique `"DTD"`** pour tous les DD : pas de risque de collision car chaque DD a sa propre flash.
