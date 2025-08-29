# 🔍 Steem/Hive Curation Test Interface

Questa è un'interfaccia web per testare il sistema di curation di Steem/Hive. Permette di inserire un sample post e visualizzare i risultati dell'analisi dei votanti.

## 🚀 Come utilizzare

### 1. Avviare il server
```bash
cd test
python app.py
```

Il server si avvierà su `http://localhost:5001`

### 2. Aprire il browser
Navigare su `http://localhost:5001` per accedere all'interfaccia.

### 3. Inserire i dati
- **Sample Post URL**: Inserire l'URL del post nel formato `@author/permlink`
- **Platform**: Scegliere tra "steem" o "hive"
- **Min Importance**: Valore minimo di importanza per filtrare i votanti (0.0 - 1.0)

### 4. Visualizzare i risultati
Dopo aver cliccato su "Analizza Post", verranno mostrati:
- 📊 **Informazioni del post**: Author, permlink, post precedente
- 👥 **Statistiche votanti**: Numero totale e valore complessivo
- 📋 **Tabella votanti**: Lista dettagliata con rshares, valore, importanza e delay
- 🔗 **Risposta webhook**: Status della chiamata al webhook n8n
- 📝 **Logs**: Log dettagliati dell'operazione

## 📁 Struttura Files

```
test/
├── app.py          # Backend Flask
├── index.html      # Interfaccia web principale
├── style.css       # Styling dell'interfaccia
├── script.js       # Logica JavaScript
└── README.md       # Questo file
```

## 🔧 API Endpoints

### POST /api/test-curation
Esegue il test di curation per un dato sample.

**Request Body:**
```json
{
    "sample": "@cryptopie/post-title",
    "platform": "steem",
    "min_importance": 0.1
}
```

**Response:**
```json
{
    "author": "cryptopie",
    "permlink": "post-title",
    "previous_permlink": "previous-post-title",
    "platform": "steem",
    "min_importance": 0.1,
    "post_voters": [...],
    "webhook_response": {...},
    "logs": [...]
}
```

### GET /api/health
Health check del servizio.

## 🎨 Funzionalità UI

- ✨ **Design moderno**: Interfaccia pulita e responsive
- 📱 **Mobile-friendly**: Ottimizzata per dispositivi mobili
- 🔄 **Loading states**: Indicatori di caricamento durante l'elaborazione
- 📊 **Visualizzazione dati**: Tabelle ordinate e statistiche chiare
- 🎯 **Evidenziazione**: Votanti importanti evidenziati visualmente
- 📝 **Logs in tempo reale**: Monitoraggio del processo di analisi

## 🚨 Note Importanti

1. Assicurarsi che il sistema di curation principale sia configurato correttamente
2. I webhook n8n devono essere configurati per ricevere le chiamate
3. Le credenziali per Steem/Hive devono essere configurate nei file di configurazione principale

## 🐛 Troubleshooting

Se l'interfaccia non funziona:

1. Verificare che il server Flask sia in esecuzione
2. Controllare i logs nel browser (F12 > Console)
3. Verificare che le dipendenze Python siano installate
4. Controllare la configurazione del sistema di curation principale

## 📝 Esempi di Sample

```
@cryptopie/renting-our-neighbors-unused-house-will-going-to-suck-to-stay-into-because-the-toilet-has-no-flush
@author/post-title-with-dashes
author/another-post-example
```
