# Guide - Test des couleurs AMOLED

## Objectif

Verifier que les valeurs RGB565 definies dans `tft_config_amoled.py` correspondent bien aux couleurs affichees sur l'ecran T-Display-S3 AMOLED.

---

## Outils fournis

### 1. test_couleurs_amoled.py

**Description:** Affiche les 8 couleurs primaires en bandes horizontales avec leurs valeurs.

**Utilisation:**
```python
# Dans Thonny ou REPL
import test_couleurs_amoled
```

**Affichage:**
```
┌────────────────────────────┐
│ BLACK     0x0000  0,0,0    │ ← Noir
├────────────────────────────┤
│ WHITE     0xFFFF  255,255,255│ ← Blanc
├────────────────────────────┤
│ RED       0xF800  255,0,0  │ ← Rouge
├────────────────────────────┤
│ GREEN     0x07E0  0,255,0  │ ← Vert
├────────────────────────────┤
│ BLUE      0x001F  0,0,255  │ ← Bleu
├────────────────────────────┤
│ YELLOW    0xFFE0  255,255,0│ ← Jaune
├────────────────────────────┤
│ CYAN      0x07FF  0,255,255│ ← Cyan
├────────────────────────────┤
│ MAGENTA   0xF81F  255,0,255│ ← Magenta
└────────────────────────────┘
```

**Verifier:**
- Les couleurs sont correctes visuellement
- Le texte est lisible (contraste suffisant)

---

### 2. test_couleurs_interactif.py

**Description:** Interface interactive pour tester des couleurs personnalisees.

**Utilisation:**
```python
# Dans Thonny ou REPL
import test_couleurs_interactif
```

**Fonctions disponibles:**

#### afficher_couleur(r, g, b)
Affiche une couleur RGB sur tout l'ecran.

```python
>>> afficher_couleur(255, 0, 0)      # Rouge pur
>>> afficher_couleur(0, 255, 0)      # Vert pur
>>> afficher_couleur(0, 0, 255)      # Bleu pur
>>> afficher_couleur(128, 128, 128)  # Gris moyen
>>> afficher_couleur(255, 128, 0)    # Orange
```

#### afficher_rgb565(valeur)
Affiche une valeur RGB565 hexadecimale directe.

```python
>>> afficher_rgb565(0xF800)  # Rouge
>>> afficher_rgb565(0x07E0)  # Vert
>>> afficher_rgb565(0x001F)  # Bleu
>>> afficher_rgb565(0xFFE0)  # Jaune
```

#### comparer_couleurs()
Compare les valeurs `tft_config` avec le module `amoled` natif.

```python
>>> comparer_couleurs()

Comparaison tft_config vs module amoled:
--------------------------------------------------
BLACK   : tft=0x0000 | amoled=0x0000 [OK]
WHITE   : tft=0xFFFF | amoled=0xFFFF [OK]
RED     : tft=0xF800 | amoled=0xF800 [OK]
...
--------------------------------------------------
```

**Si differences detectees:**
- Note les couleurs qui different
- Verifie les valeurs RGB565 dans `tft_config_amoled.py`

#### grille_couleurs()
Affiche un degrade de couleurs (rouge → jaune → vert → cyan → bleu).

```python
>>> grille_couleurs()
```

Utile pour:
- Verifier le rendu des degrades
- Tester la qualite de l'ecran
- Detecter des problemes de banding

#### test_primaires()
Affiche les couleurs primaires en plein ecran, changement automatique toutes les 2 secondes.

```python
>>> test_primaires()
Test des couleurs primaires...
Affichage: NOIR
Affichage: ROUGE
Affichage: VERT
...
```

Utile pour:
- Verifier rapidement toutes les couleurs
- Detecter des problemes d'affichage
- Test visuel rapide

---

### 3. comparateur_couleurs.py

**Description:** Compare visuellement les valeurs `tft_config` (gauche) avec le module `amoled` natif (droite).

**Utilisation:**
```python
import comparateur_couleurs
```

**Affichage ecran:**
```
┌──────────┬──────────┐
│ tft_conf │  amoled  │
├──────────┼──────────┤
│  BLACK   │  BLACK   │ ← Meme couleur
├──────────┼──────────┤
│  RED     │  RED !   │ ← Difference (! rouge)
├──────────┼──────────┤
│  ...     │  ...     │
└──────────┴──────────┘
```

**Ligne verticale blanche** au milieu separe les deux cotes.

**Indicateur de difference:**
- Si couleurs identiques: pas de marqueur
- Si couleurs differentes: **"!"** rouge sur la droite

**Console:**
```
Couleur       | tft_config | amoled     | Match
-------------------------------------------------------
BLACK         | 0x0000     | 0x0000     | OK
WHITE         | 0xFFFF     | 0xFFFF     | OK
RED           | 0xF800     | 0xF800     | OK
GREEN         | 0x07E0     | 0x07E0     | OK
...
```

---

## Procedure de test recommandee

### Etape 1: Test basique

```python
import test_couleurs_amoled
```

**Verifier visuellement:**
- [ ] NOIR = Noir profond (pas gris)
- [ ] BLANC = Blanc pur (pas gris clair)
- [ ] ROUGE = Rouge pur (pas orange/rose)
- [ ] VERT = Vert pur (pas jaune/cyan)
- [ ] BLEU = Bleu pur (pas cyan/violet)
- [ ] JAUNE = Jaune pur (pas orange/vert)
- [ ] CYAN = Cyan pur (pas vert/bleu)
- [ ] MAGENTA = Magenta pur (pas rose/violet)

### Etape 2: Comparaison avec module natif

```python
import comparateur_couleurs
```

**Observer:**
- Gauche vs Droite: couleurs identiques ?
- Presence de "!" rouge = difference detectee
- Console: liste des differences

