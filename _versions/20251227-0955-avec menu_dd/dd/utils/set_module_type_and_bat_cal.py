"""
set_module_type_and_bat_cal.py v2.0.0 - Utilitaire de configuration NVS pour DD

Description:
    Utilitaire interactif pour configurer les parametres persistants d'un module DD.
    Configure le type de module (WROOM-32 ou WROVER-T7) et effectue la calibration
    batterie interactive avec mesure ADC en temps reel.

Fonctionnalites:
    1. Configuration du type de module (MODULE_TYPE)
    2. Calibration batterie interactive avec voltmetre
    3. Affichage de la configuration actuelle avec mesures en temps reel
    4. Reinitialisation aux valeurs par defaut
    5. Redemarrage du module
    
Nouveau dans v2.0.0:
    - Calibration batterie interactive avec voltmetre (comme lilygo-t7-v1_5-calibration-batterie.py)
    - Mesure ADC en temps reel pendant la calibration
    - Calcul automatique du facteur de correction
    - Validation et verification de la calibration
    
Utilisation:
    1. Copier ce fichier sur le DD (via REPL ou OTA)
    2. Lancer depuis REPL:
        >>> import set_module_type_and_bat_cal
        >>> # Le menu interactif demarre automatiquement

Menu principal:
    1. Configurer type de module    → Choisir WROOM-32 ou WROVER-T7
    2. Calibrer batterie (interactif) → Calibration avec voltmetre
    3. Afficher configuration        → Voir parametres et mesures actuels
    4. Reinitialiser                 → Remettre valeurs par defaut
    5. Redemarrer                    → Appliquer les changements
    6. Quitter                       → Sortir sans redemarrer

Configuration NVS:
    Namespace: "DTD"
    Cles:
        - DD-type (string)        : "WROOM-32" ou "WROVER-T7"
        - bat_cal_factor (float)  : Facteur de calibration (defaut 1.0)

Auteur: Systeme DTD
Version: 2.0.0
Date: 08/12/2025
"""

import utils.nvs_utils as nvs_utils

def set_module_type():
    """Configure le type de module dans la NVS"""
    
    print("=" * 60)
    print("CONFIGURATION TYPE DE MODULE DD")
    print("=" * 60)
    print()
    
    # Lecture valeur actuelle
    current = nvs_utils.get_str("DTD", "DD-type", default="NON_DEFINI")
    print("Valeur actuelle: {}".format(current))
    print()
    
    # Menu
    print("Types de modules disponibles:")
    print("  1. WROOM-32")
    print("  2. WROVER-T7")
    print()
    
    choice = input("Choisir (1 ou 2): ").strip()
    
    if choice == "1":
        module_type = "WROOM-32"
    elif choice == "2":
        module_type = "WROVER-T7"
    else:
        print("Choix invalide!")
        return
    
    # Confirmation
    print()
    print("Configuration a enregistrer: {}".format(module_type))
    confirm = input("Confirmer (o/n): ").strip().lower()
    
    if confirm != "o" and confirm != "y":
        print("Annule.")
        return
    
    # Enregistrement
    try:
        nvs_utils.set_str("DTD", "DD-type", module_type)
        print()
        print("[OK] Type de module enregistre: {}".format(module_type))
        print()
        print("IMPORTANT: Redemarrer le DD pour appliquer:")
        print("  >>> import machine")
        print("  >>> machine.reset()")
    except Exception as e:
        print("ERREUR lors de l'enregistrement:", e)


