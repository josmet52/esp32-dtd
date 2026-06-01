"""
test_couleurs_interactif.py - Test interactif des couleurs
Date: 27.12.2025

Application interactive pour tester n'importe quelle couleur RGB565

Fonctions disponibles:
- afficher_couleur(r, g, b) : Affiche une couleur RGB (0-255)
- afficher_rgb565(valeur) : Affiche une couleur RGB565 directe
- comparer_couleurs() : Compare les couleurs tft_config avec module amoled
- grille_couleurs() : Affiche une grille de degrade
"""

import tft_config_amoled as tft_config

# Initialiser l'ecran
print("Initialisation ecran AMOLED...")
tft = tft_config.config(rotation=0)  # Portrait
tft.reset()
tft.init()
tft.rotation(0)
tft.brightness(128)

print("Ecran pret!")
print("")


def afficher_couleur(r, g, b):
    """
    Affiche une couleur RGB sur tout l'ecran
    
    Args:
        r: Rouge (0-255)
        g: Vert (0-255)
        b: Bleu (0-255)
    
    Exemple:
        >>> afficher_couleur(255, 0, 0)  # Rouge pur
        >>> afficher_couleur(128, 128, 255)  # Bleu clair
    """
    # Convertir RGB en RGB565
    couleur = tft_config.color565(r, g, b)
    
    # Afficher
    tft.fill(couleur)
    
    print("RGB({}, {}, {}) = 0x{:04X}".format(r, g, b, couleur))
    print("Affiche sur l'ecran!")


def afficher_rgb565(valeur):
    """
    Affiche une valeur RGB565 directe
    
    Args:
        valeur: Valeur RGB565 (0x0000 - 0xFFFF)
    
    Exemple:
        >>> afficher_rgb565(0xF800)  # Rouge
        >>> afficher_rgb565(0x07E0)  # Vert
    """
    tft.fill(valeur)
    
    # Decoder RGB565 en RGB
    r = (valeur >> 11) << 3
    g = ((valeur >> 5) & 0x3F) << 2
    b = (valeur & 0x1F) << 3
    
    print("RGB565: 0x{:04X}".format(valeur))
    print("RGB approximatif: ({}, {}, {})".format(r, g, b))


def comparer_couleurs():
    """
    Compare les couleurs definies dans tft_config avec le module amoled natif
    Affiche les differences s'il y en a
    """
    print("Comparaison tft_config vs module amoled:")
    print("-" * 50)
    
    try:
        import amoled
        
        couleurs = {
            "BLACK": (tft_config.BLACK, amoled.BLACK),
            "WHITE": (tft_config.WHITE, amoled.WHITE),
            "RED": (tft_config.RED, amoled.RED),
            "GREEN": (tft_config.GREEN, amoled.GREEN),
            "BLUE": (tft_config.BLUE, amoled.BLUE),
            "YELLOW": (tft_config.YELLOW, amoled.YELLOW),
            "CYAN": (tft_config.CYAN, amoled.CYAN),
            "MAGENTA": (tft_config.MAGENTA, amoled.MAGENTA),
        }
        
        differences = False
        
        for nom, (val_tft, val_amoled) in couleurs.items():
            match = "OK" if val_tft == val_amoled else "DIFF"
            print("{:8s}: tft=0x{:04X} | amoled=0x{:04X} [{}]".format(
                nom, val_tft, val_amoled, match))
            
            if val_tft != val_amoled:
                differences = True
        
        print("-" * 50)
        if differences:
            print("ATTENTION: Des differences detectees!")
        else:
            print("Toutes les couleurs correspondent.")
        
    except ImportError:
        print("Module amoled non disponible pour comparaison")


def grille_couleurs():
    """
    Affiche une grille de degrade de couleurs
    Utile pour tester le rendu global
    """
    import fonts.vga2_16x16 as font_small
    
    print("Affichage grille de couleurs...")
    
    # Dimensions
    w = 240
    h = 536
    
    # Degrade horizontal (Rouge → Vert → Bleu)
    for y in range(h):
        # Calculer couleur selon position Y
        if y < h // 3:
            # Zone rouge → jaune
            r = 255
            g = int((y / (h // 3)) * 255)
            b = 0
        elif y < 2 * h // 3:
            # Zone jaune → vert
            r = int(255 - ((y - h // 3) / (h // 3)) * 255)
            g = 255
            b = 0
        else:
            # Zone vert → cyan → bleu
            r = 0
            g = int(255 - ((y - 2 * h // 3) / (h // 3)) * 255)
            b = int(((y - 2 * h // 3) / (h // 3)) * 255)
        
        couleur = tft_config.color565(r, g, b)
        tft.hline(0, y, w, couleur)
    
    # Ajouter texte
    tft.text(font_small, "DEGRADE", 80, 10, tft_config.WHITE, tft_config.BLACK)
    
    print("Grille affichee!")


def test_primaires():
    """
    Teste les 3 couleurs primaires + blanc/noir en plein ecran
    Change toutes les 2 secondes
    """
    import time
    
    couleurs_test = [
        ("NOIR", tft_config.BLACK),
        ("ROUGE", tft_config.RED),
        ("VERT", tft_config.GREEN),
        ("BLEU", tft_config.BLUE),
        ("JAUNE", tft_config.YELLOW),
        ("CYAN", tft_config.CYAN),
        ("MAGENTA", tft_config.MAGENTA),
        ("BLANC", tft_config.WHITE),
    ]
    
    print("Test des couleurs primaires...")
    print("Chaque couleur affichee pendant 2 secondes")
    print("")
    
    for nom, couleur in couleurs_test:
        print("Affichage: {}".format(nom))
        tft.fill(couleur)
        time.sleep(2)
    
    print("Test termine!")


# Menu d'aide
def aide():
    """Affiche l'aide"""
    print("")
    print("=" * 60)
    print("TEST COULEURS AMOLED - Fonctions disponibles:")
    print("=" * 60)
    print("")
    print("afficher_couleur(r, g, b)")
    print("  Affiche une couleur RGB (0-255)")
    print("  Exemple: afficher_couleur(255, 0, 0)")
    print("")
    print("afficher_rgb565(valeur)")
    print("  Affiche une valeur RGB565 directe (0x0000-0xFFFF)")
    print("  Exemple: afficher_rgb565(0xF800)")
    print("")
    print("comparer_couleurs()")
    print("  Compare tft_config avec module amoled natif")
    print("")
    print("grille_couleurs()")
    print("  Affiche un degrade de couleurs")
    print("")
    print("test_primaires()")
    print("  Teste les couleurs primaires (change auto)")
    print("")
    print("aide()")
    print("  Affiche cette aide")
    print("")
    print("=" * 60)


# Afficher aide au demarrage
aide()

# Comparer automatiquement au demarrage
print("")
comparer_couleurs()
print("")
print("Entrez une commande (ex: test_primaires())")
