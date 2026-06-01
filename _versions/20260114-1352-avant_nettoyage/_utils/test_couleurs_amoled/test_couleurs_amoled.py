"""
test_couleurs_amoled.py - Test des couleurs tft_config_amoled
Date: 27.12.2025

Application de test pour verifier les couleurs RGB565 sur T-Display-S3 AMOLED

Affiche:
- 8 blocs de couleurs primaires (BLACK, WHITE, RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA)
- Nom de la couleur
- Valeur hexadecimale RGB565
- Valeurs RGB decimales equivalentes

Utilisation:
1. Uploader ce fichier sur l'ESP32-S3
2. Executer: import test_couleurs_amoled
3. Observer l'ecran
"""

import tft_config_amoled as tft_config
import fonts.vga2_16x16 as font

# Initialiser l'ecran
print("Initialisation ecran AMOLED...")
tft = tft_config.config(rotation=0)  # Portrait
tft.reset()
tft.init()
tft.rotation(0)
tft.brightness(128)

# Effacer ecran en noir
tft.fill(tft_config.BLACK)

print("Test des couleurs...")

# Liste des couleurs a tester
couleurs = [
    ("BLACK",   tft_config.BLACK,   (0, 0, 0)),
    ("WHITE",   tft_config.WHITE,   (255, 255, 255)),
    ("RED",     tft_config.RED,     (255, 0, 0)),
    ("GREEN",   tft_config.GREEN,   (0, 255, 0)),
    ("BLUE",    tft_config.BLUE,    (0, 0, 255)),
    ("YELLOW",  tft_config.YELLOW,  (255, 255, 0)),
    ("CYAN",    tft_config.CYAN,    (0, 255, 255)),
    ("MAGENTA", tft_config.MAGENTA, (255, 0, 255)),
]

# Dimensions
screen_width = 240
screen_height = 536
bloc_height = screen_height // len(couleurs)  # ~67 pixels par couleur

y = 0

for nom, valeur_rgb565, rgb_attendu in couleurs:
    # Dessiner un bloc de couleur
    tft.fill_rect(0, y, screen_width, bloc_height, valeur_rgb565)
    
    # Texte: nom de la couleur (en haut du bloc)
    # Choisir couleur de texte contrastante
    if nom == "BLACK":
        couleur_texte = tft_config.WHITE
    elif nom in ["YELLOW", "CYAN", "WHITE"]:
        couleur_texte = tft_config.BLACK
    else:
        couleur_texte = tft_config.WHITE
    
    # Afficher nom
    text_y = y + 5
    tft.text(font, nom, 10, text_y, couleur_texte, valeur_rgb565)
    
    # Afficher valeur hexa
    hexa = "0x{:04X}".format(valeur_rgb565)
    text_y += 20
    tft.text(font, hexa, 10, text_y, couleur_texte, valeur_rgb565)
    
    # Afficher RGB attendu
    rgb_text = "RGB:{},{},{}".format(*rgb_attendu)
    text_y += 20
    tft.text(font, rgb_text, 10, text_y, couleur_texte, valeur_rgb565)
    
    # Log console
    print("{:8s} = {} = RGB{}".format(nom, hexa, rgb_attendu))
    
    # Passer au bloc suivant
    y += bloc_height

print("")
print("Test termine!")
print("Ecran affiche 8 bandes de couleurs avec:")
print("- Nom de la couleur")
print("- Valeur hexadecimale RGB565")
print("- Valeurs RGB attendues")
print("")
print("Verifiez visuellement que les couleurs correspondent.")
