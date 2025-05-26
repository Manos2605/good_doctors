from flask import Blueprint, render_template
from flask_login import login_required
from app.models import Medicament

bp = Blueprint('consultations', __name__)

@bp.route('/medicaments/<int:id>')
@login_required
def detail_medicament(id):
    medicament = Medicament.query.get_or_404(id)
    return render_template('consultations/detail_medicament.html',
                         title=f'{medicament.nom} - Détails',
                         medicament=medicament) 