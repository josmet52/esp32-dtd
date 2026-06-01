# DD ESP-NOW v5.0.0 - Migration RS-485 → ESP-NOW

## Changements principaux

### ✅ Ajouté

- Communication ESP-NOW sans fil (remplace RS-485)
- RSSI disponible pour chaque communication
- Classe `DD_Radio` pour gérer ESP-NOW
- Configuration MAC du TA via NVS

### ❌ Supprimé

- Module UART RS-485 (MAX485, etc.)
- Pins GPIO 18/23 (maintenant libres)
- Pin RADIO_SET_PIN (GPIO 26, maintenant libre)
- Tout le câblage RS-485

### 🔄 Identique

- Protocole: POLL:XX → ACK:XX:Y
- Gestion batterie et LEDs
- Mode OTA
- Logique métier complète

## Configuration initiale

### 1. Sur le Terminal Admin (TA)

```python
# Récupérer le MAC du TA
import network
sta = network.WLAN(network.STA_IF)
sta.active(True)
mac = ':'.join('{:02X}'.format(b) for b in sta.config('mac'))
print("MAC du TA:", mac)
# Exemple: 24:6F:28:XX:YY:ZZ
```

### 2. Sur chaque DD

```python
# Méthode 1: Via config_ta_mac.py
# Éditer TA_MAC dans config_ta_mac.py puis:
import config_ta_mac

# Méthode 2: Directement en REPL
import utils.nvs_utils as nvs_utils
nvs_utils.set_str("DTD", "ta_mac", "24:6F:28:XX:YY:ZZ")
```

### 3. Vérification

```python
import utils.nvs_utils as nvs_utils
print(nvs_utils.get_str("DTD", "ta_mac", default=""))
```

## Déploiement

### Fichiers à téléverser sur chaque DD

```
dd_main.py              # Programme principal v5.0.0
boot.py                 # Inchangé
ota_mode.py            # Inchangé
utils/nvs_utils.py     # Inchangé
utils/set_module_type_and_bat_cal.py  # Inchangé
```

### Optionnel

```
config_ta_mac.py       # Pour config initiale
```

## Test de communication

### Sur le TA (à adapter)

```python
import network
import espnow

sta = network.WLAN(network.STA_IF)
sta.active(True)

e = espnow.ESPNow()
e.active(True)

# Broadcast POLL
e.send(None, b"POLL:00\n")

# Écouter réponses
host, msg = e.recv(1000)
if msg:
    rssi = sta.status('rssi')
    print(f"Reçu de {host.hex()}: {msg} (RSSI: {rssi})")
```

## GPIOs libérés

Avec ESP-NOW, ces GPIOs sont maintenant **disponibles**:

- **GPIO 18** (ex-UART TX)
- **GPIO 23** (ex-UART RX)
- **GPIO 26** (ex-RADIO_SET)

Soit 3 GPIOs pour extensions futures!

## Avantages ESP-NOW vs RS-485

| Critère        | RS-485         | ESP-NOW                         |
| -------------- | -------------- | ------------------------------- |
| Matériel       | Module MAX485  | Aucun (intégré)                 |
| Câblage        | Paire torsadée | Sans fil                        |
| RSSI           | ❌              | ✅                               |
| Coût           | ~3-5€/module   | 0€                              |
| Portée         | ~1200m         | 300m (1km avec antenne externe) |
| Installation   | Complexe       | Simple                          |
| GPIOs utilisés | 3 (TX/RX/SET)  | 0                               |

## Dépannage

### "MAC du TA non configuré"

→ Exécuter `config_ta_mac.py` ou configurer via NVS

### Pas de communication

1. Vérifier MAC du TA stocké: `nvs_utils.get_str("DTD", "ta_mac")`
2. Vérifier TA actif et ESP-NOW initialisé
3. Vérifier portée (<300m sans antenne externe)

### RSSI faible

- RSSI > -50 dBm = Excellent
- RSSI > -60 dBm = Bon
- RSSI > -70 dBm = Moyen
- RSSI < -70 dBm = Faible (rapprocher ou antenne externe)

## Version

**v5.0.0** - Migration ESP-NOW (25/12/2024)

- Première version sans fil
- Compatibilité protocole v4.9.0