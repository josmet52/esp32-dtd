# CHANGELOG - DD (Detecteur de Presence)
## Version 6.0.1 - 27.12.2025

### Modifications

#### Correction MicroPython
- **Suppression des accents dans tous les commentaires Python (#)**
- Compatibilite stricte avec MicroPython (ASCII uniquement)
- Les docstrings (""") peuvent toujours contenir des accents

### Fichiers modifies

Tous les fichiers .py ont ete corriges pour supprimer les accents des commentaires :

1. **boot.py**
   - Commentaires sans accents
   - Fonctionnalite inchangee

2. **dd_main.py**
   - Commentaires sans accents
   - Fonctionnalite inchangee

3. **dd_main_espnow.py**
   - Commentaires sans accents
   - Fonctionnalite inchangee

4. **dd_main_433.py**
   - Commentaires sans accents
   - Fonctionnalite inchangee

5. **dd_nvs_config.py**
   - Commentaires sans accents
   - Fonctionnalite inchangee

6. **ota_mode.py**
   - Commentaires sans accents
   - Fonctionnalite inchangee

7. **config_ta_mac.py**
   - Commentaires sans accents
   - Fonctionnalite inchangee

### Architecture DD (rappel)

Le DD utilise deja une architecture simplifiee avec 2 modes uniquement :
- **Mode ESP-NOW** (valeur NVS: 0) - Mode par defaut
- **Mode Radio 433MHz** (valeur NVS: 1)

**Note:** Contrairement au TA, le DD n'a JAMAIS eu de mode RSSI separe.
Les valeurs NVS sont differentes entre TA et DD:
- TA: ESP-NOW=0, 433MHz=2
- DD: ESP-NOW=0, 433MHz=1

### Fonctionnalites

#### Synchronisation automatique TA ↔ DD
Le systeme de synchronisation fonctionne correctement :

1. TA envoie commande MODE:ESPNOW ou MODE:433MHZ
2. DD recoit, change son mode NVS, reboot
3. TA change son mode NVS, reboot
4. TA et DD sont synchronises automatiquement

#### Gestion OTA
- Mode OTA via flag NVS
- Lancement automatique au boot si flag=1
- Compatible avec les deux modes radio

### Tests recommandes

#### Test 1: Verification accents
```python
# Verifier qu'aucun fichier ne contient d'accents dans les commentaires
import os
for f in os.listdir():
    if f.endswith('.py'):
        with open(f, 'rb') as file:
            content = file.read()
            if any(b > 127 for b in content if b'#' in content):
                print(f'{f}: ERREUR - Accents detectes')
```

#### Test 2: Demarrage normal
```
=== BOOT v1.2.1 ===
[BOOT] Module: WROVER-T7 (ou WROOM-32)
DD00 (ou DD01, DD02, etc.)

=== DD MAIN LOADER v6.0.0 ===
==================================================
MODE RADIO: ESP-NOW
==================================================
[LOADER] Chargement: dd_main_espnow
```

#### Test 3: Changement de mode
```python
# Depuis REPL
from dd_nvs_config import quick_set_mode
quick_set_mode('433')  # Passer en 433MHz
# Puis reboot
import machine
machine.reset()
```

#### Test 4: Communication avec TA
1. TA envoie POLL (ESP-NOW ou 433MHz)
2. DD repond ACK avec etat presence
3. Pas d'erreurs de communication

### Migration depuis version anterieure

Si vous avez une ancienne version du DD :

1. **Sauvegarde**
   ```python
   from dd_nvs_config import show_current_mode
   show_current_mode()
   ```

2. **Deploiement**
   - Copier tous les fichiers .py de l'archive
   - Remplacer les fichiers existants

3. **Verification**
   ```python
   import machine
   machine.reset()
   # Verifier les logs au boot
   ```

### Compatibilite

#### Avec TA v2.7.0
- ✓ 100% compatible
- Protocole de communication identique
- Synchronisation automatique fonctionnelle

#### Avec anciennes versions DD
- ✓ Compatible avec v6.0.0
- ✓ Pas de changement de protocole
- ✓ Seule difference: accents supprimes

### Notes importantes

#### Difference TA vs DD (valeurs NVS)
Le TA et le DD utilisent des valeurs NVS differentes pour des raisons historiques:

**TA (ta_nvs_config.py):**
```python
RADIO_MODE_ESP_NORMAL = 0  # ESP-NOW
RADIO_MODE_433 = 2         # Radio 433MHz
```

**DD (dd_nvs_config.py):**
```python
RADIO_MODE_ESPNOW = 0  # ESP-NOW
RADIO_MODE_433 = 1     # Radio 433MHz
```

Cette difference n'affecte pas le fonctionnement car :
- Chaque appareil gere sa propre NVS
- La synchronisation se fait par commandes texte (MODE:ESPNOW / MODE:433MHZ)
- Pas d'echange de valeurs NVS entre appareils

#### Pourquoi pas de mode RSSI sur DD ?
Le mode RSSI necessitait une connexion WiFi pour mesurer la qualite du signal.
Sur le DD, cette fonction n'a jamais ete implementee car :
- Consommation energie supplementaire (batterie)
- Complexite inutile pour un detecteur
- RSSI utile uniquement pour diagnostic TA

### Support

En cas de probleme :

#### SyntaxError au boot
→ Fichiers avec accents non remplaces
→ Re-deployer l'archive v6.0.1

#### Module not found
→ Verifier presence de tous les fichiers .py
→ dd_main.py, dd_main_espnow.py, dd_main_433.py, dd_nvs_config.py

#### Communication TA ↔ DD echoue
→ Verifier que TA et DD sont sur le meme mode
→ Utiliser synchronisation automatique via TA

### Fichiers inclus

- boot.py (v1.2.1)
- dd_main.py (v6.0.0)
- dd_main_espnow.py
- dd_main_433.py
- dd_nvs_config.py (v6.0.0)
- ota_mode.py
- config_ta_mac.py
- utils/nvs_utils.py (si present dans l'archive)
