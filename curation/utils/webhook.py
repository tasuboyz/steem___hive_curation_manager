import requests
from ..components.logger_config import logger
import json

# Default n8n webhook URL (can be overridden by passing webhook_url)
DEFAULT_N8N_WEBHOOK = "https://edinthor.app.n8n.cloud/webhook-test/64a9a7f0-fafe-4b83-aa7b-abfa2ea25227"


def send_post_voters_to_n8n(author, permlink, post_voters, webhook_url=None, timeout=60):
    """Invia i dati dei votanti di un post a un webhook n8n.

    Args:
        author (str): nome autore
        permlink (str): permlink del post precedente
        post_voters (list): lista di votanti (serializzabile in JSON)
        webhook_url (str|None): URL del webhook; se None viene usato DEFAULT_N8N_WEBHOOK
        timeout (int|float): timeout in secondi per la richiesta

    Raises:
        Exception: se la richiesta fallisce (non-2xx) o ci sono errori di rete
    """
    url = webhook_url or DEFAULT_N8N_WEBHOOK
    payload = {
        'author': author,
        'permlink': permlink,
        'post_voters': json.dumps(post_voters)
    }
    headers = {'Content-Type': 'application/json'}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if resp.ok:
            logger.info(f"Inviati post_voters al webhook ({resp.status_code}) per @{author}/{permlink}")
            return resp
        else:
            msg = f"Webhook returned {resp.status_code}: {resp.text}"
            logger.warning(msg)
            raise Exception(msg)
    except Exception as e:
        logger.error(f"Errore invio post_voters al webhook per @{author}/{permlink}: {e}")
        raise
