from flask import request, jsonify, render_template
from curation.components.db import User, db
from curation.components.logger_config import logger
from curation.components.config import TEST
from curation.components.factory import create_app, init_services, app_state
from curation.services.user_service import UserService
import signal
import sys

app = create_app()

# Definire le route
@app.route('/')
def home():
    return render_template('index.html')

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
    
    # Inizializza tutti i servizi
    init_services(app)
    
    # Avvia l'applicazione
    try:
        debug_mode = not TEST  # Debug attivo solo quando non in modalità test
        app.run(debug=debug_mode, port=8088, host='0.0.0.0')
    except KeyboardInterrupt:
        # Questo blocco è un backup, il gestore di segnale dovrebbe gestire l'interruzione
        app_state.stop_all()
        logger.info("Applicazione arrestata")
