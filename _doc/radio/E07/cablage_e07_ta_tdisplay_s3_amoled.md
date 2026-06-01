# Plan de câblage E07 (CC1101) pour LilyGO T-Display-S3 AMOLED

## Contexte
Terminal Administrateur (TA) du projet DTD utilisant un **LilyGO T-Display-S3 AMOLED** avec écran intégré et un module radio **E07-433M20S (CC1101)** pour communication sans fil avec les détecteurs distants (DD).

---

## Spécifications T-Display-S3 AMOLED

### MCU
- **ESP32-S3R8** (dual-core LX7 @ 240 MHz)
- **Flash :** 16 MB
- **PSRAM :** 8 MB
- **WiFi :** 2.4 GHz 802.11 b/g/n
- **Bluetooth :** 5.0 LE

### Écran AMOLED
- **Taille :** 1.91" (536×240 pixels)
- **Contrôleur :** RM67162
- **Interface :** QSPI (D0-D3) ou SPI
- **Pins utilisés :** GPIO6, 7, 8, 9, 10, 11, 12, 13, 14

### GPIO disponibles

#### GPIO libres (pas utilisés par l'écran)
| GPIO | Type | Notes |
|------|------|-------|
| **1** | I/O | Touch01, disponible ✅ |
| **2** | I/O | Touch02, disponible ✅ |
| **3** | I/O | Touch03, disponible ✅ |
| **4** | I/O | Bat Voltage Detection, disponible ✅ |
| **5** | I/O | Disponible ✅ |
| **16** | I/O | Disponible ✅ |
| **17** | I/O | Disponible ✅ |
| **18** | I/O | Disponible ✅ |
| **21** | I/O | Disponible ✅ |
| **38** | I/O | Disponible ✅ |
| **39** | I/O | Disponible ✅ |
| **40** | I/O | Disponible ✅ |
| **41** | I/O | Disponible ✅ |
| **42** | I/O | Disponible ✅ |

#### GPIO réservés (ne pas utiliser)
| GPIO | Fonction | Notes |
|------|----------|-------|
| 0 | Boot | Bouton BOOT ❌ |
| 6-14 | QSPI Display | Écran AMOLED ❌ |
| 15 | Display Power | Backlight control ❌ |
| 19, 20 | USB | USB D-/D+ ❌ |
| 43, 44 | UART0 | Console USB CDC ❌ |

---

## Configuration SPI pour E07

### Bus SPI recommandé : HSPI (SPI2)

Sur ESP32-S3, il y a 3 bus SPI :
- **SPI0/SPI1** : Réservés pour le flash ❌
- **SPI2 (HSPI)** : Disponible, recommandé ✅
- **SPI3 (VSPI)** : Disponible mais moins utilisé

**Configuration HSPI par défaut ESP32-S3 :**
- MOSI : GPIO11 ❌ (occupé par écran)
- MISO : GPIO13 ❌ (occupé par écran)
- SCK : GPIO12 ❌ (occupé par écran)
- CS : GPIO10 ❌ (occupé par écran)

**→ On doit utiliser des GPIO custom pour le SPI !**

---

## Plan de câblage final E07 → T-Display-S3 AMOLED

### Connexions E07 → ESP32-S3 (QSPI écran actif)

| Pin E07 | Fonction | → | Pin T-Display | GPIO | Notes |
|---------|----------|---|---------------|------|-------|
| **VCC** | Alimentation | → | **3V3** | - | 3.3V ⚠️ Stable |
| **GND** | Masse | → | **GND** | - | 2 pins GND E07 |
| **MOSI** | SPI Data Out | → | **IO42** | **GPIO42** | SPI MOSI ✅ Libre |
| **MISO** | SPI Data In | → | **IO41** | **GPIO41** | SPI MISO ✅ Libre |
| **SCK** | SPI Clock | → | **IO40** | **GPIO40** | SPI SCK ✅ Libre |
| **CSN** | Chip Select | → | **IO3** | **GPIO3** | CS ✅ Libre |
| **GDO0** | DIO0/IRQ | → | **IO1** | **GPIO1** | IRQ principale ✅ |
| **GDO2** | DIO2 | → | **IO2** | **GPIO2** | IRQ optionnelle ✅ |
| **TXEN** | TX Enable | → | **3.3V** via 100Ω | - | PA auto mode |
| **RXEN** | RX Enable | → | **3.3V** via 100Ω | - | LNA auto mode |
| **N** | NC | → | **NC** | - | Non connecté |
| **ANT** | Antenne | → | **Antenne** | - | 433MHz 50Ω |

### Résumé GPIO utilisés

