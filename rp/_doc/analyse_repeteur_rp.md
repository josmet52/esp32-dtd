# Analyse de Faisabilité et Proposition de Solution
## Module Répéteur RP pour le Système DTD

**Date:** 14 janvier 2026  
**Projet:** DTD (Détecteur de Tension Distant)  
**Version TA analysée:** 1.0.0 (13.01.2026)  
**Version DD analysée:** 1.0.0 (13.01.2026)

---

## 1. ANALYSE DE L'ARCHITECTURE EXISTANTE

### 1.1 Architecture Actuelle

Le système DTD actuel comprend :

#### Terminal Afficheur (TA)
- **Hardware:** ESP32-S3 avec écran AMOLED
- **Rôle:** Coordinateur central qui interroge séquentiellement les détecteurs
- **Modes radio supportés:**
  - ESP-NOW (2.4GHz, WiFi sans infrastructure)
  - Radio 433MHz (via module GT38 sur UART)

#### Détecteurs Distants (DD)
- **Hardware:** ESP32 WROVER-T7
- **Rôle:** Détection de tension et réponse aux interrogations du TA
- **ID hardware:** 0-7 (configuré via straps hardware)
- **Modes radio supportés:** ESP-NOW ou 433MHz (configurables via NVS)

### 1.2 Protocole de Communication Actuel

#### Mode ESP-NOW
```
TA → [BROADCAST] → POLL:XX\n
DD (si ID=XX) → [UNICAST to TA] → ACK:XX:Y\n
```
- `XX` : ID du DD (00-07)
- `Y` : État détecté (0=absent, 1=présent)
- Communication séquentielle (un DD à la fois)
- Timeout par défaut : 300ms
- Canal par défaut : 1

#### Mode 433MHz
```
TA → [UART→GT38] → POLL:XX\n
DD → [GT38→UART] → ACK:XX:Y\n
```
- Protocole identique à ESP-NOW
- Baudrate UART : 9600 bps
- Modules GT38 configurables sur différents canaux

### 1.3 Contraintes Identifiées

#### Contraintes Techniques
1. **Communication séquentielle :** Un seul DD interrogé à la fois
2. **Timeout strict :** 300ms par DD
3. **Broadcast initial :** Tous les DD reçoivent POLL mais seul le bon répond
4. **Pas de routage :** Les DD ne peuvent pas relayer les messages
5. **Configuration par NVS :** Les paramètres sont stockés en mémoire non volatile

#### Contraintes Matérielles
1. **Un seul canal ESP-NOW actif :** Un ESP32 ne peut écouter qu'un canal à la fois
2. **Module GT38 mono-canal :** Chaque module 433MHz écoute un seul canal
3. **Ressources mémoire limitées :** ESP32 standard (pas de PSRAM sur DD)

---

## 2. ANALYSE DE FAISABILITÉ

### 2.1 Scénario Proposé : Double Canal

**Principe:**
```
TA (canal 33) ←→ RP ←→ (canal 1) DD1, DD2, DD3...
```

#### Faisabilité ESP-NOW : ❌ **NON RÉALISTE**

**Problèmes majeurs :**

1. **Limitation mono-canal ESP-NOW**
   - Un ESP32 ne peut écouter qu'un seul canal à la fois
   - Pour relayer entre canal 33 et canal 1, le RP devrait :
     - Recevoir sur canal 33
     - Changer vers canal 1
     - Transmettre
     - Attendre réponse
     - Changer vers canal 33
     - Retransmettre
   - **Temps de commutation** : ~100-200ms par changement de canal
   - **Impact** : Avec timeout de 300ms et 2 changements de canal, le délai total dépasserait le timeout

2. **Complexité de synchronisation**
   - Les changements de canal causent des pertes de messages
   - Risque élevé de désynchronisation TA-RP-DD

3. **Configuration requise**
   - Modification majeure du protocole
   - Gestion d'états complexe dans le RP
   - Latence non compatible avec les timeouts actuels

#### Faisabilité 433MHz : ✅ **RÉALISTE ET SIMPLE**

**Avantages :**

1. **Hardware simple**
   - 2 modules GT38 sur le RP
   - GT38-A configuré sur canal 33 (communication avec TA)
   - GT38-B configuré sur canal 1 (communication avec DD)

