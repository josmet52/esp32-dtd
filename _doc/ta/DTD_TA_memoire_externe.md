# DTD — TA : Mémoire externe
**Projet : DTD (Détecteur de Tension à Distance)**
**Composant : TA (Transmetteur-Afficheur) — v2.7.1 — 27.12.2025**
GitHub : https://github.com/JOM52/esp32-dtd

---

## C'EST QUOI CE PROJET, DÉJÀ ?

Un système de surveillance sans fil. Des capteurs distants (les **DD** = Détecteurs Distants) détectent si quelque chose est présent ou absent (tension, objet, peu importe). Le **TA** est le boîtier central qui interroge tous les DD en boucle et affiche leur état sur son écran.

```
         ┌──────────────────────────────────┐
         │  TA — LilyGO T-Display-S3 AMOLED │
         │  (ESP32-S3, écran 240×536)       │
         └─────────────┬────────────────────┘
                       │
                       │
          ┌────────────┴────────────────────┐
          │ ESP-NOW (défaut)                │
          │   ou 433MHz via HC-12           │
          └──┬───┬───┬───┬───┬───┬───┬───┬──┘
             │   │   │   │   │   │   │   │
           DD0  DD1 DD2 DD3 DD4 DD5 DD6 DD7
```

Le TA envoie `POLL:XX`, le DD répond `ACK:XX:1` (présent) ou `ACK:XX:0` (absent).

---

## HARDWARE EN UN COUP D'ŒIL

**Carte :** LilyGO T-Display-S3 AMOLED  
**MCU :** ESP32-S3

| Ce que ça fait | GPIO | Détail |
|---|---|---|
| Bouton menu | 0 | PULL_UP, actif à LOW. Pression longue (1.5s) → menu |
| Bouton Down | 21 | PULL_UP, réservé mais câblé |
| Batterie (ADC) | 4 | Diviseur ×2, ATTN_11DB. Lire → multiplier ×2 |
| UART TX → HC-12 | 43 | Mode 433MHz seulement |
| UART RX ← HC-12 | 44 | Mode 433MHz seulement |
| HC-12 SET | 45 | Initialisation : LOW 50ms puis HIGH |
| Écran alimentation | 38 | **CRITIQUE** — doit être HIGH sinon écran mort |

**Point piège écran :** `TFT_CDE = GPIO38` doit être mis à `1` avant TOUT. Si l'écran reste noir, c'est probablement ça.

**Point piège couleurs :** Cet écran AMOLED utilise le format **BRG565** et non RGB565. La fonction `color565(r, g, b)` dans `tft_config_amoled.py` fait la conversion. Si tes couleurs semblent inversées, c'est ce bug-là.

---

## LES FICHIERS ET CE QU'ILS FONT

```
main.py              ← 2 lignes. Point d'entrée. Toucher = jamais.
ta_main.py           ← Lit le mode radio en NVS, charge le bon module radio, lance TaApp
ta_app.py            ← Le chef d'orchestre. Boucle principale, gestion états DD, batterie
ta_config.py         ← TOUT CE QUE TU VEUX CHANGER EST LÀ. Pas ailleurs.
ta_radio_espnow.py   ← Moteur radio ESP-NOW (mode par défaut)
ta_radio_433.py      ← Moteur radio 433MHz via UART/HC-12
ta_buttons.py        ← Gestion bouton + menu de configuration
ta_menu_ui.py        ← Affichage du menu (passe en mode paysage le temps du menu)
ta_ui_portrait.py    ← Tout l'affichage en mode portrait (l'écran normal)
ta_nvs_config.py     ← Lit/écrit le mode radio dans la mémoire flash (NVS)
ta_logger.py         ← Système de log (DEBUG/INFO/WARNING/ERROR/CRITICAL)
ta_ota.py            ← Mise à jour firmware Over The Air
tft_config_amoled.py ← Config bas niveau de l'écran AMOLED (QSPI, GPIO38, BRG565)
fonts/               ← Polices bitmap (vga2_16x16, vga2_bold_16x32, etc.)
```

**Règle d'or : si tu veux changer un comportement, commence par `ta_config.py`.**

---

## COMMENT ÇA DÉMARRE (séquence de boot)

```
main.py
  └── ta_main.py::main()
        └── load_radio_module()         ← lit NVS pour savoir quel mode radio
              └── charge ta_radio_espnow OU ta_radio_433
        └── TaApp(radio_module=...)
              ├── UIPortrait()           ← init écran (GPIO38 → 1, fond noir)
              ├── ButtonManager()        ← init boutons GPIO0 et GPIO21
              ├── RadioESPNow() ou Radio433()  ← init WiFi/UART
              ├── check_hardware()       ← si False → écran rouge, boucle infinie
              └── run()                  ← boucle asyncio
                    ├── _print_stats()   ← tâche périodique (si DEBUG_MODE)
                    ├── check_buttons()  ← tâche permanente
                    ├── _update_battery_periodic()  ← toutes les 30s
                    └── while True:
                          ├── _update_states()   ← poll tous les DD
                          ├── _refresh_ui()      ← redessine l'écran
                          └── sleep 10ms
```

