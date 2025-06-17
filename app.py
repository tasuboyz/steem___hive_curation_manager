from flask import request, jsonify, render_template, redirect
from curation.components.logger_config import logger
from curation.components.config import TEST
from curation.components.factory import create_app, init_services, app_state
from curation.services.user_service import UserService
from curation.services.settings_service import SettingsService
from curation.services.auth_service import AuthService
from curation.middleware.auth_middleware import auth_required, get_current_user, check_user_limits
from curation.components.beem import Blockchain
from curation.utils.vote import VoteManager
import signal
import sys
import os

app = create_app()
blockchain_connector = Blockchain(app=app)  # Istanza globale per la classe Blockchain
vote_manager = VoteManager()

# === ROUTE DI AUTENTICAZIONE ===

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login con username blockchain e posting key"""
    data = request.json
    if not data or 'username' not in data or 'posting_key' not in data or 'platform' not in data:
        return jsonify({'error': 'Username, posting_key and platform required'}), 400
    
    username = data['username'].strip()
    posting_key = data['posting_key'].strip()
    platform = data['platform'].lower()
    
    if platform not in ['steem', 'hive']:
        return jsonify({'error': 'Platform must be steem or hive'}), 400
    
    result = AuthService.authenticate_user(username, posting_key, platform)
    
    if result['success']:
        response = jsonify({
            'message': result['message'],
            'user': AuthService.get_user_stats(result['user']),
            'token': result['token']
        })
        # Imposta anche il cookie per compatibilità con il frontend esistente
        response.set_cookie('session_token', result['token'], 
                          max_age=30*24*60*60, httponly=True, secure=False)
        return response
    else:
        return jsonify({'error': result['message']}), 401

@app.route('/api/auth/logout', methods=['POST'])
@auth_required
def logout():
    """Logout dell'utente"""
    token = request.cookies.get('session_token')
    if not token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
    
    if token:
        AuthService.logout_user(token)
    
    response = jsonify({'message': 'Logged out successfully'})
    response.set_cookie('session_token', '', expires=0)
    return response

@app.route('/api/auth/me', methods=['GET'])
@auth_required
def get_current_user_info():
    """Ottieni informazioni sull'utente corrente"""
    user = get_current_user()
    return jsonify(AuthService.get_user_stats(user))

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Controlla se l'utente è autenticato"""
    token = request.cookies.get('session_token')
    if not token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
    
    if token:
        user_account = AuthService.verify_session_token(token)
        if user_account:
            return jsonify({
                'authenticated': True,
                'user': AuthService.get_user_stats(user_account)
            })
    
    return jsonify({'authenticated': False})

