# TA v2.7.1 - CORRECTION Synchronisation ESP-NOW

## Probleme identifie

Lors du changement de mode radio sur le TA (via le menu), la commande `MODE:XXX` n'etait pas envoyee aux DD.

**Symptome:**
- TA passe en mode 433MHz
- DD restent en mode ESP-NOW
- Pas de communication entre TA et DD
- Necessaire de changer le mode manuellement sur chaque DD

## Cause

La methode `send_to_dd()` n'existait pas dans `ta_radio_espnow.py`.

Quand `ta_buttons.py` appelait `self.app.radio.send_to_dd(dd_id, command)`, cela provoquait une erreur silencieuse et la commande n'etait jamais envoyee.

## Solution

### 1. Ajout methode send_to_dd() dans ta_radio_espnow.py

```python
def send_to_dd(self, dd_id, command):
    """
    Envoie une commande en broadcast a tous les DD
    
    Args:
        dd_id (int): ID pour logs uniquement
        command (str): Commande a envoyer (ex: "MODE:ESPNOW\n")
    
    Returns:
        bool: True si envoi reussi
    """
    try:
        # Broadcast (tous les DD recevront)
        broadcast_mac = b'\xff\xff\xff\xff\xff\xff'
        self.esp.send(broadcast_mac, command.encode())
        return True
    except Exception as e:
        self.logger.error("Erreur envoi: {}".format(e), "radio")
        return False
```

### 2. Simplification _notify_dd_espnow() dans ta_buttons.py

**Avant:** Boucle sur tous les DD_IDs (inutile car broadcast)
**Apres:** Un seul envoi broadcast

```python
async def _notify_dd_espnow(self, command, mode_name):
    """Envoie notification via ESP-NOW (broadcast)"""
    try:
        # Un seul broadcast suffit
        success = self.app.radio.send_to_dd(0, command)
        
        if success:
            logger.info("Commande {} broadcast".format(mode_name), "buttons")
    except Exception as e:
        logger.warning("Erreur: {}".format(e), "buttons")
    
    # Attendre que les DD rebootent
    await asyncio.sleep_ms(2000)
```

## Fichiers modifies

1. **ta_radio_espnow.py** (v6.0.0 → v6.1.0)
   - Ajout methode `send_to_dd()`
   - Support envoi commandes MODE

2. **ta_buttons.py** (v3.2.0 → v3.2.1)
   - Simplification `_notify_dd_espnow()`
   - Broadcast unique au lieu de boucle

3. **ta_config.py**
   - Version: 2.7.0 → 2.7.1

## Comment ca fonctionne maintenant

### Sequence complete de changement de mode

1. **Utilisateur selectionne nouveau mode dans menu TA**
   - Ex: "2. Radio 433MHz"
   - Pression longue pour valider

2. **TA envoie commande MODE: aux DD**
   ```
   [INFO] Notification DD: changement vers 433MHz
   [DEBUG] Commande broadcast: MODE:433MHZ
   ```

3. **Tous les DD recoivent la commande**
   ```
   [MODE] Commande recue du TA: 433MHZ
   [MODE] → Changement vers 433MHz
   [MODE] ✓ Mode enregistre en NVS
   [MODE] Reboot dans 500ms...
   ```

4. **DD rebootent en mode 433MHz**

5. **TA attend 2 secondes puis change son mode et reboote**

6. **TA reboote en mode 433MHz**

7. **Systeme synchronise**
   - TA en mode 433MHz (titre: "TA-433MHz")
   - Tous les DD en mode 433MHz
   - Communication fonctionne

## Tests de validation

### Test 1: ESP-NOW → 433MHz

1. **Etat initial:**
   - TA en ESP-NOW (titre: "TA-espnow")
   - DD en ESP-NOW
   - Communication OK

2. **Action:**
   - Menu TA → "2. Radio 433MHz"
   - Pression longue

3. **Verification logs TA:**
   ```
   [INFO] Notification DD: changement vers 433MHz
   [DEBUG] Commande broadcast: MODE:433MHZ
   [INFO] Notification ESP-NOW terminee, attente DD reboot (2s)...
   [INFO] Mode radio enregistre: Radio 433MHz
   [INFO] Reboot...
   ```

4. **Verification logs DD:**
   ```
   [MODE] Commande recue du TA: 433MHZ
   [MODE] → Changement vers 433MHz
   [MODE] ✓ Mode enregistre en NVS
   [MODE] Reboot dans 500ms...
   ```

5. **Apres reboot:**
   - TA titre: "TA-433MHz"
   - DD en mode 433MHz
   - Communication UART fonctionne

### Test 2: 433MHz → ESP-NOW

1. **Etat initial:**
   - TA en 433MHz
   - DD en 433MHz
   - Communication UART OK

2. **Action:**
   - Menu TA → "1. ESP-NOW"
   - Pression longue

3. **Verification:**
   - Logs similaires avec MODE:ESPNOW
   - Reboot synchronise
   - Communication ESP-NOW fonctionne

### Test 3: Avec plusieurs DD

1. **Configuration:**
   - TA avec DD0, DD1, DD2 actifs

2. **Action:**
   - Changement mode via menu TA

3. **Verification:**
   - TOUS les DD recoivent la commande
   - TOUS les DD rebootent
   - TOUS les DD synchronises avec TA

## Broadcast vs Unicast

### Pourquoi broadcast ?

**Avantages:**
- Tous les DD recoivent simultanement
- Un seul envoi necessaire
- Plus rapide
- Plus fiable

**Pas d'inconvenient:**
- La commande MODE: est pour tous les DD
- Tous doivent changer de mode ensemble
- Broadcast est la bonne approche

### Format du message

**Envoye par TA:**
```
MODE:ESPNOW\n
MODE:433MHZ\n
```

**Recu par DD:**
```python
if line.startswith("MODE:"):
    handle_mode_command(line)
```

## Compatibilite

### TA v2.7.1 ↔ DD v6.0.1
✓ 100% compatible
✓ Synchronisation automatique fonctionne

### TA v2.7.0 ↔ DD v6.0.1
✗ Synchronisation ne fonctionne PAS
→ Mettre a jour TA vers v2.7.1

## Migration

### Depuis TA v2.7.0

1. **Deployer les fichiers modifies:**
   - ta_radio_espnow.py (v6.1.0)
   - ta_buttons.py (v3.2.1)
   - ta_config.py (v2.7.1)

2. **Reboot TA**

3. **Tester synchronisation:**
   - Changer mode via menu
   - Verifier DD rebootent
   - Verifier communication

### DD inchange

DD v6.0.1 reste compatible, aucune modification necessaire.

## En cas de probleme

### DD ne rebootent pas

**Cause possible:** Commande MODE: non recue

**Debug:**
1. Activer DEBUG_MODE sur DD
2. Verifier reception message:
   ```
   [RX] MODE:433MHZ  ← Doit apparaitre
   ```
3. Si pas de [RX], probleme communication ESP-NOW

### Logs TA montrent erreur send_to_dd

**Cause:** ta_radio_espnow.py pas v6.1.0

**Solution:** Re-deployer ta_radio_espnow.py v6.1.0

### Un seul DD ne reboote pas

**Cause:** DD trop eloigne ou probleme materiel

**Solution:** 
1. Verifier distance TA ↔ DD
2. Changer mode manuellement sur ce DD
3. Verifier antenne DD