---

## LES DEUX MODES RADIO

Le mode actif est stocké en **NVS** (mémoire flash persistante, survit au reboot).

| Mode | Constante | Valeur NVS | Module chargé | Titre affiché |
|---|---|---|---|---|
| ESP-NOW | `RADIO_MODE_ESP_NORMAL` | 0 | `ta_radio_espnow.py` | `TA-espnow` |
| 433MHz | `RADIO_MODE_433` | 2 | `ta_radio_433.py` | `TA-433MHz` |

**Mode par défaut à la première mise en route :** ESP-NOW (si rien en NVS).

### Changer le mode depuis le REPL (sans menu physique)
```python
from ta_nvs_config import quick_set_mode
quick_set_mode('espnow')   # ou '433'
import machine; machine.reset()
```

### Comment fonctionne le poll (même logique pour les deux modes)
1. Pour chaque DD (DD0 à DD7, séquentiellement) :
2. Envoie `POLL:00\n`, `POLL:01\n`, etc.
3. Attend `ACK:XX:Y` pendant 300ms max (`REPLY_TIMEOUT_MS`)
4. Si pas de réponse → état `UNKNOWN` (gris à l'écran)
5. Si `Y=1` → `PRESENT` (vert), si `Y=0` → `ABSENT` (rouge)

### Différence ESP-NOW vs 433MHz
- **ESP-NOW** : broadcast WiFi (`FF:FF:FF:FF:FF:FF`). Pas de RSSI dans cette version. Les DD non encore vus sont ajoutés comme peers au premier ACK reçu.
- **433MHz** : UART2 (9600 baud, TX=43, RX=44). Pin SET GPIO45 à initialiser. Pas de RSSI non plus.

---

## L'INTERFACE — CE QUE TU VOIS À L'ÉCRAN

```
┌──────────────────────┐  ← Header bleu, nom du mode (TA-espnow)
│     TA-espnow        │
├──────────────────────┤
│ DD0  [  ON   ]       │  ← Vert si présent
│ DD1  [  OFF  ]       │  ← Rouge si absent
│ DD2  [ no signal ]   │  ← Gris si pas de réponse
│ DD3  [  ON   ]       │
│ ...                  │
│ DD7  [  ON   ]       │
├──────────────────────┤
│ (zone log/statut)    │  ← Message status() affiché ici via logger
├──────────────────────┤
│ v2.7.1               │  ← Zone version
│ 3.82V 45%            │  ← Tension et % batterie (mis à jour toutes 30s)
│ RSSI: -55dBm         │  ← RSSI moyen (si disponible)
├──────────────────────┤
│████████████████████  │  ← Barre heartbeat cyan (clignote à chaque cycle)
└──────────────────────┘
```

**Rendu "dirty" :** L'écran ne se redessine pas en entier à chaque fois. Chaque zone a un flag `_dirty_xxx`. Seules les zones marquées dirty sont redessinées → optimisation pour AMOLED.

**Menu (pression longue bouton GPIO0) :**
- L'écran bascule en **mode paysage** le temps du menu
- Options : ESP-NOW / 433MHz / OTA Update / Reboot
- Navigation : pression courte = item suivant, pression longue = valider
- Avant de changer de mode radio, le TA envoie `MODE:ESPNOW\n` ou `MODE:433MHZ\n` aux DD pour qu'ils se synchronisent, puis reboot

---

## PARAMÈTRES QUE TU VAS SÛREMENT VOULOIR TOUCHER

Tout est dans **`ta_config.py`** :

```python
# Quels DD surveiller (par défaut 0 à 7)
RADIO["GROUP_IDS"] = [0, 1, 2, 3, 4, 5, 6, 7]

# Si un DD ne répond pas dans ce délai → UNKNOWN (gris)
RADIO["REPLY_TIMEOUT_MS"] = 300   # ms

# Logs verbeux dans le terminal série
MAIN["DEBUG_MODE"] = True   # False = moins de bruit

# Niveau de log (DEBUG, INFO, WARNING, ERROR)
LOGGER["LEVEL"] = "INFO"

# WiFi (utilisé uniquement pour OTA)
HARDWARE["WIFI"]["SSID"] = "ton_ssid"
HARDWARE["WIFI"]["PASSWORD"] = "ton_mdp"
```

---

## DEBUGGING — PAR OÙ COMMENCER

### Le TA démarre mais écran noir
→ Vérifie que `TFT_CDE` (GPIO38) est bien à `1` dans `tft_config_amoled.py::config()`.

### "Hardware non disponible — Arrêt" / écran rouge
→ `check_hardware()` a retourné `False`. Pour ESP-NOW : module espnow planté. Pour 433MHz : UART non initialisé (câble débranché ? mauvais GPIO ?).

### Les DD apparaissent tous en gris (no signal)
→ Vérifie que le mode radio est correct (`show_current_mode()` dans REPL). Vérifie que les DD sont en vie et dans le bon mode. Vérifie `REPLY_TIMEOUT_MS` (300ms, peut être trop court).

### Voir les logs en direct
Connecte-toi en REPL (Thonny ou `mpremote`). Avec `DEBUG_MODE = True`, tu verras chaque POLL envoyé et chaque ACK reçu.

### Forcer un état depuis le REPL
```python
# Voir le mode radio actuel
from ta_nvs_config import show_current_mode
show_current_mode()

# Voir/modifier le mode
from ta_nvs_config import interactive_menu
interactive_menu()
```

### Statistiques radio en live
```python
# (après interruption Ctrl+C du main)
import ta_main
# ou accéder à app.radio.get_stats() si tu as une référence à l'app
```

---

## CE QUI N'EXISTE PAS ENCORE / PISTES FUTURES

- **RSSI** : Les stubs `get_rssi()` existent dans les deux modules radio mais retournent toujours `None`. L'UI sait afficher le RSSI s'il était disponible. À implémenter dans une future version ESP-NOW.
- **Watchdog** : présent dans le code (`WATCHDOG_ENABLED = False`). Il suffit de passer à `True` si des freezes sont observés.
- **Bouton DOWN** (GPIO21) : câblé, initialisé, mais non utilisé dans la logique actuelle.
- **Mode test DD individuel** : le squelette existe (`start_testing_dd`, `stop_testing_dd`) mais n'est pas exposé via l'UI.
- **Logger vers fichier** : la classe `FileHandler` existe dans `ta_logger.py`. Il suffit de l'instancier et de l'ajouter avec `logger.add_handler(FileHandler("/logs.txt"))`.

---

## INSTALLATION DU FIRMWARE MICROPYTHON SUR LE T-DISPLAY-S3 AMOLED

> À faire uniquement sur une carte neuve, ou si le firmware est corrompu / à mettre à jour.

**Répertoire de travail :**
`C:\Users\jmetr\kDrive_jo\technique\_projets\DTD\_utils\lilygo_t-displa-s3-amoled`

**Sources firmware sur GitHub :**
https://github.com/dobodu/Lilygo_Waveshare_Amoled_Micropython

**Clone local du repo :**
`C:\Users\jmetr\kDrive_jo\technique\_projets\DTD\_utils\lilygo\Lilygo_Waveshare_Amoled_Micropython`

### Procédure pas à pas

**1.** Ouvrir une fenêtre de commande dans le répertoire de travail : taper `cmd` + ENTRÉE dans la barre d'adresse de l'explorateur.

**2.** Connecter le T-Display au PC par câble USB.

**3.** Mettre le T-Display en mode **BOOT** : maintenir le bouton `BOOT` enfoncé, appuyer sur `RESET`, puis relâcher `BOOT`.

**4.** Ouvrir le Gestionnaire de périphériques Windows et noter le port COM attribué (ex: `COM7`).

**5a.** Effacer la mémoire flash :
```
python -m esptool --port COM7 erase-flash
```

**5b.** Flasher le firmware :
```
python -m esptool --chip esp32s3 --port COM7 --baud 460800 write-flash --flash-mode dio --flash-freq 80m --flash-size 16MB -z 0x0 lilygo_Waveshare_Amoled_Micropython\firmware\firmware_2026_01_05.bin
```

**6.** Faire un `RESET` du module. Rouvrir le Gestionnaire de périphériques — le port COM peut avoir changé après le flash.

**7.** Ouvrir **Thonny**, se connecter sur le nouveau port COM, et vérifier que le REPL MicroPython répond.

> **Piège fréquent :** si le flash plante avec `invalid header: 0xffffffff` au reboot, c'est presque toujours un effacement incomplet. Refaire l'étape 5a (erase-flash) avant de reflasher.

---

## RAPPEL : ARCHITECTURE DU CODE (pourquoi c'est structuré comme ça)

Le module radio est **chargé dynamiquement** au boot (pas importé en dur dans `ta_app.py`). Raison : les deux modules (`ta_radio_espnow` et `ta_radio_433`) exposent la **même interface** (`poll_status()`, `get_stats()`, `get_rssi()`, `check_hardware()`). `TaApp` ne sait pas quel module tourne, il appelle juste cette interface. C'est un pattern "duck typing" MicroPython.

Si tu ajoutes un 3ème mode radio un jour : crée `ta_radio_xxx.py` avec les mêmes méthodes, ajoute une constante dans `ta_nvs_config.py`, ajoute un `elif` dans `ta_main.py::load_radio_module()` et une option dans `ta_menu_ui.py`.

L'**asyncio** est utilisé pour gérer en parallèle : le poll radio, la surveillance des boutons, et la mise à jour batterie, sans multithreading réel. `await asyncio.sleep_ms(0)` dans les boucles = cède la main aux autres tâches.
