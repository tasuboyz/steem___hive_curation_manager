import threading
from flask import Flask, request, jsonify, render_template
from curation.components.db import User, db  # Importa il modello e l'istanza di SQLAlchemy
from curation.components.instance import local_data_list
from curation.sniper import SocialMediaPublisher
from curation.components.beem import Blockchain
from curation.utils.data_loader import get_user_data
from apscheduler.schedulers.background import BackgroundScheduler
from curation.action import _run_check_cycle
from curation.components.logger_config import logger
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'  # Configura il database
db.init_app(app)  # Inizializza SQLAlchemy con l'app

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/users', methods=['POST'])
def add_user():
    get_user_data()
    user_data = request.json
    new_user = User(username=user_data['username'], data=user_data)
    db.session.add(new_user)
    db.session.commit()
    get_user_data()
    return jsonify({'message': 'User added successfully'})

@app.route('/users/<username>', methods=['PUT'])
def update_user(username):
    get_user_data()
    user_data = request.json
    user = User.query.filter_by(username=username).first()
    if user:
        user.data = user_data
        db.session.commit()
        get_user_data()
        return jsonify({'message': 'User updated successfully'})
    return jsonify({'message': 'User not found'}), 404

@app.route('/users/<username>', methods=['DELETE'])
def delete_user(username):
    user = User.query.filter_by(username=username).first()
    if user:
        db.session.delete(user)
        db.session.commit()
        get_user_data()
        return jsonify({'message': 'User deleted successfully'})
    return jsonify({'message': 'User not found'}), 404

@app.route('/users/<username>', methods=['GET'])
def get_user(username):
    user = User.query.filter_by(username=username).first()
    if user:
        user_list = user.data
        get_user_data()
        return jsonify(user_list)
    return jsonify({'message': 'User not found'}), 404

@app.route('/users', methods=['GET'])
def get_all_users():
    get_user_data()  # Aggiorna i dati degli utenti prima di restituire la lista
    users = User.query.all()
    user_list = [{'username': user.username, 'data': user.data} for user in users]
    return jsonify(user_list)

def run_scheduler():
    with app.app_context():  # Assicurati di avere il contesto dell'app
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=get_user_data, trigger="interval", seconds=600)  # Aggiorna ogni 10 minuti
        scheduler.start()
        return scheduler
    
def create_app():
    with app.app_context():
        db.create_all()
        get_user_data()
    return app

def start_monitoring(app):
    """Avvia il monitoraggio delle deleghe con contesto applicazione"""
    with app.app_context():
        logger.info("Avvio del monitoraggio delle deleghe...")
        while True:
            try:
                _run_check_cycle()
            except Exception as e:
                logger.error(f"Errore durante il ciclo di monitoraggio: {str(e)}")
            time.sleep(60)
    
if __name__ == '__main__':
    app = create_app()
    monitor_thread = threading.Thread(target=start_monitoring, args=(app,), daemon=True)
    monitor_thread.start()
    publisher = SocialMediaPublisher()  # Crea un'istanza di SocialMediaPublisher
    publisher_thread = threading.Thread(target=publisher.publish_posts)  # Avvia publish_posts in un thread separato
    publisher_thread.start()

    try:
        app.run(debug=True, port= 8088, host='0.0.0.0')
    except KeyboardInterrupt:
        # scheduler.shutdown()  # Ferma il scheduler quando l'app viene chiusa
        print("Scheduler shut down successfully.")
