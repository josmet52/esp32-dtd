"""
ta_main.py v3.0.0 - Point d'entrée avec sélection dynamique radio
"""

try:
    import uasyncio as asyncio
except Exception:
    import asyncio

import ta_config as config
from ta_app import TaApp
from ta_logger import get_logger
from ta_nvs_config import NVSConfig, RADIO_MODE_ESP_NORMAL, RADIO_MODE_ESP_RSSI, RADIO_MODE_433

logger = get_logger()


def load_radio_module():
    """Charge dynamiquement le module radio selon NVS"""
    mode = NVSConfig.get_radio_mode()
    
    logger.info("="*60, "main")
    logger.info("Mode radio: {}".format(NVSConfig.get_mode_name(mode)), "main")
    logger.info("="*60, "main")
    
    try:
        if mode == RADIO_MODE_ESP_NORMAL:
            logger.info("Chargement: ta_radio_espnow_sans_wifi", "main")
            import ta_radio_espnow_sans_wifi as radio_module
            
        elif mode == RADIO_MODE_ESP_RSSI:
            logger.info("Chargement: ta_radio_espnow_avec_wifi", "main")
            import ta_radio_espnow_avec_wifi as radio_module
            
        elif mode == RADIO_MODE_433:
            logger.info("Chargement: ta_radio_433", "main")
            import ta_radio_433 as radio_module
            
        else:
            logger.warning("Mode invalide, fallback ESP-NOW Normal", "main")
            import ta_radio_espnow_sans_wifi as radio_module
        
        return radio_module
        
    except ImportError as e:
        logger.error("Erreur import: {}".format(e), "main")
        import ta_radio_espnow_sans_wifi as radio_module
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