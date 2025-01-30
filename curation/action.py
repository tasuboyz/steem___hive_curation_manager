from .components.logger_config import logger
import time
from datetime import datetime
from .components.beem import Blockchain

beem = Blockchain()

def start_monitoring(self):
        logger.info("Avvio del monitoraggio delle deleghe...")
        while True:
            try:
                _run_check_cycle()
            except Exception as e:
                logger.error(f"Errore durante il ciclo di monitoraggio: {str(e)}")
            finally:
                # Attendi prima del prossimo ciclo
                time.sleep(60)

def _run_check_cycle(self):
    """Esegue un singolo ciclo di controllo."""
    logger.info(f"Inizio nuovo ciclo di controllo alle {datetime.utcnow().isoformat()}")
    
    # Ottieni le deleghe
    delegate_ops = beem.get_steem_delegators()
    
    if delegate_ops:
        logger.info(f"Trovate {len(delegate_ops)} nuove/modificate deleghe")
    else:
        logger.debug("Nessuna nuova delega trovata")

    # # Aggiorna il timestamp dell'ultimo controllo
    # self.last_check_time = datetime.utcnow()
    # logger.info(f"Ciclo completato. Prossimo controllo tra {self.check_interval} secondi")