from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.models import Consultation, RendezVous, User, Message
from app import db

bp = Blueprint('consultations', __name__)

@bp.route('/consultations')
@login_required
def index():
    if current_user.role in ['medecin', 'veterinaire']:
        consultations = Consultation.query.filter_by(medecin_id=current_user.id).order_by(Consultation.date.desc()).all()
    else:
        consultations = Consultation.query.filter_by(patient_id=current_user.id).order_by(Consultation.date.desc()).all()
    return render_template('consultations/index.html', title='Consultations', consultations=consultations)

@bp.route('/consultations/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle():
    if request.method == 'GET':
        medecin_id = request.args.get('medecin_id')
        date = request.args.get('date')
        
        if not medecin_id:
            flash('Médecin non spécifié', 'error')
            return redirect(url_for('main.index'))
            
        medecin = User.query.get_or_404(medecin_id)
        if medecin.role not in ['medecin', 'veterinaire']:
            flash('Utilisateur non autorisé', 'error')
            return redirect(url_for('main.index'))
            
        creneaux = []
        if date:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            # Récupérer les créneaux disponibles pour cette date
            creneaux = RendezVous.query.filter(
                RendezVous.medecin_id == medecin_id,
                RendezVous.date_debut >= date_obj,
                RendezVous.date_debut < date_obj + timedelta(days=1),
                RendezVous.statut == 'disponible'
            ).order_by(RendezVous.date_debut).all()
            
        return render_template('consultations/nouvelle.html', 
                             medecin=medecin,
                             date=date,
                             creneaux=creneaux,
                             now=datetime.now())
                             
    elif request.method == 'POST':
        medecin_id = request.form.get('medecin_id')
        date_str = request.form.get('date')
        type_consultation = request.form.get('type')
        description = request.form.get('description')
        
        if not all([medecin_id, date_str, type_consultation]):
            flash('Tous les champs obligatoires doivent être remplis', 'error')
            return redirect(url_for('consultations.nouvelle', medecin_id=medecin_id))
            
        medecin = User.query.get_or_404(medecin_id)
        if medecin.role not in ['medecin', 'veterinaire']:
            flash('Utilisateur non autorisé', 'error')
            return redirect(url_for('main.index'))
            
        date_debut = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        
        # Vérifier si le créneau est toujours disponible
        rendez_vous = RendezVous.query.filter(
            RendezVous.medecin_id == medecin_id,
            RendezVous.date_debut == date_debut,
            RendezVous.statut == 'disponible'
        ).first()
        
        if not rendez_vous:
            flash('Ce créneau n\'est plus disponible', 'error')
            return redirect(url_for('consultations.nouvelle', medecin_id=medecin_id))
            
        # Créer la consultation
        consultation = Consultation(
            patient_id=current_user.id,
            medecin_id=medecin_id,
            date=date_debut,
            duree=30,  # Durée fixe de 30 minutes
            type=type_consultation,
            description=description,
            statut='planifiee'
        )
        
        # Mettre à jour le statut du rendez-vous
        rendez_vous.statut = 'reserve'
        rendez_vous.consultation = consultation
        
        try:
            db.session.add(consultation)
            db.session.commit()
            flash('Rendez-vous pris avec succès', 'success')
            return redirect(url_for('consultations.detail', id=consultation.id))
        except Exception as e:
            db.session.rollback()
            flash('Une erreur est survenue lors de la prise de rendez-vous', 'error')
            return redirect(url_for('consultations.nouvelle', medecin_id=medecin_id))

@bp.route('/consultations/<int:id>')
@login_required
def detail(id):
    consultation = Consultation.query.get_or_404(id)
    if current_user.id not in [consultation.medecin_id, consultation.patient_id]:
        flash('Vous n\'avez pas accès à cette consultation.', 'danger')
        return redirect(url_for('consultations.index'))
    
    messages = Message.query.filter_by(consultation_id=id).order_by(Message.date_envoi).all()
    return render_template('consultations/detail.html', 
                         title='Détail Consultation',
                         consultation=consultation,
                         messages=messages)

@bp.route('/consultations/<int:id>/message', methods=['POST'])
@login_required
def envoyer_message(id):
    consultation = Consultation.query.get_or_404(id)
    if current_user.id not in [consultation.medecin_id, consultation.patient_id]:
        return jsonify({'error': 'Accès non autorisé'}), 403

    contenu = request.form.get('contenu')
    if not contenu:
        return jsonify({'error': 'Le message ne peut pas être vide'}), 400

    destinataire_id = consultation.patient_id if current_user.id == consultation.medecin_id else consultation.medecin_id

    message = Message(
        contenu=contenu,
        expediteur_id=current_user.id,
        destinataire_id=destinataire_id,
        consultation_id=id
    )

    db.session.add(message)
    db.session.commit()

    return jsonify({
        'id': message.id,
        'contenu': message.contenu,
        'date_envoi': message.date_envoi.strftime('%d/%m/%Y %H:%M'),
        'expediteur': current_user.prenom + ' ' + current_user.nom
    })

@bp.route('/consultations/<int:id>/status', methods=['POST'])
@login_required
def update_status(id):
    if current_user.role not in ['medecin', 'veterinaire']:
        return jsonify({'error': 'Accès non autorisé'}), 403

    consultation = Consultation.query.get_or_404(id)
    if consultation.medecin_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403

    status = request.form.get('status')
    if status not in ['planifiee', 'en_cours', 'terminee', 'annulee']:
        return jsonify({'error': 'Statut invalide'}), 400

    consultation.statut = status
    db.session.commit()

    return jsonify({'success': True})

@bp.route('/consultations/<int:id>/notes', methods=['POST'])
@login_required
def update_notes(id):
    if current_user.role not in ['medecin', 'veterinaire']:
        return jsonify({'error': 'Accès non autorisé'}), 403

    consultation = Consultation.query.get_or_404(id)
    if consultation.medecin_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403

    notes = request.form.get('notes')
    consultation.notes = notes
    db.session.commit()

    return jsonify({'success': True})

@bp.route('/rendez-vous')
@login_required
def rendez_vous():
    if current_user.role not in ['medecin', 'veterinaire']:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('consultations.index'))

    date_debut = request.args.get('date_debut', datetime.now().strftime('%Y-%m-%d'))
    date_fin = request.args.get('date_fin', (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))

    rendez_vous = RendezVous.query.filter(
        RendezVous.medecin_id == current_user.id,
        RendezVous.date_debut >= datetime.strptime(date_debut, '%Y-%m-%d'),
        RendezVous.date_debut <= datetime.strptime(date_fin, '%Y-%m-%d')
    ).order_by(RendezVous.date_debut).all()

    return render_template('consultations/rendez_vous.html',
                         title='Gestion des Rendez-vous',
                         rendez_vous=rendez_vous,
                         date_debut=date_debut,
                         date_fin=date_fin)