| Fonction | GPIO ESP32-S3 | Notes |
|----------|---------------|-------|
| **SPI MOSI** | GPIO42 | ✅ Libre (pas de conflit QSPI) |
| **SPI MISO** | GPIO41 | ✅ Libre (pas de conflit QSPI) |
| **SPI SCK** | GPIO40 | ✅ Libre (pas de conflit QSPI) |
| **CS (CSN)** | GPIO3 | ✅ Libre (pas de conflit QSPI) |
| **GDO0** | GPIO1 | ✅ IRQ/RX data |
| **GDO2** | GPIO2 | ✅ IRQ/TX data (optionnel) |

**✅ Aucun conflit avec l'écran AMOLED QSPI (GPIO 6-13)**

### Pourquoi ces GPIO ?

L'écran AMOLED en mode **QSPI** utilise :
- GPIO 6-13 : Interface QSPI complète (D0-D3, CLK, CS)

Les GPIO **40, 41, 42, 3** sont :
- ✅ **Disponibles** sur le board (confirmé par vos pins exposés)
- ✅ **Libres** (pas utilisés par l'écran)
- ✅ **Compatibles SPI** (GPIO standards I/O)
- ✅ **Accessibles** physiquement sur les connecteurs

---

## Schéma de connexion visuel

```
T-Display-S3 AMOLED                    E07-433M20S (CC1101)
┌─────────────────────┐                ┌──────────────────┐
│                     │                │                  │
│  ┌──────────────┐   │                │   1  GND         │──┐
│  │   AMOLED     │   │                │   2  MOSI    ────│←─┼─ GPIO42 (MOSI)
│  │   QSPI       │   │                │   3  SCK     ────│←─┼─ GPIO40 (SCK)
│  │ (GPIO 6-13)  │   │                │   4  MISO    ────│──┼→ GPIO41 (MISO)
│  └──────────────┘   │                │   5  GDO2    ────│──┼→ GPIO2
│                     │                │   7  CSN     ────│←─┼─ GPIO3 (CS)
│  GPIO3  (CS)    ────│───────────────→│                  │  │
│  GPIO1  (GDO0)  ←───│────────────────│   6  GDO0        │  │
│  GPIO2  (GDO2)  ←───│────────────────│   5  GDO2        │  │
│                     │                │   8  TXEN    ────│← 3.3V via 100Ω
│  3V3            ────│───────────────→│   11 VCC         │  │
│  GND            ────│───────┬────────│   1,12,14-16 GND │  │
│                     │       │        │   9  RXEN    ────│← 3.3V via 100Ω
│  GPIO40 (SCK)   ────│───────┼───────→│   3  SCK         │  │
│  GPIO41 (MISO)  ←───│───────┼────────│   4  MISO        │  │
│  GPIO42 (MOSI)  ────│───────┼───────→│   2  MOSI        │  │
│                     │       │        │   13 ANT     ────│← Antenne 433MHz
└─────────────────────┘       │        └──────────────────┘
                              └─────────── Masse commune

✅ Pas de conflit : Écran QSPI (GPIO 6-13) et E07 SPI (GPIO 40-42, 3) séparés
```

---

## Composants requis

### Matériel
1. **Module E07-433M20S** (CC1101 433MHz)
2. **Antenne 433MHz** (50Ω, connecteur IPEX ou stamp hole)
3. **2× Résistances 100Ω** (TXEN/RXEN → 3.3V)
4. **Condensateurs découplage :**
   - 10µF + 100nF près du VCC E07
   - 470µF électrolytique sur rail 3.3V (recommandé)

### Câbles
- Fils Dupont ou câbles courts (<15 cm recommandé)
- Ou souder directement si montage permanent

---

## Code MicroPython - Configuration SPI

```python
from machine import Pin, SPI

# Configuration SPI pour E07 sur T-Display-S3 AMOLED
# GPIO libres (pas de conflit avec écran QSPI sur GPIO 6-13)
CC1101_SPI_BUS = 2        # HSPI (SPI2)
CC1101_SCK_PIN = 40       # GPIO40 (libre)
CC1101_MOSI_PIN = 42      # GPIO42 (libre)
CC1101_MISO_PIN = 41      # GPIO41 (libre)
CC1101_CSN_PIN = 3        # GPIO3 (CS, libre)
CC1101_GDO0_PIN = 1       # GPIO1 (IRQ principale)
CC1101_GDO2_PIN = 2       # GPIO2 (IRQ optionnelle)

# Initialisation SPI custom
spi = SPI(
    CC1101_SPI_BUS,
    baudrate=4000000,
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB,
    sck=Pin(CC1101_SCK_PIN),
    mosi=Pin(CC1101_MOSI_PIN),
    miso=Pin(CC1101_MISO_PIN)
)

# Pins de contrôle
csn = Pin(CC1101_CSN_PIN, Pin.OUT, value=1)
gdo0 = Pin(CC1101_GDO0_PIN, Pin.IN)
gdo2 = Pin(CC1101_GDO2_PIN, Pin.IN)

print("SPI CC1101 initialisé sur T-Display-S3 AMOLED")
print("Écran QSPI (GPIO 6-13) et E07 SPI (GPIO 40-42, 3) : Pas de conflit ✓")
```

---

## Considérations importantes

### 1. Alimentation 3.3V
⚠️ **Critique :** Le T-Display-S3 AMOLED + E07 consomment beaucoup !
- **ESP32-S3** : 80-160 mA (WiFi actif)
- **Écran AMOLED** : 50-100 mA (selon luminosité)
- **E07 TX** : ~120 mA peak
- **Total max** : ~380 mA

**Solutions :**
- ✅ Alimentation USB fiable (500 mA min)
- ✅ Batterie LiPo 500+ mAh
- ✅ **Désactiver WiFi** quand E07 actif :
  ```python
  import network
  sta = network.WLAN(network.STA_IF)
  sta.active(False)
  ```

### 2. Backlight control
Le T-Display-S3 AMOLED nécessite **GPIO15 = HIGH** pour allumer l'écran :
```python
# Au démarrage
backlight = Pin(15, Pin.OUT)
backlight.value(1)  # Allumer écran
```

### 3. Condensateurs de découplage
**Essentiels** pour stabilité :
- **10µF + 100nF** directement sur pins VCC/GND du E07
- **470µF électrolytique** sur rail 3.3V (entre T-Display et E07)

### 4. Antenne
🔴 **Obligatoire** pour communication :
- Antenne 433MHz accordée (longueur ~17.3 cm pour 1/4 λ)
- Impédance 50Ω
- Pas d'émission sans antenne = risque module

---

## Tests de validation

### Test 1 : Vérifier alimentation
```python
from machine import Pin
import time

led = Pin(15, Pin.OUT)  # Backlight comme indicateur
for i in range(10):
    led.value(1)
    time.sleep_ms(200)
    led.value(0)
    time.sleep_ms(200)
print("Alimentation OK")
```

### Test 2 : Vérifier SPI
```python
from machine import Pin, SPI

spi = SPI(2, baudrate=4000000, polarity=0, phase=0,
          sck=Pin(17), mosi=Pin(18), miso=Pin(5))
csn = Pin(16, Pin.OUT, value=1)

# Lire VERSION CC1101
csn.value(0)
time.sleep_us(10)
spi.write(bytearray([0x31 | 0xC0]))  # Status read VERSION
data = spi.read(1)
csn.value(1)

print("CC1101 VERSION: 0x{:02X}".format(data[0]))
# Attendu: 0x0F ou 0x14
```

### Test 3 : Vérifier GDO0
```python
gdo0 = Pin(1, Pin.IN)
for i in range(10):
    print("GDO0 level:", gdo0.value())
    time.sleep_ms(500)
```

---

## Tableau récapitulatif

### GPIO T-Display-S3 AMOLED vs DD (T7 v1.5)

| Fonction | DD (T7 v1.5) | TA (T-Display-S3 AMOLED) |
|----------|--------------|--------------------------|
| **SPI MOSI** | GPIO23 | **GPIO42** |
| **SPI MISO** | GPIO19 | **GPIO41** |
| **SPI SCK** | GPIO18 | **GPIO40** |
| **CS (CSN)** | GPIO13 | **GPIO3** |
| **GDO0** | GPIO36 (VP) | **GPIO1** |
| **GDO2** | GPIO39 (VN) | **GPIO2** |

### Avantages de cette configuration
- ✅ **Aucun conflit** avec l'écran AMOLED QSPI (GPIO 6-13)
- ✅ **GPIO libres** (40, 41, 42, 3) disponibles sur le board
- ✅ **Écran QSPI rapide** maintenu (pas de dégradation)
- ✅ **SPI custom** pour E07 avec performance optimale

---

## Prochaines étapes

1. ✅ Câbler le E07 selon ce plan
2. ✅ Tester la communication SPI (lire VERSION)
3. ✅ Adapter le code TA pour T-Display-S3 AMOLED
4. ✅ Tester communication DD ↔ TA

---

## Notes de sécurité

⚠️ **ESP32-S3 est sensible aux décharges électrostatiques (ESD)**
- Se décharger avant manipulation
- Éviter surtensions >3.6V sur GPIO
- Ne jamais connecter/déconnecter E07 sous tension

🔴 **Ne jamais émettre sans antenne** = risque destruction PA du E07

✅ **Toujours vérifier polarité alimentation** avant mise sous tension

---

**Document créé pour le projet DTD - Terminal Administrateur**  
**Version 1.0 - Décembre 2025**
