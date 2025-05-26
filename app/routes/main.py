from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.models import Medicament
import os

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    medicaments = Medicament.query.all()
    return render_template('index.html', medicaments=medicaments)

@bp.route('/medicament/<int:id>')
def medicament_details(id):
    medicament = Medicament.query.get_or_404(id)
    # Convertir le nom du médicament en minuscules et remplacer les espaces par des underscores
    template_name = medicament.nom.lower().replace(' ', '_')
    template_path = f'medicaments/{template_name}.html'
    
    # Vérifier si le template existe
    if not os.path.exists(os.path.join('app', 'templates', template_path)):
        # Si le template n'existe pas, utiliser un template générique
        return render_template('medicaments/generic.html', medicament=medicament)
    
    return render_template(template_path, medicament=medicament)

@bp.route('/legal')
def legal():
    return render_template('legal.html', title='Mentions légales')

@bp.route('/contact')
def contact():
    return render_template('contact.html', title='Contact') 