def calibrate_battery_interactive():
    """
    Calibration batterie interactive avec voltmetre
    Similaire a lilygo-t7-v1_5-calibration-batterie.py
    """
    print("=" * 60)
    print("CALIBRATION BATTERIE INTERACTIVE")
    print("=" * 60)
    print()
    
    # Verifier type de module
    module_type = nvs_utils.get_str("DTD", "DD-type", default="NON_DEFINI")
    if module_type != "WROVER-T7":
        print("ATTENTION: La calibration batterie concerne uniquement WROVER-T7")
        print("Type de module actuel: {}".format(module_type))
        print()
        confirm = input("Continuer quand meme? (o/n): ").strip().lower()
        if confirm != "o" and confirm != "y":
            return
        print()
    
    # Initialisation ADC
    try:
        from machine import ADC, Pin
        import time
        
        BAT_ADC = ADC(Pin(35))
        try:
            BAT_ADC.atten(ADC.ATTN_11DB)  # Plage 0-3.3V
        except:
            pass
        
        # Lecture facteur actuel
        current_factor = nvs_utils.get_f32("DTD", "bat_cal_factor", default=1.0)
        print("Facteur actuel: {:.6f}".format(current_factor))
        print()
        
    except Exception as e:
        print("ERREUR: Impossible d'initialiser l'ADC:", e)
        return
    
    # Instructions
    print("INSTRUCTIONS:")
    print("1. Branchez un voltmetre entre GPIO35 et la masse (GND)")
    print("2. Relevez la tension affichee sur le voltmetre")
    print("3. Entrez cette valeur ci-dessous")
    print()
    print("Note: Mesurez sur GPIO35 (apres le diviseur de tension)")
    print("      La tension doit etre entre 0 et 3.6V")
    print()
    
    # Lecture ADC actuelle (moyenne sur 50 echantillons)
    print("Lecture ADC en cours...")
    adc_sum = 0
    for _ in range(50):
        adc_sum += BAT_ADC.read()
        time.sleep_ms(10)
    adc_value = adc_sum / 50.0
    
    # Conversion en tension (sans calibration)
    voltage_esp32 = (adc_value / 4095.0) * 3.3
    
    # Tension batterie estimee (avec calibration actuelle)
    voltage_battery_estimated = voltage_esp32 * 2.0 * current_factor
    
    print()
    print("--- MESURES ACTUELLES ---")
    print("Valeur ADC brute: {:.1f}".format(adc_value))
    print("Tension GPIO35 (ESP32): {:.3f} V".format(voltage_esp32))
    print("Tension batterie estimee: {:.3f} V".format(voltage_battery_estimated))
    print()
    
    # Demande de la tension voltmetre
    try:
        voltage_str = input("Tension voltmetre sur GPIO35 (V): ").strip()
        if not voltage_str:
            print("Annule.")
            return
        
        voltage_voltmeter = float(voltage_str)
        
        if voltage_voltmeter <= 0 or voltage_voltmeter > 3.6:
            print("ERREUR: Tension invalide (doit etre entre 0 et 3.6V)")
            return
        
    except ValueError:
        print("ERREUR: Valeur invalide!")
        return
    except KeyboardInterrupt:
        print("\n\nCalibration annulee")
        return
    
    # Calcul du facteur de correction
    if voltage_esp32 > 0:
        new_factor = voltage_voltmeter / voltage_esp32
    else:
        print("ERREUR: Tension GPIO nulle, impossible de calibrer!")
        return
    
    # Verification
    voltage_gpio_calibrated = voltage_esp32 * new_factor
    voltage_battery_new = voltage_gpio_calibrated * 2.0
    error = abs(voltage_gpio_calibrated - voltage_voltmeter)
    error_percent = (error / voltage_voltmeter) * 100
    
    print()
    print("=" * 60)
    print("RESULTATS DE CALIBRATION")
    print("=" * 60)
    print()
    print("Facteur de correction: {:.6f}".format(new_factor))
    print("Tension GPIO35 calibree: {:.3f} V".format(voltage_gpio_calibrated))
    print("Tension batterie recalculee: {:.3f} V".format(voltage_battery_new))
    print("Erreur sur GPIO35: {:.3f} V ({:.2f}%)".format(error, error_percent))
    print()
    
    if error_percent < 1.0:
        print("[OK] Calibration reussie (erreur < 1%)")
    else:
        print("[ATTENTION] Calibration avec erreur > 1%")
    
    print()
    
    # Confirmation sauvegarde
    confirm = input("Sauvegarder ce facteur de calibration? (o/n): ").strip().lower()
    if confirm != "o" and confirm != "y":
        print("Calibration non sauvegardee.")
        return
    
    # Enregistrement
    try:
        nvs_utils.set_f32("DTD", "bat_cal_factor", new_factor)
        print()
        print("[OK] Facteur de calibration enregistre: {:.6f}".format(new_factor))
        print()
        print("IMPORTANT: Redemarrer le DD pour appliquer:")
        print("  >>> import machine")
        print("  >>> machine.reset()")
    except Exception as e:
        print("ERREUR lors de l'enregistrement:", e)


