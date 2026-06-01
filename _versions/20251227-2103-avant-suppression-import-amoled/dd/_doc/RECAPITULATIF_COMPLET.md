# RECAPITULATIF COMPLET - TA et DD v2.7.0 / v6.0.1

## Vue d'ensemble

### TA (Terminal d'Affichage) - v2.7.0
**Modifications majeures:**
- Suppression du mode ESP-NOW RSSI
- Fusion fichiers ESP-NOW en un seul
- Titre dynamique selon mode radio
- Menu reduit de 5 a 4 options

### DD (Detecteur de Presence) - v6.0.1
**Modifications mineures:**
- Correction accents dans commentaires
- Aucun changement fonctionnel
- Architecture deja simplifiee (2 modes)

## Comparaison architecture

### Modes radio

**TA v2.7.0:**
- ESP-NOW (NVS=0)
- Radio 433MHz (NVS=2)
- ~~ESP-NOW RSSI~~ (SUPPRIME)

**DD v6.0.1:**
- ESP-NOW (NVS=0)
- Radio 433MHz (NVS=1)
- (Jamais eu de mode RSSI)

### Fichiers radio

**TA v2.7.0:**
```
ta_radio_espnow.py     ← FICHIER UNIQUE (fusion)
ta_radio_433.py
```

**DD v6.0.1:**
```
dd_main_espnow.py
dd_main_433.py
```

### Titre / Identification

**TA v2.7.0:**
- Titre dynamique selon mode:
  - Mode ESP-NOW → "TA-espnow"
  - Mode 433MHz → "TA-433MHz"

**DD v6.0.1:**
- ID fixe: "DD00" a "DD07"
- Pas de titre dynamique necessaire

## Synchronisation TA ↔ DD

### Protocole de synchronisation

1. **Changement mode sur TA:**
   - Utilisateur selectionne nouveau mode dans menu
   - TA envoie commande MODE:ESPNOW ou MODE:433MHZ a tous les DD
   - Chaque DD recoit, change NVS, reboot
   - TA change sa NVS, reboot

2. **Resultat:**
   - TA et tous les DD sur le meme mode
   - Synchronisation automatique
   - Pas d'intervention manuelle necessaire

### Commandes MODE

**Envoyees par TA:**
```
MODE:ESPNOW\n   → DD passe en ESP-NOW (NVS=0)
MODE:433MHZ\n   → DD passe en 433MHz (NVS=1)
```

**Reception par DD:**
- Commande recue via ESP-NOW ou UART
- Parsing de la commande
- Mise a jour NVS
- Reboot automatique

## Valeurs NVS - Difference importante

### Pourquoi des valeurs differentes ?

**TA:**
```python
RADIO_MODE_ESP_NORMAL = 0
RADIO_MODE_433 = 2        # Valeur 2 !
```

**DD:**
```python
RADIO_MODE_ESPNOW = 0
RADIO_MODE_433 = 1        # Valeur 1 !
```

### Raison historique
- TA avait 3 modes (0=ESP-NOW, 1=RSSI, 2=433MHz)
- Suppression du mode RSSI (1) mais garde valeur 2 pour 433MHz
- DD n'a jamais eu de mode RSSI donc valeur 1 pour 433MHz
- Cette difference n'affecte rien (NVS locale a chaque appareil)

### Pourquoi ne pas unifier ?
- Eviter migration NVS sur appareils deployes
- Pas d'impact fonctionnel
- Synchronisation via commandes texte (pas valeurs NVS)

## Corrections MicroPython

### Probleme des accents

**TA v2.7.0:**
- Tous les accents supprimes des commentaires #
- Docstrings """ peuvent garder accents

**DD v6.0.1:**
- Tous les accents supprimes des commentaires #
- Docstrings """ peuvent garder accents

### Caracteres remplaces

```
e → e
a → a
u → u
i → i
o → o
c → c
```

## Installation complete du systeme

### Etape 1: Deploiement TA

1. Sauvegarder config:
```python
from ta_nvs_config import show_current_mode
show_current_mode()
```

2. Supprimer anciens fichiers:
```python
import os
os.remove('ta_radio_espnow_rssi.py')      # Si existe
os.remove('ta_radio_espnow_normal.py')    # Si existe
```

3. Copier fichiers TA v2.7.0

