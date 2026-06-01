# TA v2.7.0 - Titre Dynamique

## Modification ajoutee

### Titre selon le mode radio actif

Le titre affiche en haut de l'ecran change automatiquement selon le mode radio:

```
Mode ESP-NOW  →  Titre: "TA-espnow"
Mode 433MHz   →  Titre: "TA-433MHz"
```

## Implementation

### Fichiers modifies

#### ta_main.py (v3.3.0)
Ajout de la logique de titre dynamique dans `load_radio_module()`:

```python
# Ajuster le nom de l'application selon le mode
if mode == RADIO_MODE_ESP_NORMAL:
    config.APP_NAME = "TA-espnow"
elif mode == RADIO_MODE_433:
    config.APP_NAME = "TA-433MHz"
else:
    config.APP_NAME = "TA-espnow"  # Defaut

logger.info("Titre affiche: {}".format(config.APP_NAME), "main")
```

#### ta_config.py (v2.7.0)
- Version mise a jour: 2.5.0 → 2.7.0
- Date: 27.12.2025
- Note ajoutee dans commentaire

### Comment ca fonctionne

1. **Au demarrage:**
   - `ta_main.py` lit le mode radio depuis la NVS
   - Modifie `config.APP_NAME` selon le mode
   - Charge le module radio approprie

2. **Affichage:**
   - `ta_ui_portrait.py` lit `config.APP_NAME`
   - Affiche le titre dans la zone superieure bleue
   - Le titre est centre horizontalement

3. **Logs:**
   ```
   [INFO] Mode radio: ESP-NOW
   [INFO] Titre affiche: TA-espnow
   [INFO] Chargement: ta_radio_espnow
   ```

## Avantages

### 1. Visibilite immediate
- Plus besoin de deviner quel mode est actif
- Information claire en permanence a l'ecran

### 2. Simplicite
- Pas de changement dans ta_ui_portrait.py
- Modification centralisee dans ta_main.py
- Pas d'impact sur les autres composants

### 3. Coherence
- Titre correspond toujours au mode actif
- Mis a jour automatiquement au changement de mode

## Tests de validation

### Test 1: Mode par defaut (ESP-NOW)
```
1. Boot du TA
2. Verifier titre = "TA-espnow"
3. Verifier logs: [INFO] Titre affiche: TA-espnow
```

### Test 2: Passage en mode 433MHz
```
1. Menu → Selection "2. Radio 433MHz"
2. Pression longue → Confirmation
3. Reboot automatique
4. Apres reboot:
   - Verifier titre = "TA-433MHz"
   - Verifier logs: [INFO] Titre affiche: TA-433MHz
5. Tester communication 433MHz
```

### Test 3: Retour en mode ESP-NOW
```
1. Menu → Selection "1. ESP-NOW"
2. Pression longue → Confirmation
3. Reboot automatique
4. Apres reboot:
   - Verifier titre = "TA-espnow"
   - Verifier logs: [INFO] Titre affiche: TA-espnow
5. Tester communication ESP-NOW
```

### Test 4: Migration depuis ancien mode RSSI
```
1. TA avec mode RSSI (1) en NVS
2. Deployer v2.7.0
3. Reboot
4. Verifier:
   - Mode bascule sur ESP-NOW (0)
   - Titre = "TA-espnow"
   - Warning dans logs: "Mode NVS invalide"
```

## Compatibilite

### Avec versions anterieures
- ✓ Compatible v2.6.0 → v2.7.0
- ✓ Pas de changement de protocole
- ✓ Migration automatique

### Avec DD
- ✓ Aucun impact sur les DD
- ✓ Communication inchangee

## En cas de probleme

### Titre reste sur "TA-espnow" en mode 433MHz
**Cause:** ta_main.py v3.3.0 pas deploye
**Solution:** Re-deployer ta_main.py depuis l'archive

### Titre affiche caracteres bizarres
**Cause:** Police ou encodage
**Solution:** Verifier que ta_ui_portrait.py est bien deploye

### Logs n'affichent pas "Titre affiche: ..."
**Cause:** Ancienne version de ta_main.py
**Solution:** Deployer ta_main.py v3.3.0

## Notes techniques

### Pourquoi modifier config.APP_NAME ?
- APP_NAME est deja utilise par ta_ui_portrait.py
- Evite de modifier ta_ui_portrait.py
- Centralise la logique dans ta_main.py
- Solution simple et elegante

### Alternative non retenue
Modifier ta_ui_portrait.py pour lire le mode depuis NVS:
- ✗ Plus complexe
- ✗ Coupling avec NVS
- ✗ Modification dans 2 fichiers

### Futur
Si d'autres modes sont ajoutes, il suffit de:
1. Ajouter le mode dans ta_nvs_config.py
2. Ajouter le cas dans ta_main.py
3. Definir le titre correspondant

Exemple:
```python
elif mode == RADIO_MODE_LORA:
    config.APP_NAME = "TA-LoRa"
```