def show_current_config():
    """Affiche la configuration actuelle avec mesures en temps reel"""
    print("=" * 60)
    print("CONFIGURATION ACTUELLE")
    print("=" * 60)
    print()
    
    # Type de module
    module_type = nvs_utils.get_str("DTD", "DD-type", default="NON_DEFINI")
    print("Type de module: {}".format(module_type))
    
    # Calibration batterie
    try:
        bat_cal = nvs_utils.get_f32("DTD", "bat_cal_factor", default=1.0)
        print("Facteur calibration batterie: {:.6f}".format(bat_cal))
    except:
        bat_cal = 1.0
        print("Facteur calibration batterie: 1.000000 (par defaut)")
    
    # Tension batterie si T7
    if module_type == "WROVER-T7":
        try:
            from machine import ADC, Pin
            import time
            
            BAT_ADC = ADC(Pin(35))
            try:
                BAT_ADC.atten(ADC.ATTN_11DB)
            except:
                pass
            
            # Lecture moyenne sur 20 echantillons
            adc_sum = 0
            for _ in range(20):
                adc_sum += BAT_ADC.read()
                time.sleep_ms(10)
            raw = adc_sum / 20.0
            
            voltage_adc = (raw / 4095.0) * 3.3
            voltage_bat = voltage_adc * 2.0 * bat_cal
            
            print()
            print("Tension batterie (mesure actuelle):")
            print("  ADC brut: {:.1f}".format(raw))
            print("  Tension GPIO35: {:.3f} V".format(voltage_adc))
            print("  Tension batterie: {:.3f} V".format(voltage_bat))
            
            # Indicateur de niveau
            print()
            if voltage_bat >= 4.0:
                print("  Etat: [OK] Chargee (>= 4.0V)")
            elif voltage_bat >= 3.7:
                print("  Etat: [OK] Bonne (>= 3.7V)")
            elif voltage_bat >= 3.5:
                print("  Etat: [ATTENTION] Moyenne (3.5-3.7V)")
            else:
                print("  Etat: [FAIBLE] Recharger (< 3.5V)")
                
        except Exception as e:
            print()
            print("Impossible de lire la tension batterie:", e)
    
    print("=" * 60)


def reset_to_defaults():
    """Reinitialise la configuration aux valeurs par defaut"""
    print("=" * 60)
    print("REINITIALISATION CONFIGURATION")
    print("=" * 60)
    print()
    
    print("Cette operation va:")
    print("  - Supprimer le type de module")
    print("  - Reinitialiser la calibration batterie a 1.000")
    print()
    
    confirm = input("Confirmer la reinitialisation (o/n): ").strip().lower()
    if confirm != "o" and confirm != "y":
        print("Annule.")
        return
    
    try:
        nvs_utils.set_str("DTD", "DD-type", "")
        nvs_utils.set_f32("DTD", "bat_cal_factor", 1.0)
        
        print()
        print("[OK] Configuration reinitialisee")
        print()
        print("Redemarrer le DD:")
        print("  >>> import machine")
        print("  >>> machine.reset()")
    except Exception as e:
        print("ERREUR:", e)


# Menu principal
if __name__ == "__main__":
    while True:
        print()
        print("=" * 60)
        print("UTILITAIRE CONFIGURATION DD v2.0.0")
        print("=" * 60)
        print()
        print("1. Configurer type de module")
        print("2. Calibrer batterie (interactif)")
        print("3. Afficher configuration actuelle")
        print("4. Reinitialiser configuration")
        print("5. Redemarrer le DD")
        print("6. Quitter")
        print()
        
        choice = input("Choisir (1-6): ").strip()
        
        if choice == "1":
            set_module_type()
        elif choice == "2":
            calibrate_battery_interactive()
        elif choice == "3":
            show_current_config()
        elif choice == "4":
            reset_to_defaults()
        elif choice == "5":
            print()
            confirm = input("Redemarrer maintenant? (o/n): ").strip().lower()
            if confirm == "o" or confirm == "y":
                import machine
                print("Redemarrage...")
                machine.reset()
            else:
                print("Annule.")
        elif choice == "6":
            print("Au revoir.")
            break
        else:
            print("Choix invalide!")
else:
    # Si importe, executer directement le menu
    pass