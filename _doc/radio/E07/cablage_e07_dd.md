# Plan de câblage E07 pour DD (WROVER-T7-v1.5)

## Contexte
Intégration d'un module radio E07 (LoRa SX1278/SX1276) sur le détecteur distant (DD) du projet DTD.

---

## Modification préalable : Déplacement LED_ACTIVITY

### Problème
Le GPIO19 est utilisé par LED_ACTIVITY (anciennement LED_INTERNAL) dans le code DD actuel, ce qui empêche l'utilisation du bus VSPI matériel (GPIO 18/19/23).

### Solution recommandée
**Déplacer LED_ACTIVITY de GPIO19 vers GPIO4**

#### Pourquoi GPIO4 ?
- ✅ Complètement libre sur le DD
- ✅ Pas de contraintes au boot
- ✅ GPIO standard (pas utilisé par PSRAM)
- ✅ Sortie stable et fiable
- ✅ Pas de conflit avec HC-12 SET (GPIO26)

#### Modification du code DD

**Fichier :** `dd_main_espnow.py` (et `dd_main_433.py` si applicable)

**Ligne 68 (dd_main_espnow.py) et Ligne 64 (dd_main_433.py) :** Remplacer
```python
LED_INTERNAL_PIN = 19
```
par
```python
LED_ACTIVITY_PIN = 4  # Déplacé pour libérer GPIO19 (VSPI MISO) + renommé
```

**Note :** Remplacer ensuite toutes les occurrences de `LED_INTERNAL` par `LED_ACTIVITY` dans les deux fichiers.

---

## GPIO utilisés par le DD (à éviter)

| GPIO | Fonction DD | Disponible pour E07 |
|------|-------------|---------------------|
| 2 | USB_POWER (détection USB) | ❌ Non |
| 4 | - | ✅ Libre → LED_ACTIVITY |
| 19 | LED_ACTIVITY (ancien GPIO19) | ⚠️ À déplacer |
| 21 | LED_GREEN | ❌ Non |
| 22 | LED_RED | ❌ Non |
| 25 | BIT1 (ID hardware) | ❌ Non |
| 26 | HC-12 SET | ❌ Non |
| 27 | BIT0 (ID hardware) | ❌ Non |
| 32 | BIT2 (ID hardware) | ❌ Non |
| 33 | DD_STATUS (entrée détecteur) | ❌ Non |
| 35 | BATTERY_ADC | ❌ Non |

---

## Plan de câblage E07 → ESP32-WROVER-T7-v1.5

### Connexions SPI (VSPI matériel)

| Pin E07 | Fonction | Pin ESP32 | GPIO | Notes |
|---------|----------|-----------|------|-------|
| VCC | Alimentation | 3V3 | - | 3.3V uniquement |
| GND | Masse | GND | - | Commune |
| **MISO** | SPI MISO | **IO19** | **GPIO19** | VSPI MISO (libéré) |
| **MOSI** | SPI MOSI | **IO23** | **GPIO23** | VSPI MOSI |
| **SCK** | SPI CLK | **IO18** | **GPIO18** | VSPI SCK |
| **NSS** | Chip Select | **IO5** | **GPIO5** | CS/SS |
| **RESET** | Reset module | **IO4** | **GPIO4** | Contrôle reset |
| **DIO0** | IRQ RX/TX | **IO34** | **GPIO34** | IRQ principale (input-only OK) |
| **DIO1** | IRQ timeout | **IO36** | **GPIO36** | IRQ optionnelle (input-only OK) |

### Connexions optionnelles (non utilisées)

| Pin E07 | Fonction | Statut |
|---------|----------|--------|
| DIO2 | FHSS change | Non connecté |
| DIO3 | CAD done | Non connecté |
| DIO4 | - | Non connecté |
| DIO5 | - | Non connecté |

---

## Spécifications du module E07

### Caractéristiques électriques
- **Alimentation :** 3.3V ± 0.3V (1.8V à 3.7V max)
- **Courant RX :** ~10-12 mA
- **Courant TX :** ~120 mA (pic)
- **Courant sleep :** ~0.2 µA

### Fréquences disponibles
- E07-400M : 410-525 MHz
- E07-900M : 862-1020 MHz

### Interface
- **Bus :** SPI (mode 0 ou 1)
- **Vitesse SPI :** jusqu'à 10 MHz
- **Reset :** Actif LOW
- **NSS :** Actif LOW

---

## Recommandations matérielles

### 1. Alimentation
- **Condensateur de découplage obligatoire :**
  - 10 µF électrolytique + 100 nF céramique
  - Placement : le plus près possible du pin VCC du E07
  
### 2. Antenne
- ⚠️ **CRITIQUE :** Ne JAMAIS alimenter le module sans antenne connectée
- **Impédance :** 50Ω
- **Type :** Antenne accordée sur la fréquence du module
  - 433 MHz → λ/4 = 17.3 cm
  - 868 MHz → λ/4 = 8.6 cm
  - 915 MHz → λ/4 = 8.2 cm

### 3. PCB / Câblage
- Garder les traces SPI courtes (<10 cm si possible)
- Pas de traces parallèles longues entre MOSI/MISO/SCK
- Plan de masse sous le module si PCB

---

## Configuration SPI pour MicroPython

### Paramètres VSPI