2. **Relais transparent**
   - Réception sur UART1 (GT38-A) → Transmission sur UART2 (GT38-B)
   - Réception sur UART2 (GT38-B) → Transmission sur UART1 (GT38-A)
   - Latence < 10ms
   - Compatible avec timeout 300ms

3. **Pas de modification du protocole**
   - TA et DD fonctionnent sans changement
   - Répéteur totalement transparent

---

## 3. SOLUTION RECOMMANDÉE

### 3.1 Architecture Proposée

#### Choix : **Radio 433MHz avec Double Module GT38**

```
┌─────────────────────────────────────────────────────┐
│                    SYSTÈME DTD-RP                    │
└─────────────────────────────────────────────────────┘

    TA                    RP                     DD1-DD8
    │                     │                        │
    │  [433MHz Canal 33]  │  [433MHz Canal 1]     │
    │◄───────────────────►│◄─────────────────────►│
    │                     │                        │
    │   POLL:XX           │   POLL:XX             │
    ├────────────────────►├──────────────────────►│
    │                     │                        │
    │   ACK:XX:Y          │   ACK:XX:Y            │
    │◄────────────────────┤◄──────────────────────┤
    │                     │                        │

MODE NORMAL (sans RP):
    TA [433MHz Canal 1] ◄──────────────────────► DD1-DD8

Configuration TA:
    - Menu: "Utiliser répéteur: OUI/NON"
    - Si OUI → Canal 33
    - Si NON → Canal 1
```

### 3.2 Hardware du Répéteur RP

#### Composants Principaux

1. **Microcontrôleur:** ESP32 (standard, pas besoin de WROVER)
   - 2 UART disponibles (UART1 et UART2)
   - Alimentation USB ou batterie
   - Consommation : ~100mA en fonctionnement

2. **Modules Radio:**
   - **GT38-A (Interface TA):**
     - Connecté sur UART1
     - Canal configuré sur 33
     - TX1 (GPIO17), RX1 (GPIO16)
     - PIN_SET1 (GPIO4)
   
   - **GT38-B (Interface DD):**
     - Connecté sur UART2
     - Canal configuré sur 1
     - TX2 (GPIO25), RX2 (GPIO26)
     - PIN_SET2 (GPIO27)

3. **Indicateurs:**
   - LED verte : Alimentation
   - LED orange : Activité canal TA
   - LED bleue : Activité canal DD
   - LED rouge : Erreur

4. **Alimentation:**
   - USB-C 5V
   - Ou batterie Li-Ion 3.7V (avec régulateur 3.3V)
   - Optionnel : Solar panel pour installation permanente

#### Schéma de Principe

```
┌──────────────────────────────────────────────────┐
│                   ESP32 RP                        │
│                                                   │
│  UART1 (GPIO17/16) ◄───► GT38-A (Canal 33)      │
│  SET1 (GPIO4)                  │                 │
│                                433MHz ◄──► TA    │
│                                                   │
│  UART2 (GPIO25/26) ◄───► GT38-B (Canal 1)       │
│  SET2 (GPIO27)                 │                 │
│                                433MHz ◄──► DD    │
│                                                   │
│  LED Status (GPIO19, 21, 22, 23)                │
│  USB-C Power (5V → 3.3V)                         │
└──────────────────────────────────────────────────┘
```

### 3.3 Configuration des Canaux GT38

Les modules GT38 ont 33 canaux configurables (1-33). Configuration via AT commands ou straps hardware.

**Configuration recommandée:**

| Module | Canal | Fréquence | Usage |
|--------|-------|-----------|-------|
| GT38-A | 33    | 433.920 MHz | Communication TA ←→ RP |
| GT38-B | 1     | 433.000 MHz | Communication RP ←→ DD |

**Note:** La séparation de 32 canaux (920 kHz) assure une isolation RF suffisante pour éviter les interférences.

---

## 4. ARCHITECTURE SOFTWARE

### 4.1 Structure du Firmware RP

```
rp_main.py          # Point d'entrée principal
rp_config.py        # Configuration et constantes
rp_relay.py         # Logique de relais
rp_uart_manager.py  # Gestion des UART
rp_led_status.py    # Gestion des LED
boot.py             # Initialisation au démarrage
```

