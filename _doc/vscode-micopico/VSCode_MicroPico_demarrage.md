# DTD — Mémoire externe : Démarrage VSCode + MicroPico
**Environnement : Linux Mint — HP Spectre**
**Extension : MicroPico (paulober.pico-w-go)**
**Cartes : ESP32-S3 (TA) / WROVER-T7 (DD)**

---

## ÉTAPE 1 — Vérifier que l'ESP32 est reconnu

Brancher l'ESP32 en USB, puis dans un terminal :

```bash
ls /dev/ttyACM*
# Résultat attendu : /dev/ttyACM0 ou /dev/ttyACM1
```

Si rien n'apparaît → essayer un autre câble USB (cause la plus fréquente !) ou un autre port USB.

Pour surveiller la détection en temps réel au branchement :
```bash
dmesg -w
# Brancher l'ESP32 et observer les messages
# Ctrl+C pour quitter
```

---

## ÉTAPE 2 — Droits d'accès au port série

```bash
# Solution permanente (nécessite une reconnexion de session)
sudo usermod -a -G dialout $USER

# Solution immédiate pour la session en cours
sudo chmod 666 /dev/ttyACM0   # adapter le numéro de port
```

---

## ÉTAPE 3 — Ouvrir le projet dans VSCode

Toujours ouvrir VSCode **depuis le dossier du projet** — MicroPico en a besoin pour fonctionner :

```bash
cd ~/projets/dtd/ta        # ou le dossier dd selon ce qu'on travaille
code .
```

---

## ÉTAPE 4 — Configurer MicroPico (si pas déjà fait)

### Initialiser le projet MicroPico (une seule fois par projet)
`Ctrl+Shift+P` → **MicroPico: Initialize MicroPico Project**

Cela crée un dossier `.vscode/` avec `settings.json`.

### Forcer le port manuellement

Vérifier/créer le fichier `.vscode/settings.json` à la racine du projet :

```json
{
    "micropico.manualComDevice": "/dev/ttyACM0",
    "micropico.autoConnect": false
}
```

> Adapter `/dev/ttyACM0` selon le résultat de l'étape 1.

### Choisir les stubs ESP32 (une seule fois)
`Ctrl+Shift+P` → **MicroPico: Switch Stubs** → sélectionner un stub ESP32

---

## ÉTAPE 5 — Se connecter

Dans la **barre de statut en bas** de VSCode, cliquer sur **`< Connect`** (ou sur **"Pico Disconnected"**).

> ⚠️ Si SQLTools capture le bouton "Connect" : passer par `Ctrl+Shift+P` → **MicroPico: Connect**

Connexion réussie = la barre affiche :
```
Pico Connected  ●  /dev/ttyACM0
```

---

## ÉTAPE 6 — Lancer le code

| Action | Comment |
|---|---|
| Lancer le fichier ouvert | `Ctrl+Shift+P` → **MicroPico: Run current file on Pico** |
| Lancer `main.py` | `Ctrl+Shift+P` → **MicroPico: Run current file on Pico** (depuis `main.py` ouvert) |
| Ouvrir le REPL interactif | `Ctrl+Shift+P` → **MicroPico: Toggle REPL** |
| Uploader un fichier sur l'ESP32 | Clic droit sur le fichier → **Upload file to Pico** |
| Uploader tout le projet | `Ctrl+Shift+P` → **MicroPico: Upload project to Pico** |
| Arrêter l'exécution | `Ctrl+C` dans le terminal REPL |

---

## DÉPANNAGE RAPIDE

**"No COM device found"**
→ Vérifier le câble, rebrancher, refaire l'étape 1

**Port change au rebranchemnt (ttyACM0 → ttyACM1)**
→ Mettre à jour `micropico.manualComDevice` dans `.vscode/settings.json`

**MicroPico ne répond plus / figé**
→ `Ctrl+C` dans le REPL pour interrompre, puis déconnecter/reconnecter

**Le bouton "Connect" ouvre SQLTools**
→ Toujours passer par `Ctrl+Shift+P` → **MicroPico: Connect**

---

## RAPPEL STRUCTURE PROJET DTD

```
~/projets/dtd/
├── ta/          → Transmetteur Agrégateur (ESP32-S3)
│   ├── .vscode/settings.json
│   ├── ta_main.py
│   ├── ta_config.py
│   ├── ta_radio_433.py
│   ├── ta_radio_espnow.py
│   └── ...
└── dd/          → Détecteur Distant (WROVER-T7 / ESP32)
    ├── .vscode/settings.json
    ├── boot.py
    ├── dd_main.py
    ├── dd_config.py
    └── ...
```

---

*Généré le 01.06.2026 — à mettre à jour si la structure des dossiers change*
