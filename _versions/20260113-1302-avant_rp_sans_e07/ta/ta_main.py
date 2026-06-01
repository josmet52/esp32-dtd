"""
ta_main.py v3.3.0 - Point d'entree avec selection dynamique radio
Date: 27.12.2025

v3.3.0:
- Titre dynamique selon mode radio (TA-espnow ou TA-433MHz)

v3.2.0:
- Fichier unique ta_radio_espnow (suppression de _normal et _rssi)

v3.1.0:
- Suppression du mode ESP-NOW RSSI
- Simplification: ESP-NOW et Radio 433MHz uniquement
"""

try:
    import uasyncio as asyncio
except Exception:
    import asyncio

import ta_config as config
from ta_app import TaApp
from ta_logger import get_logger
from ta_nvs_config import NVSConfig, RADIO_MODE_ESP_NORMAL, RADIO_MODE_433

logger = get_logger()


def load_radio_module():
    """Charge dynamiquement le module radio selon NVS et ajuste le titre"""
    mode = NVSConfig.get_radio_mode()
    
    logger.info("="*60, "main")
    logger.info("Mode radio: {}".format(NVSConfig.get_mode_name(mode)), "main")
    logger.info("="*60, "main")
    
    # Ajuster le nom de l'application selon le mode
    if mode == RADIO_MODE_ESP_NORMAL:
        config.APP_NAME = "TA-espnow"
    elif mode == RADIO_MODE_433:
        config.APP_NAME = "TA-433MHz"
    else:
        config.APP_NAME = "TA-espnow"  # Defaut
    
    logger.info("Titre affiche: {}".format(config.APP_NAME), "main")
    
    try:
        if mode == RADIO_MODE_ESP_NORMAL:
            logger.info("Chargement: ta_radio_espnow", "main")
            import ta_radio_espnow as radio_module
            
        elif mode == RADIO_MODE_433:
            logger.info("Chargement: ta_radio_433", "main")
            import ta_radio_433 as radio_module
            
        else:
            logger.warning("Mode invalide, fallback ESP-NOW", "main")
            import ta_radio_espnow as radio_module
        
        return radio_module
        
    except ImportError as e:
        logger.error("Erreur import: {}".format(e), "main")
        import ta_radio_espnow as radio_module
        return radio_module


async def _main():
    """Fonction principale"""
    radio_module = load_radio_module()
    
    logger.info("Démarrage DTD v{} du {}".format(
        config.APP_VERSION, config.APP_DATE), "main")
    
    try:
        app = TaApp(radio_module=radio_module)
        await asyncio.create_task(app.run())
            
    except KeyboardInterrupt:
        logger.info("Arrêt utilisateur", "main")
    except Exception as e:
        logger.critical("Erreur: {}".format(e), "main")
        raise
    finally:
        logger.info("Terminé", "main")


def main():
    asyncio.run(_main())
