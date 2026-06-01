"""
set_module_type.py - Utilitaire de configuration NVS pour DD
Configure le type de module (WROOM-32 ou WROVER-T7) et calibration batterie

Usage:
1. Copier ce fichier sur le DD
2. Lancer via REPL: import set_module_type
3. Ou exécuter: execfile('set_module_type.py')
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
    print("Configuration à enregistrer: {}".format(module_type))
    confirm = input("Confirmer (o/n): ").strip().lower()
    
    if confirm != "o" and confirm != "y":
        print("Annulé.")
        return
    
    # Enregistrement
    try:
        nvs_utils.set_str("DTD", "DD-type", module_type)
        print()
        print("✓ Type de module enregistré: {}".format(module_type))
        print()
        print("IMPORTANT: Redémarrer le DD pour appliquer:")
        print("  >>> import machine")
        print("  >>> machine.reset()")
    except Exception as e:
        print("ERREUR lors de l'enregistrement:", e)

def set_battery_calibration():
    """Configure le facteur de calibration batterie"""
    
    print("=" * 60)
    print("CALIBRATION BATTERIE (T7 uniquement)")
    print("=" * 60)
    print()
    
    # Vérifier type de module
    module_type = nvs_utils.get_str("DTD", "DD-type", default="NON_DEFINI")
    if module_type != "WROVER-T7":
        print("ATTENTION: La calibration batterie concerne uniquement WROVER-T7")
        print("Type de module actuel: {}".format(module_type))
        print()
        confirm = input("Continuer quand même? (o/n): ").strip().lower()
        if confirm != "o" and confirm != "y":
            return
        print()
    
    # Lecture valeur actuelle
    try:
        current = nvs_utils.get_f32("DTD", "bat_cal_factor", default=1.0)
        print("Facteur actuel: {:.3f}".format(current))
    except:
        current = 1.0
        print("Facteur actuel: 1.000 (par défaut)")
    
    print()
    print("Information:")
    print("  - Facteur par défaut: 1.000")
    print("  - Plage valide: 0.500 à 2.000")
    print("  - Exemple: Si tension mesurée = 3.6V mais réelle = 3.7V")
    print("            alors facteur = 3.7 / 3.6 = 1.028")
    print()
    
    # Saisie nouvelle valeur
    try:
        value_str = input("Nouveau facteur (ou vide pour annuler): ").strip()
        if not value_str:
            print("Annulé.")
            return
        
        new_factor = float(value_str)
        
        if new_factor < 0.5 or new_factor > 2.0:
            print("ERREUR: Facteur hors limites (0.5 - 2.0)")
            return
        
    except ValueError:
        print("ERREUR: Valeur invalide!")
        return
    
    # Confirmation
    print()
    print("Facteur à enregistrer: {:.3f}".format(new_factor))
    confirm = input("Confirmer (o/n): ").strip().lower()
    
    if confirm != "o" and confirm != "y":
        print("Annulé.")
        return
    
    # Enregistrement
    try:
        nvs_utils.set_f32("DTD", "bat_cal_factor", new_factor)
        print()
        print("✓ Facteur de calibration enregistré: {:.3f}".format(new_factor))
        print()
        print("IMPORTANT: Redémarrer le DD pour appliquer:")
        print("  >>> import machine")
        print("  >>> machine.reset()")
    except Exception as e:
        print("ERREUR lors de l'enregistrement:", e)

def show_current_config():
    """Affiche la configuration actuelle"""
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
        print("Facteur calibration batterie: {:.3f}".format(bat_cal))
    except:
        print("Facteur calibration batterie: 1.000 (par défaut)")
    
    # Tension batterie si T7
    if module_type == "WROVER-T7":
        try:
            from machine import ADC, Pin
            BAT_ADC = ADC(Pin(35))
            try:
                BAT_ADC.atten(ADC.ATTN_11DB)
            except:
                pass
            
            raw = BAT_ADC.read()
            voltage_adc = (raw / 4095.0) * 3.3
            bat_cal = nvs_utils.get_f32("DTD", "bat_cal_factor", default=1.0)
            voltage_bat = voltage_adc * 2.0 * bat_cal
            
            print()
            print("Tension batterie (mesure actuelle):")
            print("  ADC brut: {}".format(raw))
            print("  Tension ADC: {:.3f}V".format(voltage_adc))
            print("  Tension batterie: {:.3f}V".format(voltage_bat))
        except Exception as e:
            print()
            print("Impossible de lire la tension batterie:", e)
    
    print("=" * 60)

def reset_to_defaults():
    """Réinitialise la configuration aux valeurs par défaut"""
    print("=" * 60)
    print("RÉINITIALISATION CONFIGURATION")
    print("=" * 60)
    print()
    
    print("Cette opération va:")
    print("  - Supprimer le type de module")
    print("  - Réinitialiser la calibration batterie à 1.000")
    print()
    
    confirm = input("Confirmer la réinitialisation (o/n): ").strip().lower()
    if confirm != "o" and confirm != "y":
        print("Annulé.")
        return
    
    try:
        # Note: nvs_utils n'a pas forcément de fonction delete
        # On va simplement remettre les valeurs par défaut
        nvs_utils.set_str("DTD", "DD-type", "")
        nvs_utils.set_f32("DTD", "bat_cal_factor", 1.0)
        
        print()
        print("✓ Configuration réinitialisée")
        print()
        print("Redémarrer le DD:")
        print("  >>> import machine")
        print("  >>> machine.reset()")
    except Exception as e:
        print("ERREUR:", e)

# Menu principal
if __name__ == "__main__":
    while True:
        print()
        print("=" * 60)
        print("UTILITAIRE CONFIGURATION DD")
        print("=" * 60)
        print()
        print("1. Configurer type de module")
        print("2. Configurer calibration batterie")
        print("3. Afficher configuration actuelle")
        print("4. Réinitialiser configuration")
        print("5. Redémarrer le DD")
        print("6. Quitter")
        print()
        
        choice = input("Choisir (1-6): ").strip()
        
        if choice == "1":
            set_module_type()
        elif choice == "2":
            set_battery_calibration()
        elif choice == "3":
            show_current_config()
        elif choice == "4":
            reset_to_defaults()
        elif choice == "5":
            print()
            confirm = input("Redémarrer maintenant? (o/n): ").strip().lower()
            if confirm == "o" or confirm == "y":
                import machine
                print("Redémarrage...")
                machine.reset()
            else:
                print("Annulé.")
        elif choice == "6":
            print("Au revoir.")
            break
        else:
            print("Choix invalide!")
else:
    # Si importé, exécuter directement la configuration
    set_module_type()