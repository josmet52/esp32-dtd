"""
comparateur_couleurs.py - Compare visuellement tft_config vs amoled
Date: 27.12.2025

Affiche les couleurs cote a cote pour comparer:
- Gauche: Valeurs tft_config (RGB565 manuelles)
- Droite: Valeurs amoled natif (si disponible)

Utilisation:
1. Uploader sur ESP32-S3
2. Executer: import comparateur_couleurs
"""

import tft_config_amoled as tft_config
import fonts.vga2_16x16 as font

# Initialiser ecran
print("Initialisation ecran...")
tft = tft_config.config(rotation=0)
tft.reset()
tft.init()
tft.rotation(0)
tft.brightness(128)

# Effacer
tft.fill(tft_config.BLACK)

print("Comparaison des couleurs...")
print("")

# Essayer d'importer amoled pour comparaison
try:
    import amoled
    amoled_disponible = True
    print("Module amoled natif disponible")
except ImportError:
    amoled_disponible = False
    print("Module amoled natif NON disponible")

# Liste des couleurs
couleurs = [
    "BLACK",
    "WHITE", 
    "RED",
    "GREEN",
    "BLUE",
    "YELLOW",
    "CYAN",
    "MAGENTA",
]

# Dimensions
largeur_ecran = 240
hauteur_ecran = 536
largeur_moitie = largeur_ecran // 2  # 120 pixels
hauteur_bloc = hauteur_ecran // len(couleurs)  # ~67 pixels

y = 0

print("")
print("Couleur       | tft_config | amoled     | Match")
print("-" * 55)

for nom_couleur in couleurs:
    # Recuperer valeurs
    val_tft = getattr(tft_config, nom_couleur)
    
    if amoled_disponible:
        val_amoled = getattr(amoled, nom_couleur)
    else:
        val_amoled = val_tft  # Meme valeur si amoled pas dispo
    
    # Verifier si identiques
    match = (val_tft == val_amoled)
    match_str = "OK" if match else "DIFF"
    
    # Afficher dans console
    print("{:12s}  | 0x{:04X}     | 0x{:04X}     | {}".format(
        nom_couleur, val_tft, val_amoled, match_str))
    
    # Afficher a l'ecran
    # Gauche: tft_config
    tft.fill_rect(0, y, largeur_moitie, hauteur_bloc, val_tft)
    
    # Droite: amoled (ou meme couleur si pas dispo)
    tft.fill_rect(largeur_moitie, y, largeur_moitie, hauteur_bloc, val_amoled)
    
    # Ligne de separation verticale blanche au milieu
    tft.vline(largeur_moitie - 1, y, hauteur_bloc, tft_config.WHITE)
    
    # Texte: nom de la couleur (sur la partie gauche)
    # Choisir couleur texte contrastante
    if nom_couleur in ["BLACK"]:
        couleur_texte = tft_config.WHITE
    elif nom_couleur in ["YELLOW", "CYAN", "WHITE"]:
        couleur_texte = tft_config.BLACK
    else:
        couleur_texte = tft_config.WHITE
    
    # Nom sur partie gauche
    text_x = 5
    text_y = y + 10
    tft.text(font, nom_couleur[:7], text_x, text_y, couleur_texte, val_tft)
    
    # Indicateur difference si necessaire
    if not match and amoled_disponible:
        # Afficher "!" en rouge sur la droite
        tft.text(font, "!", largeur_moitie + 5, text_y, tft_config.RED, val_amoled)
    
    # Valeurs hexa
    text_y += 20
    hexa_tft = "T:{:04X}".format(val_tft)
    tft.text(font, hexa_tft[:6], text_x, text_y, couleur_texte, val_tft)
    
    if amoled_disponible:
        hexa_amoled = "A:{:04X}".format(val_amoled)
        tft.text(font, hexa_amoled[:6], largeur_moitie + 5, text_y, couleur_texte, val_amoled)
    
    y += hauteur_bloc

print("-" * 55)
print("")

if amoled_disponible:
    print("Ecran divise verticalement:")
    print("  GAUCHE = tft_config (valeurs manuelles RGB565)")
    print("  DROITE = amoled natif")
    print("")
    print("Si couleurs differentes, un '!' rouge apparait a droite")
else:
    print("Ecran affiche uniquement les valeurs tft_config")
    print("Module amoled natif non disponible pour comparaison")

print("")
print("Legende:")
print("  T:xxxx = Valeur tft_config")
print("  A:xxxx = Valeur amoled natif")
print("")
print("Test termine!")