@bp.route('/rendez-vous/nouveau', methods=['POST'])
@login_required
def nouveau_rendez_vous():
    if current_user.role not in ['medecin', 'veterinaire']:
        return jsonify({'error': 'Accès non autorisé'}), 403

    date_debut = datetime.strptime(request.form.get('date_debut'), '%Y-%m-%dT%H:%M')
    date_fin = datetime.strptime(request.form.get('date_fin'), '%Y-%m-%dT%H:%M')
    medecin_id = request.form.get('medecin_id', current_user.id)

    # Vérifier que le médecin existe
    medecin = User.query.filter_by(id=medecin_id, role__in=['medecin', 'veterinaire']).first()
    if not medecin:
        return jsonify({'error': 'Médecin non trouvé'}), 404

    # Vérifier les conflits
    conflit = RendezVous.query.filter(
        RendezVous.medecin_id == medecin_id,
        RendezVous.date_debut < date_fin,
        RendezVous.date_fin > date_debut
    ).first()

    if conflit:
        return jsonify({'error': 'Ce créneau chevauche un autre rendez-vous'}), 400

    # Créer les créneaux de 30 minutes
    creneaux = []
    current_time = date_debut
    while current_time < date_fin:
        creneau = RendezVous(
            date_debut=current_time,
            date_fin=current_time + timedelta(minutes=30),
            medecin_id=medecin_id,
            statut='disponible'
        )
        creneaux.append(creneau)
        current_time += timedelta(minutes=30)

    db.session.add_all(creneaux)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'{len(creneaux)} créneaux créés avec succès',
        'creneaux': [{
            'id': c.id,
            'date_debut': c.date_debut.strftime('%d/%m/%Y %H:%M'),
            'date_fin': c.date_fin.strftime('%d/%m/%Y %H:%M')
        } for c in creneaux]
    })

@bp.route('/rendez-vous/<int:id>/supprimer', methods=['POST'])
@login_required
def supprimer_rendez_vous(id):
    if current_user.role not in ['medecin', 'veterinaire']:
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    rendez_vous = RendezVous.query.get_or_404(id)
    
    if rendez_vous.medecin_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    if rendez_vous.statut != 'disponible':
        return jsonify({'error': 'Impossible de supprimer un rendez-vous réservé'}), 400
        
    db.session.delete(rendez_vous)
    db.session.commit()
    
    return jsonify({'success': True})

@bp.route('/recherche-medecin', methods=['GET'])
@login_required
def recherche_medecin():
    if current_user.role != 'patient':
        flash('Cette fonctionnalité est réservée aux patients.', 'warning')
        return redirect(url_for('main.index'))
        
    specialite = request.args.get('specialite', '')
    date = request.args.get('date', '')
    
    # Base query pour les médecins et vétérinaires
    query = User.query.filter(User.role.in_(['medecin', 'veterinaire']))
    
    # Filtrer par spécialité si spécifiée
    if specialite:
        query = query.filter(User.specialite.ilike(f'%{specialite}%'))
    
    # Récupérer tous les médecins/vétérinaires
    professionnels = query.all()
    
    # Si une date est spécifiée, filtrer les professionnels disponibles
    if date:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        professionnels_disponibles = []
        
        for pro in professionnels:
            # Vérifier les rendez-vous existants pour cette date
            rendez_vous = RendezVous.query.filter(
                RendezVous.medecin_id == pro.id,
                RendezVous.date == date_obj
            ).all()
            
            # Vérifier les consultations existantes pour cette date
            consultations = Consultation.query.filter(
                Consultation.medecin_id == pro.id,
                Consultation.date == date_obj
            ).all()
            
            # Si moins de 8 rendez-vous/consultations pour cette date, le professionnel est disponible
            if len(rendez_vous) + len(consultations) < 8:
                professionnels_disponibles.append(pro)
                
        professionnels = professionnels_disponibles
    
    return render_template('consultations/recherche_medecin.html',
                         professionnels=professionnels,
                         specialite=specialite,
                         date=date,
                         now=datetime.now()) 