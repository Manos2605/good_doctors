from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

bp = Blueprint('consultations', __name__)

@bp.route('/consultations')
@login_required
def index():
    return render_template('consultations/index.html', title='Consultations')

@bp.route('/consultations/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle():
    if request.method == 'POST':
        # Logique pour créer une nouvelle consultation
        flash('Consultation créée avec succès!', 'success')
        return redirect(url_for('consultations.index'))
    return render_template('consultations/nouvelle.html', title='Nouvelle Consultation') 