4. Reboot:
```python
import machine
machine.reset()
```

### Etape 2: Deploiement DD

1. Sauvegarder config de chaque DD:
```python
from dd_nvs_config import show_current_mode
show_current_mode()
```

2. Copier fichiers DD v6.0.1 sur chaque DD

3. Reboot chaque DD:
```python
import machine
machine.reset()
```

### Etape 3: Verification

1. **Verifier titre TA:**
   - Mode ESP-NOW → "TA-espnow"
   - Mode 433MHz → "TA-433MHz"

2. **Verifier communication:**
   - TA interroge les DD
   - DD repondent
   - Etats affiches correctement

3. **Tester synchronisation:**
   - Changer mode sur TA via menu
   - Verifier DD rebootent automatiquement
   - Verifier tous sur meme mode apres reboot

## Tests de validation

### Test 1: Communication ESP-NOW
```
1. TA et DD en mode ESP-NOW
2. TA affiche titre "TA-espnow"
3. TA envoie POLL
4. DD repond ACK
5. Etat affiche sur TA
```

### Test 2: Communication 433MHz
```
1. TA et DD en mode 433MHz
2. TA affiche titre "TA-433MHz"
3. TA envoie POLL via UART
4. DD repond ACK via UART
5. Etat affiche sur TA
```

### Test 3: Synchronisation automatique
```
1. TA en ESP-NOW, DD en ESP-NOW
2. Menu TA → Selection "2. Radio 433MHz"
3. Pression longue → Confirmation
4. Verifier:
   - TA envoie MODE:433MHZ aux DD
   - DD rebootent en mode 433MHz
   - TA reboote en mode 433MHz
   - Titre TA = "TA-433MHz"
   - Communication fonctionne
```

### Test 4: Retour ESP-NOW
```
1. TA en 433MHz, DD en 433MHz
2. Menu TA → Selection "1. ESP-NOW"
3. Pression longue → Confirmation
4. Verifier:
   - TA envoie MODE:ESPNOW aux DD
   - DD rebootent en mode ESP-NOW
   - TA reboote en mode ESP-NOW
   - Titre TA = "TA-espnow"
   - Communication fonctionne
```

## Compatibilite versions

### TA v2.7.0 ↔ DD v6.0.1
✓ 100% compatible

### TA v2.7.0 ↔ DD v6.0.0
✓ Compatible (DD v6.0.1 juste correction accents)

### TA v2.6.0 ↔ DD v6.0.1
✓ Compatible mais pas de titre dynamique

### Anciennes versions
⚠️ Migrer toutes les versions ensemble recommande

## Fichiers par appareil

### TA v2.7.0 (14 fichiers)
```
boot.py
ta_main.py
ta_app.py
ta_buttons.py
ta_menu_ui.py
ta_nvs_config.py
ta_config.py
ta_logger.py
ta_ota.py
ta_ui_portrait.py
ta_radio_espnow.py    ← FICHIER UNIQUE
ta_radio_433.py
+ Documentation
```

### DD v6.0.1 (7+ fichiers)
```
boot.py
dd_main.py
dd_main_espnow.py
dd_main_433.py
dd_nvs_config.py
ota_mode.py
config_ta_mac.py
utils/nvs_utils.py (si present)
+ Documentation
```

## Support

### TA - Problemes courants

**Titre reste "TA-espnow" en mode 433MHz**
→ ta_main.py v3.3.0 pas deploye

**Menu affiche 5 options au lieu de 4**
→ ta_menu_ui.py v1.2.0 pas deploye

**Erreur "Module not found: ta_radio_espnow"**
→ Fichier ta_radio_espnow.py manquant

### DD - Problemes courants

**SyntaxError au boot**
→ Fichiers avec accents pas remplaces
→ Deployer DD v6.0.1

**DD ne reboot pas lors changement mode TA**
→ Verifier communication TA → DD
→ Verifier reception commande MODE:XXX

## Conclusion

### TA v2.7.0
- Architecture simplifiee
- Titre dynamique
- Fichier unique ESP-NOW
- 8 fichiers modifies

### DD v6.0.1
- Correction compatibilite
- Pas de changement fonctionnel
- 7 fichiers corriges

### Systeme complet
- TA et DD synchronises automatiquement
- 2 modes radio: ESP-NOW et 433MHz
- Communication stable et fiable
