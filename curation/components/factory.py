from flask import Flask
import os
from curation.components.db import db
from curation.utils.data_loader import get_user_data
from curation.components.config import TEST

def create_app():
    # Ottieni il percorso base del progetto (directory principale)
    # Il file si trova in curation/components/factory.py, quindi risaliamo di due livelli
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')
    
    print(f"Base directory: {base_dir}")
    print(f"Template directory: {template_dir}")
    print(f"Static directory: {static_dir}")
    print(f"Template directory exists: {os.path.exists(template_dir)}")
    
    # Crea l'app Flask con i percorsi corretti per template e static
    app = Flask(__name__, 
                template_folder=template_dir, 
                static_folder=static_dir)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'
    db.init_app(app)

    with app.app_context():
        db.create_all()
        get_user_data()

    return app