**Si differences:**
1. Noter les couleurs differentes
2. Noter les valeurs hexadecimales
3. Passer a l'etape 3

### Etape 3: Test interactif (si differences)

```python
import test_couleurs_interactif

# Comparer valeurs
comparer_couleurs()

# Tester une couleur specifique
# Exemple si RED est different:
afficher_rgb565(0xF800)  # Valeur tft_config
# Observer la couleur

# Importer amoled et tester sa valeur
import amoled
afficher_rgb565(amoled.RED)
# Observer la difference
```

---

## Correction des valeurs (si necessaire)

Si des differences sont detectees entre `tft_config` et `amoled`:

### Methode 1: Copier les valeurs amoled

**Dans `tft_config_amoled.py`:**

```python
# AVANT (valeurs manuelles)
RED = 0xF800

# APRES (copier depuis amoled)
import amoled
RED = amoled.RED  # Utiliser valeur native
```

### Methode 2: Corriger manuellement

Si vous connaissez les bonnes valeurs RGB565:

```python
# Calculer RGB565 manuellement
# Formule: (R & 0xF8) << 8 | (G & 0xFC) << 3 | (B >> 3)

# Exemple pour un rouge leger (255, 64, 64):
R = 255  # 0xFF → 0xF8 (5 bits)
G = 64   # 0x40 → 0x40 (6 bits)
B = 64   # 0x40 → 0x08 (5 bits)

RED_CLAIR = (R & 0xF8) << 8 | (G & 0xFC) << 3 | (B >> 3)
# = 0xF808
```

### Methode 3: Utiliser color565()

```python
# Dans tft_config_amoled.py
RED = color565(255, 0, 0)      # Rouge pur
ORANGE = color565(255, 128, 0) # Orange
```

---

## Valeurs RGB565 de reference

### Couleurs pures

| Couleur | RGB (8-bit) | RGB565 (hex) | Calcul |
|---------|-------------|--------------|--------|
| NOIR    | 0, 0, 0     | 0x0000 | Tout a zero |
| BLANC   | 255, 255, 255 | 0xFFFF | Tout a un |
| ROUGE   | 255, 0, 0   | 0xF800 | R=31, G=0, B=0 |
| VERT    | 0, 255, 0   | 0x07E0 | R=0, G=63, B=0 |
| BLEU    | 0, 0, 255   | 0x001F | R=0, G=0, B=31 |
| JAUNE   | 255, 255, 0 | 0xFFE0 | R=31, G=63, B=0 |
| CYAN    | 0, 255, 255 | 0x07FF | R=0, G=63, B=31 |
| MAGENTA | 255, 0, 255 | 0xF81F | R=31, G=0, B=31 |

### Formule de conversion RGB → RGB565

```
RGB565 = (R >> 3) << 11 | (G >> 2) << 5 | (B >> 3)

Ou:
RGB565 = (R & 0xF8) << 8 | (G & 0xFC) << 3 | (B >> 3)

Details:
- R: 8 bits → 5 bits (diviser par 8)
- G: 8 bits → 6 bits (diviser par 4)
- B: 8 bits → 5 bits (diviser par 8)
```

---

## Troubleshooting

### Probleme: Couleurs ternes ou incorrectes

**Causes possibles:**
1. Luminosite trop basse
2. Valeurs RGB565 incorrectes
3. Probleme materiel ecran

**Solutions:**
```python
import tft_config_amoled as tft_config

# 1. Augmenter luminosite
tft = tft_config.config()
tft.reset()
tft.init()
tft.brightness(255)  # Max luminosite

# 2. Verifier les valeurs
import test_couleurs_interactif
comparer_couleurs()

# 3. Tester avec module natif
import amoled
# Comparer avec affichage natif
```

### Probleme: Ecran reste noir

**Verifier:**
```python
# GPIO38 active ?
from machine import Pin
gpio38 = Pin(38, Pin.OUT)
gpio38.value(1)  # Doit etre a 1

# Reinitialiser
import tft_config_amoled as tft_config
tft = tft_config.config()
tft.reset()
tft.init()
tft.brightness(128)
tft.fill(0xFFFF)  # Blanc
```

### Probleme: Import error

**Si erreur `fonts not found`:**
```python
# Verifier presence dossier fonts/
import os
os.listdir('fonts')

# Si manquant, utiliser version simplifiee:
# Modifier les scripts pour ne pas importer fonts
```

---

## Resultats attendus

### Test nominal (valeurs correctes)

**test_couleurs_amoled.py:**
- 8 bandes de couleurs vives
- Texte lisible
- Couleurs correspondent aux noms

**comparateur_couleurs.py:**
- Gauche = Droite (aucune difference)
- Pas de "!" rouge
- Console: tous "OK"

**test_couleurs_interactif.py:**
```
comparer_couleurs()
→ Toutes les couleurs correspondent.
```

### Si problemes detectes

**Couleurs differentes:**
1. Noter les couleurs en erreur
2. Utiliser `comparateur_couleurs.py` pour visualiser
3. Corriger `tft_config_amoled.py` avec bonnes valeurs

**Console logs:**
```
RED     : tft=0xF800 | amoled=0xF810 [DIFF]
                                      ^^^^
```
→ Corriger RED dans `tft_config_amoled.py`

---

## Conclusion

Apres tests:
1. Si toutes couleurs OK → Garder valeurs actuelles
2. Si differences mineures → Evaluer impact visuel
3. Si differences majeures → Corriger avec valeurs natives amoled

**Recommandation:**
En cas de doute, utiliser directement les valeurs du module `amoled` natif pour garantir la compatibilite.

---

**Date:** 27.12.2025  
**Version:** 1.0  
**Compatible:** T-Display-S3 AMOLED + MicroPython
