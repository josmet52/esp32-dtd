# CHANGELOG - TA (Terminal d'Affichage)

## Version 2.7.1 - 27.12.2025 (CORRECTION CRITIQUE)

### Correction synchronisation ESP-NOW

**Probleme resolu:**
Lors du changement de mode via le menu TA, les DD ne recevaient pas la commande MODE: et restaient dans leur ancien mode.

**Cause:**
La methode `send_to_dd()` n'existait pas dans `ta_radio_espnow.py`.

**Solution:**
- Ajout methode `send_to_dd()` dans ta_radio_espnow.py v6.1.0
- Simplification `_notify_dd_espnow()` dans ta_buttons.py v3.2.1
- Un seul broadcast au lieu d'une boucle inutile

### Fichiers modifies

#### ta_radio_espnow.py (v6.0.0 → v6.1.0)
- Ajout methode `send_to_dd(dd_id, command)`
- Envoi broadcast de commandes MODE: aux DD
- Support synchronisation automatique TA → DD

#### ta_buttons.py (v3.2.0 → v3.2.1)
- Simplification `_notify_dd_espnow()`
- Broadcast unique au lieu de boucle sur DD_IDs

#### ta_config.py
- Version: 2.7.0 → 2.7.1

### Tests critiques

1. Changement ESP-NOW → 433MHz
   - TA envoie MODE:433MHZ
   - DD rebootent en 433MHz
   - Communication fonctionne

2. Changement 433MHz → ESP-NOW
   - TA envoie MODE:ESPNOW
   - DD rebootent en ESP-NOW
   - Communication fonctionne

---

## Version 2.7.0 - 27.12.2025

### Modifications majeures
- **Suppression du mode ESP-NOW RSSI**
- **Fusion des fichiers ESP-NOW en un seul** (ta_radio_espnow.py)
- **Titre dynamique selon le mode radio** (TA-espnow ou TA-433MHz)
- Simplification du systeme: 2 modes radio uniquement (ESP-NOW et Radio 433MHz)
- Menu reduit de 5 a 4 options

### Fichiers modifies

#### 1. ta_menu_ui.py (v1.2.0)
- Suppression de l'option "2. ESP-NOW RSSI" du menu
- Menu simplifie: 
  1. ESP-NOW
  2. Radio 433MHz
  3. OTA Update
  4. Reboot
- Constantes MENU_* ajustees (indices 0-3)

#### 2. ta_nvs_config.py (v1.2.0)
- Suppression de `RADIO_MODE_ESP_RSSI = 1`
- Modes valides: `RADIO_MODE_ESP_NORMAL = 0` et `RADIO_MODE_433 = 2`
- Mise a jour du menu CLI interactif (options 3 et 4 au lieu de 3, 4, 5)
- Mise a jour des fonctions `get_mode_name()` et validation

#### 3. ta_main.py (v3.3.0)
- Suppression de l'import `RADIO_MODE_ESP_RSSI`
- Suppression de la branche `elif mode == RADIO_MODE_ESP_RSSI`
- Chargement simplifie: `ta_radio_espnow` ou `ta_radio_433`
- **Import unique: ta_radio_espnow (au lieu de ta_radio_espnow_normal)**
- **Titre dynamique: modifie config.APP_NAME selon le mode**
  - Mode ESP-NOW → "TA-espnow"
  - Mode 433MHz → "TA-433MHz"

#### 4. ta_buttons.py (v3.2.0)
- Suppression de l'import `RADIO_MODE_ESP_RSSI`
- Suppression de l'import `MENU_ESP_RSSI` 
- Cycle du menu ajuste: `% 4` au lieu de `% 5`
- Suppression de la branche `elif self.menu_selected_index == MENU_ESP_RSSI`
- Mise a jour de `_notify_dd_mode_change()`: 
  - Condition simplifiee pour ESP-NOW (un seul mode)
  - Suppression de la reference a MENU_ESP_RSSI

#### 5. ta_radio_espnow.py (v6.0.0) **NOUVEAU**
- **Fusion de ta_radio_espnow_normal.py dans ta_radio_espnow.py**
- Fichier unique pour la communication ESP-NOW
- En-tete mis a jour (v6.0.0)
- Suppression des references au mode RSSI

#### 6. ta_app.py (modification mineure)
- Mise a jour des imports de fallback
- `ta_radio_espnow_sans_wifi` → `ta_radio_espnow`

#### 7. ta_config.py (v2.7.0)
- Mise a jour version: 2.5.0 → 2.7.0
- Date mise a jour: 27.12.2025
- Note ajoutee: APP_NAME modifie dynamiquement par ta_main.py

### Fichiers non modifies
- boot.py
- ta_logger.py
- ta_ota.py
- ta_radio_433.py
- ta_ui_portrait.py

### Fichiers supprimes
- ✗ ta_radio_espnow_rssi.py (ne plus inclure dans le deploiement)
- ✗ ta_radio_espnow_normal.py (fusionne dans ta_radio_espnow.py)
- ✗ ta_radio_espnow_sans_wifi.py (ancien nom, remplace par ta_radio_espnow.py)

### Tests recommandes
1. Verifier que le menu affiche bien 4 options
2. **Verifier le titre affiche selon le mode:**
   - Mode ESP-NOW → titre = "TA-espnow"
   - Mode 433MHz → titre = "TA-433MHz"
3. Tester la selection ESP-NOW → reboot → verifier mode actif ET titre
4. Tester la selection Radio 433MHz → reboot → verifier mode actif ET titre
5. Verifier que la navigation cyclique fonctionne (0→1→2→3→0)
6. Verifier le mode OTA
7. Verifier le reboot simple

### Notes de migration
- Si un TA avait le mode RSSI actif (RADIO_MODE_ESP_RSSI = 1) en NVS:
  - La validation détectera un mode invalide
  - Le système basculera automatiquement sur ESP-NOW Normal (mode par défaut)
  - Un warning sera loggé

### Compatibilité
- Compatible avec tous les DD existants
- Les DD recevront toujours la même commande "MODE:ESPNOW" qu'avant
- Pas de changement de protocole de communication
