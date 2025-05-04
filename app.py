from flask import request, jsonify, render_template
from curation.components.db import User, db
from curation.components.logger_config import logger
from curation.components.config import TEST
from curation.components.factory import create_app, init_services, app_state
from curation.services.user_service import UserService
from curation.components.beem import Blockchain
import signal
import sys
import os

app = create_app()
blockchain_connector = Blockchain()  # Istanza globale per la classe Blockchain

# Definire le route
@app.route('/')
def home():
    return render_template('index.html')

# Nuovo endpoint per ottenere i votanti di un post
@app.route('/api/post_voters', methods=['GET'])
def get_post_voters():
    post_url = request.args.get('post_url')
    min_importance = float(request.args.get('min_importance', 0.0))
    
    if not post_url:
        return jsonify({'error': 'Missing post_url parameter'}), 400
    
    try:
        # Determina la blockchain in base all'URL
        platform = 'hive' if 'peakd.com' in post_url or 'hive.blog' in post_url else 'steem'
        
        # Inizializza l'istanza di blockchain corretta
        for node_url in blockchain_connector.node_urls.get(platform):
            if blockchain_connector.ping_server(node_url):
                if platform == 'steem':
                    from beem import Steem
                    blockchain_connector.blockchain = Steem(node=node_url)
                else:
                    from beem import Hive
                    blockchain_connector.blockchain = Hive(node=node_url)
                break
        
        if blockchain_connector.blockchain is None:
            return jsonify({'error': f'No available {platform} node'}), 503
        
        voters_data = blockchain_connector.get_post_voters(post_url, min_importance)
        
        # Calcola il tempo ottimale di voto in base ai votanti importanti
        optimal_vote_info = blockchain_connector.calculate_optimal_vote_time(voters_data)
        
        return jsonify({
            'voters': voters_data[:10],  # Limita ai 10 votanti più importanti
            'total_voters': len(voters_data),
            'platform': platform,
            'optimal_vote_time': optimal_vote_info
        })
    except Exception as e:
        logger.error(f"Errore nel recupero dei votanti per {post_url}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/users', methods=['POST'])
def add_user():
    user_data = request.json
    success = UserService.add_user(user_data)
    if success:
        return jsonify({'message': 'User added successfully'})
    return jsonify({'message': 'Error adding user'}), 500

@app.route('/users/<username>', methods=['PUT'])
def update_user(username):
    user_data = request.json
    success = UserService.update_user(username, user_data)
    if success:
        return jsonify({'message': 'User updated successfully'})
    return jsonify({'message': 'User not found or error updating'}), 404

@app.route('/users/<username>', methods=['DELETE'])
def delete_user(username):
    success = UserService.delete_user(username)
    if success:
        return jsonify({'message': 'User deleted successfully'})
    return jsonify({'message': 'User not found'}), 404

@app.route('/users/<username>', methods=['GET'])
def get_user(username):
    user_data = UserService.get_user_by_username(username)
    if user_data:
        return jsonify(user_data)
    return jsonify({'message': 'User not found'}), 404

@app.route('/users', methods=['GET'])
def get_all_users():
    users = UserService.get_users_by_platform()
    user_list = [{'username': user.username, 'data': user.data} for user in users]
    return jsonify(user_list)

def handle_shutdown(signal, frame):
    """Gestisce l'arresto pulito dell'applicazione"""
    logger.info("Segnale di arresto ricevuto, chiusura dell'applicazione...")
    app_state.stop_all()
    sys.exit(0)

if __name__ == '__main__':
    # Configura i gestori di segnale per il graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Avvia i servizi solo nel processo principale quando non si è in modalità debug
    # o quando si è nel processo principale in modalità debug
    debug_mode = not TEST
    
    # In Flask debug mode, the reloader will spawn a child process, we only want to initialize
    # services in the main process to avoid duplications
    is_main_process = not debug_mode or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    
    if is_main_process:
        logger.info("Inizializzando i servizi nel processo principale...")
        init_services(app)
    else:
        logger.info("Processo secondario, saltando l'inizializzazione dei servizi")
    
    # Avvia l'applicazione
    try:
        app.run(debug=debug_mode, port=8089, host='0.0.0.0', use_reloader=debug_mode)
    except KeyboardInterrupt:
        # Questo blocco è un backup, il gestore di segnale dovrebbe gestire l'interruzione
        app_state.stop_all()
        logger.info("Applicazione arrestata")
