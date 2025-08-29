#!/usr/bin/env python3
"""Small test script to fetch previous author post voters and send them to n8n webhook.

Usage: python test.py

This script tries to reproduce the snippet provided and uses the existing
`Blockchain`, `VoteManager` and `send_post_voters_to_n8n` utilities.
"""
import logging
import sys

from curation.components.beem import Blockchain
from curation.utils.vote import VoteManager
from curation.utils.webhook import send_post_voters_to_n8n


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")


def main():
    # Esempio fornito dall'utente
    sample = "@cryptopie/renting-our-neighbors-unused-house-will-going-to-suck-to-stay-into-because-the-toilet-has-no-flush"

    # Estrai author e permlink dal sample
    try:
        if sample.startswith('@'):
            _, rest = sample.split('@', 1)
        else:
            rest = sample
        author, permlink = rest.split('/', 1)
    except Exception as e:
        logger.error(f"Impossibile parsare il sample string: {e}")
        sys.exit(1)

    platform = 'steem'  # Cambiare in 'hive' se necessario

    blockchain = Blockchain()
    vote_manager = VoteManager(blockchain_connector_instance=blockchain)

    # 1) prova a recuperare il post precedente (come nel flusso reale)
    try:
        previous_post = blockchain.get_previous_author_posts(author, platform, limit=1)
        if previous_post and len(previous_post) > 0:
            prev_permlink = previous_post[0].get('permlink', '')
            logger.info(f"Trovato post precedente: @{author}/{prev_permlink}")
        else:
            logger.info("Nessun post precedente trovato, uso il permlink di esempio")
            prev_permlink = permlink
    except Exception as e:
        logger.warning(f"Errore recupero post precedente: {e}. Uso il permlink di esempio")
        prev_permlink = permlink

    # 2) ottieni i votanti del post precedente (basati su rshares/min_importance come richiesto)
    try:
        post_identifier = f"@{author}/{prev_permlink}"
        logger.info(f"Richiedo i votanti per {post_identifier} (min_importance=0.1)")
        post_voters = vote_manager.get_post_voters(post_identifier, min_importance=0.1)
        logger.info(f"Trovati {len(post_voters)} votanti (raw)")
    except Exception as e:
        logger.error(f"Errore ottenimento post_voters: {e}")
        post_voters = []

    # 3) Invia al webhook n8n usando la funzione riutilizzabile
    try:
        resp = send_post_voters_to_n8n(author, prev_permlink, post_voters)
        logger.info(f"Webhook response: status={getattr(resp, 'status_code', None)}")
    except Exception:
        # L'errore è già loggato nella funzione; non bloccare il flusso del test
        logger.warning("Invio al webhook fallito (vedi log per dettagli)")

    # 4) Piccola summary locale: ordina per rshares/steem_vote_value per verificare il comportamento
    try:
        sorted_by_value = sorted(
            post_voters,
            key=lambda v: (v.get('steem_vote_value', 0) or 0, v.get('importance', 0)),
            reverse=True,
        )
        logger.info("Top 5 votanti (per valore):")
        for v in sorted_by_value[:5]:
            logger.info(f"- {v.get('voter')} rshares={v.get('rshares')} value={v.get('steem_vote_value')} delay_min={v.get('vote_delay_minutes')}")
    except Exception as e:
        logger.debug(f"Impossibile calcolare summary dei votanti: {e}")


if __name__ == '__main__':
    main()
