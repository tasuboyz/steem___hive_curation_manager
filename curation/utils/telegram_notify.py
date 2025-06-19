import requests
import logging

logger = logging.getLogger(__name__)

def send_telegram_message(bot_token, chat_id, message, parse_mode="HTML"):
    """
    Invia un messaggio Telegram tramite bot.
    Args:
        bot_token (str): Token del bot Telegram
        chat_id (str/int): ID della chat o canale
        message (str): Testo del messaggio
        parse_mode (str): Modalità di parsing (HTML o Markdown)
    Returns:
        bool: True se il messaggio è stato inviato con successo, False altrimenti
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"Messaggio Telegram inviato a {chat_id}")
            return True
        else:
            logger.error(f"Errore invio Telegram: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Eccezione invio Telegram: {e}")
        return False
