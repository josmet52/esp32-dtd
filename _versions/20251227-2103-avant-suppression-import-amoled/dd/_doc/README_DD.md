# DD v6.0.1 - Correction Compatibilite MicroPython

## Resume

Cette version corrige les problemes de compatibilite MicroPython en supprimant tous les accents des commentaires Python.

## Probleme resolu

MicroPython n'accepte que de l'ASCII pur dans le code source, meme dans les commentaires.
Les caracteres accentes (e, a, etc.) provoquaient des erreurs `SyntaxError`.

## Solution

Tous les accents ont ete supprimes des commentaires `#` dans tous les fichiers Python.
Les docstrings `"""` peuvent toujours contenir des accents (c'est du texte).

## Fichiers modifies

7 fichiers corriges :
- boot.py
- dd_main.py
- dd_main_espnow.py
- dd_main_433.py
- dd_nvs_config.py
- ota_mode.py
- config_ta_mac.py

## Changements fonctionnels

**AUCUN** - Cette version corrige uniquement les commentaires.
Toutes les fonctionnalites restent identiques.

## Installation

### Etape 1: Sauvegarde
```python
from dd_nvs_config import show_current_mode
show_current_mode()  # Noter le mode actuel
```

### Etape 2: Deploiement
1. Copier tous les fichiers .py de l'archive
2. Remplacer les fichiers existants sur l'ESP32

### Etape 3: Verification
```python
import machine
machine.reset()
```

Verifier les logs au boot :
```
=== BOOT v1.2.1 ===
[BOOT] Module: WROVER-T7
DD00

=== DD MAIN LOADER v6.0.0 ===
MODE RADIO: ESP-NOW
[LOADER] Chargement: dd_main_espnow
```

## Architecture DD (rappel)

### Modes disponibles
- **ESP-NOW** (NVS=0) - Par defaut, sans fil 2.4GHz
- **Radio 433MHz** (NVS=1) - UART GT38

### Pas de mode RSSI
Contrairement au TA, le DD n'a jamais eu de mode RSSI separe.

### Synchronisation automatique
1. TA envoie MODE:ESPNOW ou MODE:433MHZ
2. DD change mode et reboot
3. TA change mode et reboot
4. Synchronisation complete

## Tests

### Test 1: Boot normal
```
=== BOOT v1.2.1 ===
DD00
=== DD MAIN LOADER v6.0.0 ===
MODE RADIO: ESP-NOW
```

### Test 2: Changement mode
```python
from dd_nvs_config import quick_set_mode
quick_set_mode('433')
import machine
machine.reset()
```

### Test 3: Communication TA
- TA envoie POLL
- DD repond ACK
- Pas d'erreur

## Compatibilite

### Avec TA v2.7.0
✓ 100% compatible

### Avec DD v6.0.0
✓ Identique sauf accents

## Difference TA vs DD

### Valeurs NVS differentes
**TA:**
- ESP-NOW = 0
- 433MHz = 2

**DD:**
- ESP-NOW = 0
- 433MHz = 1

Cette difference est normale et n'affecte pas le fonctionnement.

## Support

### SyntaxError au boot
→ Re-deployer archive v6.0.1

### Module not found
→ Verifier tous les fichiers .py presents

### Communication echoue
→ Verifier meme mode TA et DD
