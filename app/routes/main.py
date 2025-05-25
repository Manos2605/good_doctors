from flask import Blueprint, render_template
from flask_login import login_required, current_user

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html', title='Accueil')

@bp.route('/legal')
def legal():
    return render_template('legal.html', title='Mentions légales')

@bp.route('/contact')
def contact():
    return render_template('contact.html', title='Contact') 