import time
import random
import subprocess
import logging
import sys
from core.config_manager import ConfigManager

# Configuration du log spécifique au scheduler
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCHEDULER] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()


def get_intervals():
    """Récupère les intervalles depuis la config dynamique ou utilise des défauts."""
    config = ConfigManager.get_config()
    automation = config.get("automation", {})
    # Par défaut : entre 15 et 45 minutes
    min_m = automation.get("min_interval_minutes", 30)
    max_m = automation.get("max_interval_minutes", 90)
    return min_m, max_m


def main():
    logger.info("🕰️ Démarrage du Scheduler LBC Hunter...")

    while True:
        # 1. Lancement du worker en mode SMART
        logger.info("🚀 Lancement du worker (Mode SMART)...")
        try:
            # On utilise sys.executable pour être sûr d'utiliser le même python (venv)
            subprocess.run([sys.executable, "main.py", "--smart"], check=False)
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'exécution du worker : {e}")

        # 2. Calcul du temps d'attente aléatoire
        min_m, max_m = get_intervals()
        wait_minutes = random.randint(min_m, max_m)
        wait_seconds = wait_minutes * 60

        logger.info(
            f"💤 Prochain scan dans {wait_minutes} minutes ({time.strftime('%H:%M', time.localtime(time.time() + wait_seconds))})")

        # 3. Dodo
        time.sleep(wait_seconds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt du Scheduler.")
