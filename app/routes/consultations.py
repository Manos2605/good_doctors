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

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
        
    try:
        # Récupérer la dernière consultation du patient
        last_consultation = Consultation.query.filter_by(patient_id=current_user.id).order_by(Consultation.date.desc()).first()
        
        # Récupérer les consultations à venir
        upcoming_consultations = Consultation.query.filter(
            Consultation.patient_id == current_user.id,
            Consultation.date >= datetime.now(),
            Consultation.statut == 'planifiee'
        ).order_by(Consultation.date).all()
        
        # Récupérer l'historique des consultations
        past_consultations = Consultation.query.filter(
            Consultation.patient_id == current_user.id,
            Consultation.date < datetime.now()
        ).order_by(Consultation.date.desc()).limit(5).all()
        
        # Préparer les données pour le template
        dashboard_data = {
            'last_consultation': {
                'date': last_consultation.date.strftime('%d %B %Y') if last_consultation else 'Aucune consultation',
                'medecin': f"{last_consultation.medecin.prenom} {last_consultation.medecin.nom}" if last_consultation and last_consultation.medecin else None,
                'type': last_consultation.type if last_consultation else None,
                'statut': last_consultation.statut if last_consultation else None
            } if last_consultation else None,
            'upcoming_consultations': [{
                'id': c.id,
                'date': c.date.strftime('%d %B %Y %H:%M'),
                'medecin': f"{c.medecin.prenom} {c.medecin.nom}",
                'type': c.type,
                'statut': c.statut
            } for c in upcoming_consultations] if upcoming_consultations else [],
            'past_consultations': [{
                'id': c.id,
                'date': c.date.strftime('%d %B %Y %H:%M'),
                'medecin': f"{c.medecin.prenom} {c.medecin.nom}",
                'type': c.type,
                'statut': c.statut
            } for c in past_consultations] if past_consultations else []
        }
        
        return render_template('patient/dashboard.html', 
                             title='Tableau de bord',
                             data=dashboard_data)
    except Exception as e:
        flash('Une erreur est survenue lors du chargement du tableau de bord.', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/video_consultation')
@login_required
def video_consultation():
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    # Récupérer les consultations vidéo à venir
    consultations_video = Consultation.query.filter(
        Consultation.patient_id == current_user.id,
        Consultation.type == 'video',
        Consultation.date >= datetime.now(),
        Consultation.statut == 'planifiee'
    ).order_by(Consultation.date).all()
    
    return render_template('consultations/video_consultation.html',
                         title='Consultation Vidéo',
                         consultations=consultations_video)

@bp.route('/urgence')
@login_required
def urgence():
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    # Récupérer les médecins disponibles en urgence
    medecins_urgence = User.query.filter(
        User.role.in_(['medecin', 'veterinaire']),
        User.disponible_urgence == True
    ).all()
    
    return render_template('consultations/urgence.html',
                         title='Urgence',
                         medecins=medecins_urgence)

@bp.route('/ordonnance')
@login_required
def ordonnance():
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    # Récupérer les ordonnances du patient
    ordonnances = Consultation.query.filter(
        Consultation.patient_id == current_user.id,
        Consultation.ordonnance != None
    ).order_by(Consultation.date.desc()).all()
    
    return render_template('consultations/ordonnance.html',
                         title='Ordonnances',
                         ordonnances=ordonnances)

@bp.route('/documents')
@login_required
def documents():
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    # Récupérer les documents médicaux du patient
    documents = Consultation.query.filter(
        Consultation.patient_id == current_user.id,
        Consultation.documents != None
    ).order_by(Consultation.date.desc()).all()
    
    return render_template('consultations/documents.html',
                         title='Documents Médicaux',
                         documents=documents)

@bp.route('/ressources')
@login_required
def ressources():
    # Récupérer les ressources éducatives
    ressources = {
        'articles': [
            {'titre': 'Bien-être et santé', 'categorie': 'Santé générale'},
            {'titre': 'Nutrition équilibrée', 'categorie': 'Nutrition'},
            {'titre': 'Activité physique', 'categorie': 'Sport'}
        ],
        'videos': [
            {'titre': 'Exercices de relaxation', 'categorie': 'Bien-être'},
            {'titre': 'Conseils nutritionnels', 'categorie': 'Nutrition'}
        ]
    }
    
    return render_template('consultations/ressources.html',
                         title='Ressources Éducatives',
                         ressources=ressources)

@bp.route('/avis')
@login_required
def avis():
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    # Récupérer les consultations terminées pour lesquelles l'avis n'a pas encore été donné
    consultations_a_evaluer = Consultation.query.filter(
        Consultation.patient_id == current_user.id,
        Consultation.statut == 'terminee',
        Consultation.avis == None
    ).order_by(Consultation.date.desc()).all()
    
    # Récupérer les avis déjà donnés
    avis_donnes = Consultation.query.filter(
        Consultation.patient_id == current_user.id,
        Consultation.avis != None
    ).order_by(Consultation.date.desc()).all()
    
    return render_template('consultations/avis.html',
                         title='Avis & Évaluations',
                         consultations_a_evaluer=consultations_a_evaluer,
                         avis_donnes=avis_donnes)

@bp.route('/avis/<int:consultation_id>', methods=['POST'])
@login_required
def donner_avis(consultation_id):
    if current_user.role != 'patient':
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    consultation = Consultation.query.get_or_404(consultation_id)
    if consultation.patient_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    note = request.form.get('note')
    commentaire = request.form.get('commentaire')
    
    if not note or not commentaire:
        return jsonify({'error': 'Note et commentaire requis'}), 400
    
    consultation.avis = {
        'note': int(note),
        'commentaire': commentaire,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    db.session.commit()
    return jsonify({'success': True}) 