### 4.2 Logique de Fonctionnement

#### Mode de Fonctionnement : Relais Bidirectionnel Simple

```python
# Pseudo-code du répéteur

while True:
    # Direction 1 : TA → DD
    if uart1.any():  # Message du TA (GT38-A)
        data = uart1.read()
        uart2.write(data)  # Relai vers DD (GT38-B)
        led_orange.blink()
    
    # Direction 2 : DD → TA
    if uart2.any():  # Message des DD (GT38-B)
        data = uart2.read()
        uart1.write(data)  # Relai vers TA (GT38-A)
        led_bleue.blink()
    
    time.sleep_ms(1)
```

**Avantages:**
- Ultra-simple et robuste
- Latence < 10ms
- Aucune intelligence requise
- Fonctionne avec le protocole existant sans modification

#### Statistiques (Optionnel)

Le RP peut collecter des statistiques de relais :
- Nombre de messages relayés TA→DD
- Nombre de messages relayés DD→TA
- Qualité du signal (RSSI si disponible)
- Uptime

### 4.3 Gestion d'Erreurs

**Détection:**
- Timeout UART
- Buffer overflow
- Erreur de décodage

**Actions:**
- Flush des buffers UART
- Clignotement LED rouge
- Log sur port série (pour debug)
- Pas de reboot automatique (le RP doit rester actif)

---

## 5. MODIFICATIONS REQUISES

### 5.1 Modifications TA

#### Nouveau Paramètre NVS

```python
# Dans ta_nvs_config.py
def get_use_repeater():
    """
    Lit si le répéteur est activé
    Returns: bool (défaut: False)
    """
    return nvs_utils.get_i32("DTD", "use_repeater", default=0) == 1

def set_use_repeater(enabled):
    """
    Active/désactive le répéteur
    Args: enabled (bool)
    """
    nvs_utils.set_i32("DTD", "use_repeater", 1 if enabled else 0)
```

#### Configuration du Canal GT38

```python
# Dans ta_radio_433.py
def configure_gt38_channel(channel):
    """
    Configure le canal du module GT38
    Args: channel (int) : 1-33
    """
    # Option 1 : Via AT command
    uart.write("AT+CHANNEL={}\r\n".format(channel).encode())
    
    # Option 2 : Via pin SET et straps (méthode hardware)
    # Nécessite séquence spécifique selon datasheet GT38
```

#### Logique de Sélection du Canal

```python
# Dans ta_radio_433.py __init__()
use_repeater = nvs_utils.get_i32("DTD", "use_repeater", default=0) == 1

if use_repeater:
    channel = 33  # Canal pour communication avec RP
else:
    channel = 1   # Canal pour communication directe avec DD
    
configure_gt38_channel(channel)
```

#### Interface Menu

```python
# Dans ta_menu_ui.py
# Ajouter une nouvelle entrée de menu:

MENU_ITEMS = [
    # ... existant ...
    "Répéteur",  # Nouvelle entrée
    # ... existant ...
]

def menu_repeater():
    """Gestion du répéteur"""
    current = nvs_config.get_use_repeater()
    
    choices = [
        "Désactivé" if not current else "◄ Désactivé",
        "Activé" if current else "◄ Activé",
        "Retour"
    ]
    
    # Affichage et sélection
    # ...
    
    if selection == 0 or selection == 1:
        new_state = (selection == 1)
        nvs_config.set_use_repeater(new_state)
        
        # Reconfigurer le canal radio
        radio.reconfigure_channel(33 if new_state else 1)
        
        ui.show_message("Répéteur: {}".format(
            "Activé (canal 33)" if new_state else "Désactivé (canal 1)"
        ))
```

### 5.2 Modifications DD

#### Aucune Modification Requise ! ✅

Les DD continuent de fonctionner sur le canal 1 en mode 433MHz.
Ils ne sont pas conscients de l'existence du répéteur.

**Raison:** Le répéteur est totalement transparent. Les DD reçoivent les mêmes commandes POLL et renvoient les mêmes réponses ACK, que le TA communique directement ou via le RP.

---

## 6. WORKFLOW D'UTILISATION

### 6.1 Installation Initiale

