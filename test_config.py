from core.config_manager import ConfigManager

print("--- TEST 1: Chargement Défaut ---")
conf = ConfigManager.get_config()
# Vérification d'une valeur par défaut (0.5 attendu)
print(f"Poids Deal (Défaut) : {conf['weights']['deal']}")

print("\n--- TEST 2: Modification & Sauvegarde ---")
conf['weights']['deal'] = 0.99  # On change la valeur
ConfigManager.save_config(conf)
print("Sauvegarde effectuée.")

print("\n--- TEST 3: Rechargement (Persistance) ---")
conf_new = ConfigManager.get_config()
# Vérification de la persistance (0.99 attendu)
print(f"Poids Deal (Nouveau) : {conf_new['weights']['deal']}")

print("\n--- TEST 4: Reset Usine ---")
ConfigManager.reset_to_default()
conf_reset = ConfigManager.get_config()
# Vérification du retour à la normale (0.5 attendu)
print(f"Poids Deal (Reset) : {conf_reset['weights']['deal']}")

print("\n✅ Si les valeurs sont cohérentes (0.5 -> 0.99 -> 0.5), le Manager fonctionne !")
