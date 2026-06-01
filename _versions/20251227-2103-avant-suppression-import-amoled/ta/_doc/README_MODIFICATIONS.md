# TA v2.7.0 - Simplification Architecture ESP-NOW

## Resume des modifications

Le mode ESP-NOW RSSI a ete supprime du systeme TA ET les fichiers ESP-NOW ont ete fusionnes en un seul pour simplifier l'architecture:
1. **ESP-NOW** (mode par défaut, sans WiFi, performances maximales)
2. **Radio 433MHz** (mode legacy)
3. **OTA Update** (mise à jour firmware)
4. **Reboot** (redémarrage)

## Fichiers modifiés

### 1. **ta_menu_ui.py** (v1.1.1 → v1.2.0)
**Changements :**
- Menu réduit de 5 à 4 options
- Suppression de "2. ESP-NOW RSSI"
- Réindexation : 
  - MENU_ESP_NORMAL = 0
  - MENU_433MHZ = 1 (était 2)
  - MENU_OTA = 2 (était 3)
  - MENU_REBOOT = 3 (était 4)

**Impact :**
- Interface utilisateur simplifiée
- Navigation plus rapide dans le menu

### 2. **ta_nvs_config.py** (v1.1.0 → v1.2.0)
**Changements :**
- Suppression de `RADIO_MODE_ESP_RSSI = 1`
- Modes valides: 0 (ESP-NOW) et 2 (433MHz)
- Menu CLI interactif mis à jour
- Fonction `quick_set_mode()` adaptée ('espnow' ou '433')

**Impact :**
- Configuration NVS simplifiée
- Validation stricte des modes (0 ou 2 uniquement)
- Migration automatique si mode RSSI (1) détecté → bascule sur ESP-NOW (0)

### 3. **ta_main.py** (v3.0.0 → v3.1.0)
**Changements :**
- Suppression de l'import `RADIO_MODE_ESP_RSSI`
- Suppression du chargement conditionnel de `ta_radio_espnow_rssi`
- Logique simplifiée : ESP-NOW Normal OU Radio 433MHz

**Impact :**
- Code plus lisible
- Moins de dependances au demarrage
- Temps de boot legerement reduit

### 4. **ta_buttons.py** (v3.1.2 → v3.2.0)
**Changements :**
- Navigation menu : `% 5` → `% 4`
- Suppression de la gestion du cas `MENU_ESP_RSSI`
- Notification DD simplifiée (un seul mode ESP-NOW)

**Impact :**
- Cycle de navigation correct (4 options)
- Code de gestion des evenements simplifie

### 5. **ta_radio_espnow.py** (nouveau fichier unique v6.0.0)
**Changements :**
- Fusion de ta_radio_espnow_normal.py dans ta_radio_espnow.py
- Fichier unique pour toute la communication ESP-NOW
- En-tete mis a jour (v6.0.0)
- Suppression des references au mode RSSI

**Impact :**
- Architecture simplifiee
- Plus de confusion entre _normal et _rssi
- Un seul fichier a maintenir

### 6. **ta_app.py** (modification mineure)
**Changements :**
- Mise a jour des imports de fallback
- ta_radio_espnow_sans_wifi → ta_radio_espnow

**Impact :**
- Coherence avec le nouveau nom de fichier

## Fichiers NON modifies

Ces fichiers restent inchanges car ils n'ont pas de references au mode RSSI :
- boot.py
- ta_config.py
- ta_logger.py
- ta_ota.py
- ta_radio_433.py
- ta_ui_portrait.py

## Fichiers a supprimer

**⚠️ IMPORTANT : Ne pas deployer ces fichiers**
- `ta_radio_espnow_rssi.py` → A SUPPRIMER de vos backups
- `ta_radio_espnow_normal.py` → A SUPPRIMER (fusionne dans ta_radio_espnow.py)
- `ta_radio_espnow_sans_wifi.py` → A SUPPRIMER (ancien nom)

## Installation

1. **Sauvegarder la configuration actuelle**
   ```python
   from ta_nvs_config import show_current_mode
   show_current_mode()  # Noter le mode actuel
   ```

2. **Deployer les nouveaux fichiers**
   - Copier tous les fichiers de l'archive
   - SUPPRIMER les anciens fichiers: ta_radio_espnow_rssi.py, ta_radio_espnow_normal.py
   - Remplacer les fichiers modifies
   - Le nouveau fichier unique est ta_radio_espnow.py

3. **Redémarrer le TA**
   ```python
   import machine
   machine.reset()
   ```

4. **Vérifier le mode actif**
   - Si précédemment en mode RSSI → bascule auto sur ESP-NOW
   - Sinon → mode conservé

## Migration automatique

**Cas 1 : TA était en mode ESP-NOW Normal (0)**
- ✓ Aucun changement
- ✓ Fonctionne directement

**Cas 2 : TA était en mode ESP-NOW RSSI (1)**
- ⚠️ Mode invalide détecté
- → Bascule automatique sur ESP-NOW Normal (0)
- → Warning dans les logs

**Cas 3 : TA était en mode Radio 433MHz (2)**
- ✓ Aucun changement
- ✓ Fonctionne directement

## Tests recommandés

### Test 1 : Navigation menu
1. Pression longue bouton → Menu affiché
2. Pressions courtes → Cycle 0→1→2→3→0
3. Vérifier affichage correct des 4 options

### Test 2 : Sélection ESP-NOW
1. Menu → Sélectionner "1. ESP-NOW"
2. Pression longue → Confirmation → Reboot
3. Vérifier démarrage en mode ESP-NOW
4. Vérifier communication avec les DD

### Test 3 : Sélection Radio 433MHz
1. Menu → Sélectionner "2. Radio 433MHz"
2. Pression longue → Confirmation → Reboot
3. Vérifier démarrage en mode 433MHz
4. Vérifier communication avec les DD

### Test 4 : Mode OTA
1. Menu → Sélectionner "3. OTA Update"
2. Pression longue → Activation OTA
3. Vérifier passage en mode OTA

### Test 5 : Reboot
1. Menu → Sélectionner "4. Reboot"
2. Pression longue → Redémarrage
3. Vérifier redémarrage propre

## Compatibilité

### Avec les DD
- ✓ 100% compatible
- Les DD reçoivent toujours `MODE:ESPNOW` ou `MODE:433MHZ`
- Aucune modification nécessaire côté DD

### Avec les anciens TA
- ⚠️ Pas de compatibilité descendante
- Ne pas mélanger anciennes/nouvelles versions
- Migrer tous les TA ensemble

## Support

### En cas de problème

**Symptôme : Menu n'affiche que 3 options**
→ Fichier `ta_menu_ui.py` non mis à jour correctement

**Symptôme : Erreur "Mode invalide" au boot**
→ Normal si ancien mode RSSI (1) en NVS
→ Système bascule automatiquement sur ESP-NOW (0)

**Symptôme : Navigation menu incorrecte**
→ Fichier `ta_buttons.py` non mis à jour
→ Vérifier ligne `% 4` dans `_menu_next_item()`

### Logs utiles

```python
from ta_logger import get_logger
logger = get_logger()

# Vérifier mode actif
from ta_nvs_config import show_current_mode
show_current_mode()

# Voir contenu NVS
from ta_nvs_config import NVSConfig
NVSConfig.dump_nvs()
```

## Prochaines étapes

Pour le DD, il faudra probablement faire des modifications similaires si des références au mode RSSI existent.

Voulez-vous que je procède maintenant avec les modifications du DD ?