1. **Prérequis:**
   - Système DTD fonctionnel en mode 433MHz
   - TA et DD configurés sur canal 1

2. **Configuration du RP:**
   - Flasher le firmware RP
   - Les modules GT38 sont pré-configurés (canal 33 et canal 1)
   - Alimenter le RP (USB ou batterie)

3. **Test sans répéteur:**
   - Vérifier que TA communique avec DD (canal 1)
   - Noter la portée maximale

4. **Activation du répéteur:**
   - Placer le RP à mi-distance entre TA et DD
   - Sur le TA : Menu → Répéteur → Activé
   - Le TA bascule automatiquement sur canal 33
   - Vérifier la communication via l'écran TA

### 6.2 Désactivation du Répéteur

1. Sur le TA : Menu → Répéteur → Désactivé
2. Le TA rebascule automatiquement sur canal 1
3. Éteindre le RP (optionnel)

### 6.3 Diagnostic

**LED du RP:**
- ✅ Verte fixe : Alimentation OK
- 🟠 Orange clignote : Messages TA → DD relayés
- 🔵 Bleue clignote : Messages DD → TA relayés
- 🔴 Rouge clignote : Erreur (buffer overflow, etc.)

**Problèmes potentiels:**

| Symptôme | Cause Probable | Solution |
|----------|---------------|----------|
| Pas de communication | RP mal positionné | Rapprocher le RP du TA ou des DD |
| Communication intermittente | Interférences | Vérifier séparation des canaux |
| LED rouge | Surcharge UART | Réduire nombre de DD ou augmenter timeout |
| Aucune LED | Alimentation | Vérifier USB ou batterie |

---

## 7. ÉVOLUTIONS FUTURES

### 7.1 Améliorations Possibles

1. **Mode ESP-NOW avec double ESP32:**
   - Utiliser 2 ESP32 sur le RP
   - ESP32-A : Interface TA (canal 33)
   - ESP32-B : Interface DD (canal 1)
   - Communication interne via UART ou I2C
   - **Complexité:** Moyenne
   - **Avantage:** Portée ESP-NOW (100-200m en extérieur)

2. **Sélection automatique du canal:**
   - Le RP scanne les canaux pour trouver le meilleur
   - Configuration OTA du RP depuis le TA
   - **Complexité:** Élevée

3. **Mesh network:**
   - Plusieurs RP en cascade
   - Augmentation de portée quasi-illimitée
   - **Complexité:** Très élevée
   - **Nécessite:** Modification profonde du protocole

4. **Alimentation solaire:**
   - Panneau solaire + batterie Li-Ion
   - Gestion de charge
   - Mode veille intelligent
   - **Complexité:** Faible
   - **Avantage:** Installation permanente sans maintenance

### 7.2 Optimisations

1. **Buffer circulaire:**
   - Éviter les pertes de messages en cas de burst
   - Taille : 1024 bytes par UART

2. **Compression des messages:**
   - Réduction de la taille des messages (optionnel)
   - Gain : ~30% de bande passante

3. **Accusé de réception RP:**
   - Le RP envoie un ACK au TA confirmant le relais
   - Permet au TA de détecter une panne du RP

---

## 8. ESTIMATION DES COÛTS

### 8.1 Coûts Matériel (par unité RP)

| Composant | Quantité | Prix Unitaire | Total |
|-----------|----------|---------------|-------|
| ESP32 DevKit | 1 | 4€ | 4€ |
| Module GT38 | 2 | 3€ | 6€ |
| Boîtier plastique | 1 | 2€ | 2€ |
| LED 3mm | 4 | 0.10€ | 0.40€ |
| Résistances | 4 | 0.05€ | 0.20€ |
| Connecteurs | 1 set | 1€ | 1€ |
| PCB (optionnel) | 1 | 2€ | 2€ |
| **Total par RP** | | | **~15-16€** |

### 8.2 Coûts Développement

| Tâche | Estimation | Complexité |
|-------|------------|------------|
| Firmware RP | 8-12h | Faible |
| Modifications TA | 4-6h | Faible |
| Tests et validation | 4-6h | Moyenne |
| Documentation | 2-3h | Faible |
| **Total** | **18-27h** | |

---

## 9. CONCLUSION

### 9.1 Faisabilité Globale : ✅ **EXCELLENTE**