```python
from machine import Pin, SPI

# Configuration SPI matériel (VSPI)
spi = SPI(
    2,                    # VSPI (bus 2)
    baudrate=4000000,     # 4 MHz (démarrer conservateur)
    polarity=0,           # CPOL = 0
    phase=0,              # CPHA = 0
    bits=8,               # 8 bits par transfert
    firstbit=SPI.MSB,     # MSB first
    sck=Pin(18),          # VSPI SCK
    mosi=Pin(23),         # VSPI MOSI
    miso=Pin(19)          # VSPI MISO
)

# Pins de contrôle E07
nss = Pin(5, Pin.OUT, value=1)      # CS idle HIGH
reset = Pin(4, Pin.OUT, value=1)    # Reset idle HIGH
dio0 = Pin(34, Pin.IN)              # IRQ RX/TX
dio1 = Pin(36, Pin.IN)              # IRQ timeout (optionnel)
```

### Séquence d'initialisation

```python
# 1. Reset du module
reset.value(0)
time.sleep_ms(10)
reset.value(1)
time.sleep_ms(10)

# 2. Vérifier version (lecture registre 0x42)
nss.value(0)
spi.write(bytearray([0x42 & 0x7F]))  # Read register
version = spi.read(1)[0]
nss.value(1)

print("SX127x version: 0x{:02X}".format(version))
# Attendu: 0x12 pour SX1276/77/78/79
```

---

## Avantages de cette configuration

✅ **Bus VSPI matériel** → Performance optimale  
✅ **Pas de conflit** avec les GPIO du DD  
✅ **GPIO standard** → Fiabilité au boot  
✅ **Input-only pour IRQ** → Utilisation optimale des GPIO 34/36  
✅ **Évolutivité** → Autres périphériques SPI possibles sur le même bus  

---

## Bibliothèques MicroPython disponibles

### Option 1 : sx127x (recommandée)
```python
# Installation via mpremote ou IDE
# Repo: https://github.com/Wei1234c/SX127x_driver_for_MicroPython_on_ESP8266

from sx127x import SX127x
```

### Option 2 : uPyLoRaWAN
```python
# Pour LoRaWAN complet
# Repo: https://github.com/lemariva/uPyLoRaWAN
```

### Option 3 : Implémentation manuelle
Contrôle direct via registres SPI pour maximum de flexibilité.

---

## Prochaines étapes

1. ✅ Modifier `LED_ACTIVITY_PIN = 4` dans le code DD (et renommer LED_INTERNAL → LED_ACTIVITY)
2. 🔧 Câbler le module E07 selon le plan ci-dessus
3. 📡 Connecter l'antenne appropriée
4. 💾 Téléverser le code de test SPI
5. 🧪 Vérifier la communication (lecture registre version)
6. 📻 Tester transmission/réception LoRa

---

## Alimentation du module E07

### Consommation du système

| Composant | Consommation |
|-----------|--------------|
| **ESP32-WROVER (WiFi actif)** | ~80-160 mA |
| **ESP32-WROVER (sans WiFi/BLE)** | ~20-40 mA |
| **E07 en TX** | ~120 mA (pic) |
| **E07 en RX** | ~12 mA |
| **DD (LEDs, ADC, etc.)** | ~10-20 mA |
| **TOTAL (mode séquentiel)** | **~150-180 mA** |

### Régulateur onboard T7 v1.5

La carte TTGO T7 v1.5 utilise typiquement un régulateur **AMS1117-3.3** (ou ME6211) :
- **Courant max théorique :** 800 mA - 1 A
- **Courant continu recommandé :** 200-300 mA sans dissipateur
- **Dropout voltage :** 1.1-1.3V @ charge élevée

### ⚠️ Recommandations importantes pour l'alimentation

✅ **Mode séquentiel OBLIGATOIRE** : 
- **Désactiver WiFi/BLE** quand le E07 est actif
- Jamais de TX WiFi et E07 simultané
- Consommation max : ~150-180 mA → **dans les limites**

✅ **Condensateurs de découplage critiques** :
- **10 µF** + **100 nF** aussi près que possible du E07
- **470 µF** + **100 nF** sur le rail 3.3V principal

⚠️ **Si instabilités ou resets** :
- Option 1 : Ajouter un régulateur dédié ME6211C33 pour le E07
- Option 2 : Améliorer le plan de masse et les condensateurs

### Code MicroPython pour désactiver WiFi

```python
import network

# Désactiver WiFi et BLE pour économiser le courant
sta = network.WLAN(network.STA_IF)
sta.active(False)

ap = network.WLAN(network.AP_IF)
ap.active(False)

# Le E07 peut maintenant fonctionner sans risque de pic de courant
```

---

## Notes importantes

- ⚠️ Le E07 est sensible aux décharges électrostatiques (ESD)
- ⚠️ Ne jamais dépasser 3.6V sur VCC
- ⚠️ Les GPIO 34-39 sont input-only sur ESP32 (OK pour DIO0/DIO1)
- ⚠️ Prévoir un dissipateur thermique si TX longue durée à max power

---

**Date :** 28 décembre 2025  
**Projet :** DTD (Détecteur Distant)  
**Module :** ESP32-WROVER-T7-v1.5  
**Radio :** E07 (SX1276/77/78/79)
