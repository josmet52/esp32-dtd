"""
================================================================================
ta_main.py - Point d'entrée du mode normal
================================================================================

Description:
-----------
Point d'entrée de l'application en mode normal (non-OTA).
Initialise le logger, crée l'instance de TaApp et lance la boucle principale
asynchrone.

Architecture:
------------
boot.py
    ↓
ta_main.py (ce fichier) ← Point d'entrée mode NORMAL
    ↓
TaApp (ta_app.py) ← Application principale
    ├─ UIPortrait (ta_ui_portrait.py) ← Interface graphique
    ├─ ButtonManager (ta_buttons.py) ← Gestion boutons
    └─ Radio433 (ta_radio_433.py) ← Communication radio 433MHz

Fonctionnement:
--------------
1. Initialisation du logger global
2. Affichage des informations de démarrage
3. Création de l'instance TaApp
4. Lancement de la boucle principale asynchrone
5. Gestion propre des erreurs et interruptions

Usage du asyncio:
----------------
Le système utilise uasyncio (MicroPython) ou asyncio (Python) pour:
- Exécuter plusieurs tâches concurrentes (UI, boutons, radio)
- Gérer les timeouts de communication radio
- Maintenir la fluidité de l'interface utilisateur

Gestion des erreurs:
-------------------
- KeyboardInterrupt: Arrêt propre par l'utilisateur
- Exception générale: Log de l'erreur et arrêt
- Finally: Nettoyage des ressources

Project: DTD (Détecteur de Détection)
Component: TA (Terminal Aggregator)
Author: jom52
Email: jom52.dev@gmail.com
GitHub: https://github.com/JOM52/dtd

Version History:
---------------
v1.0.0 : 22.10.2025 --> Premier prototype
v2.0.0 : 24.10.2025 --> Amélioration gestion erreurs
================================================================================
"""

# Import du module asyncio (uasyncio pour MicroPython, asyncio pour Python)
try:
    import uasyncio as asyncio
except Exception:
    import asyncio

# Import des modules du projet
import ta_config as config
from ta_app import TaApp
from ta_logger import get_logger
from ta_logger import Logger

# Récupération de l'instance globale du logger
logger = get_logger()

# Note: La validation de configuration est désactivée pour l'instant
# logger.info("Validation de la configuration...", "main")
# config.ConfigValidator.validate_or_exit()


async def _main():
    """
    Fonction principale asynchrone.
    
    Fonctionnement:
    --------------
    1. Affiche bannière de démarrage avec version et date
    2. Crée l'instance TaApp (qui initialise UI, radio, boutons)
    3. Lance la tâche principale app.run() en mode async
    4. Gère les exceptions et assure un arrêt propre
    
    La tâche app.run() est une boucle infinie qui:
    - Interroge les détecteurs radio en séquence
    - Met à jour l'affichage
    - Surveille les boutons
    - Gère le watchdog si activé
    
    Raises:
    ------
    KeyboardInterrupt: Si l'utilisateur demande l'arrêt (Ctrl+C)
    Exception: Pour toute erreur fatale non gérée
    """
    # === Bannière de démarrage ===
    logger.info("="*60, "main")
    logger.info("Démarrage DTD v{} du {}".format(
        config.MAIN["VERSION_NO"], 
        config.MAIN["VERSION_DATE"]), "main")
    logger.info("Mode debug: {}".format(config.MAIN.get("DEBUG_MODE", False)), "main")
    logger.info("="*60, "main")
    
    try:
        # === Création de l'application ===
        # TaApp initialise:
        # - L'interface utilisateur (UIPortrait)
        # - Le gestionnaire de boutons (ButtonManager)
        # - Le module radio (Radio433)
        # - Le watchdog si activé
        app = TaApp()
        
        # === Lancement de la boucle principale ===
        # create_task() lance la coroutine en arrière-plan
        # await bloque jusqu'à ce que la tâche se termine (jamais en fonctionnement normal)
        app_task = asyncio.create_task(app.run())
        await app_task
            
    except KeyboardInterrupt:
        # Arrêt propre demandé par l'utilisateur
        logger.info("Arrêt demandé par l'utilisateur", "main")
        
    except Exception as e:
        # Erreur critique non gérée
        logger.critical("Erreur fatale: {}".format(e), "main")
        raise  # Re-lever l'exception pour déboguer
        
    finally:
        # Nettoyage final (toujours exécuté)
        logger.info("Application terminée", "main")


def main():
    """
    Wrapper synchrone pour lancer la boucle asynchrone.
    
    Cette fonction est appelée par boot.py au démarrage.
    Elle lance le event loop asyncio qui exécutera _main().
    
    Note:
    ----
    asyncio.run() crée un nouveau event loop, exécute _main(),
    puis ferme proprement le loop à la fin.
    """
    asyncio.run(_main())