**Points forts:**
1. Solution 433MHz simple et robuste
2. Aucune modification des DD requise
3. Modifications mineures du TA
4. Coût matériel faible (~15€)
5. Répéteur totalement transparent
6. Compatible avec le protocole existant

**Points faibles:**
1. Nécessite mode 433MHz (pas ESP-NOW)
2. Configuration manuelle du TA pour activer le répéteur
3. Portée toujours limitée (RP ajoute 1 saut, pas plusieurs)

### 9.2 Recommandations

#### Court terme (Implémentation immédiate)
1. Développer le firmware RP en mode 433MHz double GT38
2. Ajouter le paramètre "use_repeater" dans le TA
3. Tester avec 1-2 DD en conditions réelles
4. Valider la portée étendue

#### Moyen terme (3-6 mois)
1. Optimiser les buffers et la gestion d'erreurs
2. Ajouter statistiques de relais accessibles depuis le TA
3. Développer boîtier IP65 pour installation extérieure
4. Option alimentation solaire

#### Long terme (6-12 mois)
1. Explorer solution ESP-NOW avec double ESP32
2. Évaluer le mode mesh pour portée illimitée
3. Configuration OTA du RP depuis le TA

### 9.3 Prochaines Étapes

1. **Validation de principe** (1-2 jours)
   - Assembler un prototype RP avec 2 GT38
   - Tester le relais simple en laboratoire
   - Mesurer la latence réelle

2. **Développement firmware** (1 semaine)
   - Implémenter rp_main.py
   - Implémenter gestion UART et LED
   - Tests unitaires

3. **Intégration TA** (2-3 jours)
   - Ajouter menu répéteur
   - Implémenter changement de canal
   - Tests d'intégration

4. **Tests terrain** (1 semaine)
   - Tests de portée
   - Tests en environnement réel
   - Validation finale

---

## 10. ANNEXES

### 10.1 Brochage ESP32 pour RP

```
┌─────────────────────────────────┐
│         ESP32 DevKit            │
├─────────────────────────────────┤
│ UART1 (GT38-A - Canal 33)      │
│   GPIO17 → TX1 → GT38-A TX     │
│   GPIO16 → RX1 → GT38-A RX     │
│   GPIO4  → SET1 → GT38-A SET   │
│                                 │
│ UART2 (GT38-B - Canal 1)       │
│   GPIO25 → TX2 → GT38-B TX     │
│   GPIO26 → RX2 → GT38-B RX     │
│   GPIO27 → SET2 → GT38-B SET   │
│                                 │
│ LED Status                      │
│   GPIO19 → LED Verte (PWR)     │
│   GPIO21 → LED Orange (TA)     │
│   GPIO22 → LED Bleue (DD)      │
│   GPIO23 → LED Rouge (ERR)     │
│                                 │
│ Alimentation                    │
│   5V USB → Régulateur → 3.3V   │
│   GND                           │
└─────────────────────────────────┘
```

### 10.2 Configuration Modules GT38

#### Via AT Commands (nécessite mode configuration)
```
AT+CHANNEL=33    # Pour GT38-A
AT+CHANNEL=1     # Pour GT38-B
AT+POWER=20      # Puissance max (20 dBm)
AT+SAVE          # Sauvegarder
```

#### Via Hardware (straps lors du boot)
Consulter la datasheet GT38 pour la séquence de configuration des straps.

### 10.3 Tableau de Compatibilité

| Mode TA | Mode DD | RP Nécessaire | Canal TA | Canal DD | Compatible |
|---------|---------|---------------|----------|----------|------------|
| 433MHz | 433MHz | NON | 1 | 1 | ✅ |
| 433MHz | 433MHz | OUI | 33 | 1 | ✅ |
| ESP-NOW | ESP-NOW | NON | 1 | 1 | ✅ |
| ESP-NOW | ESP-NOW | OUI | - | - | ❌ (non implémenté) |
| 433MHz | ESP-NOW | - | - | - | ❌ (incompatible) |
| ESP-NOW | 433MHz | - | - | - | ❌ (incompatible) |

---

**Fin du document d'analyse**

**Auteur:** Claude (Assistant IA)  
**Date:** 14 janvier 2026  
**Version:** 1.0