# Definire le route
@app.route('/')
def home():
    # Verifica se l'utente ha un token di sessione valido
    token = request.cookies.get('session_token')
    if token:
        user_account = AuthService.verify_session_token(token)
        if user_account:
            return render_template('index.html')
    
    # Se non autenticato, reindirizza al login
    return redirect('/login.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

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
        
        voters_data = vote_manager.get_post_voters(post_url, min_importance)
        
        # Calcola il tempo ottimale di voto in base ai votanti importanti
        optimal_vote_info = vote_manager.calculate_optimal_vote_time(voters_data)
        
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
@auth_required
@check_user_limits(max_watched=True)
def add_user():
    user_data = request.json
    user_account = get_current_user()
    
    # Aggiungi l'ID dell'account utente ai dati
    user_data['user_account_id'] = user_account.id
    
    success = UserService.add_user(user_data)
    if success:
        return jsonify({'message': 'User added successfully'})
    return jsonify({'message': 'Error adding user'}), 500

@app.route('/users/<username>', methods=['PUT'])
@auth_required
def update_user(username):
    user_data = request.json
    user_account = get_current_user()
    
    success = UserService.update_user(username, user_data, user_account.id)
    if success:
        return jsonify({'message': 'User updated successfully'})
    return jsonify({'message': 'User not found or error updating'}), 404

@app.route('/users/<username>', methods=['DELETE'])
@auth_required
def delete_user(username):
    user_account = get_current_user()
    success = UserService.delete_user(username, user_account.id)
    if success:
        return jsonify({'message': 'User deleted successfully'})
    return jsonify({'message': 'User not found'}), 404

@app.route('/users/<username>', methods=['GET'])
@auth_required
def get_user(username):
    user_account = get_current_user()
    user_data = UserService.get_user_by_username(username, user_account.id)
    if user_data:
        return jsonify(user_data)
    return jsonify({'message': 'User not found'}), 404

@app.route('/users', methods=['GET'])
@auth_required
def get_all_users():
    user_account = get_current_user()
    platform = user_account.platform
    username = user_account.username
    watched_accounts = UserService.get_all_users(username, platform)
    user_list = []
    for username, data in watched_accounts.items():
        entry = {
            'username': username,
            'data': data
        }
        user_list.append(entry)
    return jsonify(user_list)

# Routes per la gestione delle impostazioni
@app.route('/api/settings', methods=['GET'])
def get_all_settings():
    """Ottiene tutte le impostazioni dell'applicazione"""
    platform = request.args.get('platform')
    settings = SettingsService.get_all_settings(platform)
    return jsonify(settings)

@app.route('/api/settings/<key>', methods=['GET'])
def get_setting(key):
    """Ottiene un'impostazione specifica"""
    platform = request.args.get('platform')
    value = SettingsService.get_setting(key, platform)
    if value is None:
        return jsonify({'error': f'Setting {key} not found'}), 404
    return jsonify({key: value})

@app.route('/api/settings/<key>', methods=['POST'])
def update_setting(key):
    """Aggiorna un'impostazione specifica"""
    data = request.json
    if not data or 'value' not in data:
        return jsonify({'error': 'Missing value parameter'}), 400
    
    platform = data.get('platform')
    success = SettingsService.set_setting(key, data['value'], platform)
    
    if success:
        return jsonify({'message': f'Setting {key} updated successfully'})
    return jsonify({'error': 'Error updating setting'}), 500

@app.route('/api/curator/info', methods=['GET'])
def get_curator_info():
    """Ottiene le informazioni sul curatore per una piattaforma specifica"""
    platform = request.args.get('platform', 'steem')
    if platform not in ['steem', 'hive']:
        return jsonify({'error': 'Invalid platform. Must be steem or hive'}), 400
    
    curator_info = SettingsService.get_curator_info(platform)
    
    # Non inviamo le chiavi al frontend per motivi di sicurezza
    if 'posting_key' in curator_info:
        curator_info['posting_key_set'] = bool(curator_info['posting_key'])
        del curator_info['posting_key']
    
    if 'active_key' in curator_info:
        curator_info['active_key_set'] = bool(curator_info['active_key'])
        del curator_info['active_key']
    
    return jsonify(curator_info)

@app.route('/api/curator/update', methods=['POST'])
def update_curator_info():
    """Aggiorna le informazioni del curatore"""
    data = request.json
    if not data or 'platform' not in data or 'username' not in data:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    platform = data['platform']
    if platform not in ['steem', 'hive']:
        return jsonify({'error': 'Invalid platform. Must be steem or hive'}), 400
    
    # Aggiorna l'username del curatore
    success = SettingsService.set_setting(f'{platform}_curator', data['username'], platform)
    
    # Aggiorna la chiave posting del curatore se fornita
    if 'posting_key' in data and data['posting_key']:
        success = success and SettingsService.set_setting(
            f'{platform}_curator_posting_key', data['posting_key'], platform)
    
    # Aggiorna la chiave active solo per steem se fornita
    if platform == 'steem' and 'active_key' in data and data['active_key']:
        success = success and SettingsService.set_setting(
            'steem_active_key', data['active_key'], platform)
    
    if success:
        return jsonify({'message': f'{platform.capitalize()} curator info updated successfully'})
    return jsonify({'error': 'Error updating curator info'}), 500

@app.route('/api/test_mode', methods=['GET'])
def get_test_mode():
    """Ottiene lo stato della modalità test"""
    test_mode = SettingsService.is_test_mode()
    return jsonify({'test_mode': test_mode})

@app.route('/api/test_mode', methods=['POST'])
def update_test_mode():
    """Aggiorna lo stato della modalità test"""
    data = request.json
    if not data or 'enabled' not in data:
        return jsonify({'error': 'Missing enabled parameter'}), 400
    
    value = 'true' if data['enabled'] else 'false'
    success = SettingsService.set_setting('test_mode', value)
    
    if success:
        return jsonify({'message': 'Test mode updated successfully'})
    return jsonify({'error': 'Error updating test mode'}), 500

@app.route('/api/bot/info', methods=['GET'])
def get_bot_info():
    """Ottiene le informazioni del bot Telegram"""
    admin_ids = SettingsService.get_setting('admin_ids', default='')
    bot_token = SettingsService.get_setting('bot_token', default='')
    
    # Prepara i dati per il frontend (nascondi parzialmente il token per sicurezza)
    masked_token = ""
    if bot_token:
        parts = bot_token.split(':')
        if len(parts) == 2:
            masked_token = f"{parts[0]}:{'*' * (len(parts[1]) - 4)}{parts[1][-4:]}"
    
    return jsonify({
        'admin_ids': admin_ids,
        'bot_token': bot_token,
        'masked_token': masked_token,
        'token_set': bool(bot_token)
    })

@app.route('/api/bot/update', methods=['POST'])
def update_bot_info():
    """Aggiorna le informazioni del bot Telegram"""
    data = request.json
    if not data:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    success = True
    
    # Aggiorna gli admin IDs se forniti
    if 'admin_ids' in data:
        success = success and SettingsService.set_setting('admin_ids', data['admin_ids'])
    
    # Aggiorna il token del bot se fornito
    if 'bot_token' in data and data['bot_token']:
        success = success and SettingsService.set_setting('bot_token', data['bot_token'])
    
    if success:
        return jsonify({'message': 'Bot information updated successfully'})
    return jsonify({'error': 'Error updating bot information'}), 500

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
    
    is_main_process = not debug_mode or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    
    if is_main_process:
        logger.info("Inizializzando i servizi nel processo principale...")
        init_services(app)
    else:
        logger.info("Processo secondario, saltando l'inizializzazione dei servizi")
        
    try:
        app.run(debug=debug_mode, port=8089, host='0.0.0.0', use_reloader=debug_mode)
    except KeyboardInterrupt:
        # Questo blocco è un backup, il gestore di segnale dovrebbe gestire l'interruzione
        app_state.stop_all()
        logger.info("Applicazione arrestata")
