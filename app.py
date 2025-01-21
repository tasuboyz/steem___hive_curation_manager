import threading
from flask import Flask, request, jsonify, render_template
from db import User, db  # Importa il modello e l'istanza di SQLAlchemy
from curation.components.instance import local_data_list
from curation.sniper import SocialMediaPublisher

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'  # Configura il database
db.init_app(app)  # Inizializza SQLAlchemy con l'app

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/users', methods=['POST'])
def add_user():
    user_data = request.json
    new_user = User(username=user_data['username'], data=user_data)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User added successfully'})

@app.route('/users/<username>', methods=['PUT'])
def update_user(username):
    user_data = request.json
    user = User.query.filter_by(username=username).first()
    if user:
        user.data = user_data
        db.session.commit()
        return jsonify({'message': 'User updated successfully'})
    return jsonify({'message': 'User not found'}), 404

@app.route('/users/<username>', methods=['DELETE'])
def delete_user(username):
    user = User.query.filter_by(username=username).first()
    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'})
    return jsonify({'message': 'User not found'}), 404

@app.route('/users/<username>', methods=['GET'])
def get_user(username):
    user = User.query.filter_by(username=username).first()
    if user:
        user_list = user.data
        return jsonify(user_list)
    return jsonify({'message': 'User not found'}), 404

@app.route('/users', methods=['GET'])
def get_all_users():
    users = User.query.all()
    user_list = [{'username': user.username, 'data': user.data} for user in users]
    return jsonify(user_list)

def get_user_data():
    users = User.query.all()
    for user in users:
        user_data = {
            'username': user.data['username'],
            'platform': user.data['platform'],
            'voteDelay': user.data['voteDelay'],
            'voteWeight': user.data['voteWeight'],
            'timestamp': user.data['timestamp']
        }   
        local_data_list.append(user_data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crea tutte le tabelle
        get_user_data()  # Ottieni i dati degli utenti dal database
    publisher = SocialMediaPublisher()  # Create an instance of SocialMediaPublisher
    publisher_thread = threading.Thread(target=publisher.publish_posts)  # Start publish_posts in a separate thread
    publisher_thread.start()
    app.run(debug=True, port=8088, host='0.0.0.0')
