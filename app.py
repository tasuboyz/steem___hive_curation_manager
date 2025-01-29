import threading
from flask import Flask, request, jsonify, render_template
from curation.components.db import User, db  # Importa il modello e l'istanza di SQLAlchemy
from curation.components.instance import local_data_list
from curation.sniper import SocialMediaPublisher
from curation.components.beem import Blockchain
from curation.utils.data_loader import get_user_data
from apscheduler.schedulers.background import BackgroundScheduler

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crea tutte le tabelle
        beem = Blockchain()  # Crea un'istanza di Blockchain
        get_user_data() 
        delegatos = beem.get_steem_delegators()  # Ottieni la lista dei delegatori Steem

    publisher = SocialMediaPublisher()  # Crea un'istanza di SocialMediaPublisher
    publisher_thread = threading.Thread(target=publisher.publish_posts)  # Avvia publish_posts in un thread separato
    publisher_thread.start()

    try:
        app.run(debug=True, port= 8088, host='0.0.0.0')
    except KeyboardInterrupt:
        # scheduler.shutdown()  # Ferma il scheduler quando l'app viene chiusa
        print("Scheduler shut down successfully.")
