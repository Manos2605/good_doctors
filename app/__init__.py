from flask import Flask, redirect, url_for, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
import os
from werkzeug.utils import secure_filename

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'info'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return filename
    return None

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes import auth, main, consultations
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(consultations.bp)

    @app.route('/')
    def index():
        return redirect(url_for('main.index'))

    return app 