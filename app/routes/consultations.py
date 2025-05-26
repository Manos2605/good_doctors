from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.models import (
    Consultation, RendezVous, User, Message, DossierMedical,
    Vaccination, Examen, Traitement, DocumentMedical, SuiviPathologie,
    Ordonnance, Medicament
)
from app import db
import json

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
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
        
    if request.method == 'GET':
        medecin_id = request.args.get('medecin_id')
        date = request.args.get('date')
        
        if not medecin_id:
            flash('Médecin non spécifié', 'error')
            return redirect(url_for('consultations.recherche_medecin'))
            
        medecin = User.query.get_or_404(medecin_id)
        if medecin.role not in ['medecin', 'veterinaire']:
            flash('Utilisateur non autorisé', 'error')
            return redirect(url_for('consultations.recherche_medecin'))
            
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
                             title='Nouveau Rendez-vous',
                             medecin=medecin,
                             date=date,
                             creneaux=creneaux,
                             now=datetime.now())
                             
    elif request.method == 'POST':
        medecin_id = request.form.get('medecin_id')
        date_str = request.form.get('date')
        type_consultation = request.form.get('type')
        description = request.form.get('description')
        creneau_id = request.form.get('creneau_id')
        
        if not all([medecin_id, date_str, type_consultation, creneau_id]):
            flash('Tous les champs obligatoires doivent être remplis', 'error')
            return redirect(url_for('consultations.nouvelle', medecin_id=medecin_id))
            
        medecin = User.query.get_or_404(medecin_id)
        if medecin.role not in ['medecin', 'veterinaire']:
            flash('Utilisateur non autorisé', 'error')
            return redirect(url_for('consultations.recherche_medecin'))
        
        # Vérifier si le créneau est toujours disponible
        rendez_vous = RendezVous.query.get_or_404(creneau_id)
        if rendez_vous.statut != 'disponible' or rendez_vous.medecin_id != int(medecin_id):
            flash('Ce créneau n\'est plus disponible', 'error')
            return redirect(url_for('consultations.nouvelle', medecin_id=medecin_id))
            
        # Créer la consultation
        consultation = Consultation(
            patient_id=current_user.id,
            medecin_id=medecin_id,
            date=rendez_vous.date_debut,
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
            # Redirection vers la page des consultations avec un message de succès
            return redirect(url_for('consultations.index'))
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
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('consultations.index'))

    # Récupérer les rendez-vous à venir
    rendez_vous = RendezVous.query.join(Consultation).filter(
        Consultation.patient_id == current_user.id,
        RendezVous.date_debut >= datetime.now(),
        RendezVous.statut != 'annule'
    ).order_by(RendezVous.date_debut).all()

    # Récupérer l'historique des rendez-vous
    historique = RendezVous.query.join(Consultation).filter(
        Consultation.patient_id == current_user.id,
        RendezVous.date_debut < datetime.now()
    ).order_by(RendezVous.date_debut.desc()).all()

    # Calculer les statistiques
    stats = {
        'total_rdv': RendezVous.query.join(Consultation).filter(
            Consultation.patient_id == current_user.id,
            RendezVous.date_debut >= datetime(datetime.now().year, 1, 1)
        ).count(),
        'rdv_a_venir': len(rendez_vous),
        'taux_presence': 0,
        'praticiens_consultes': 0
    }

    # Calculer le taux de présence
    rdv_termines = RendezVous.query.join(Consultation).filter(
        Consultation.patient_id == current_user.id,
        RendezVous.statut == 'termine'
    ).count()
    rdv_annules = RendezVous.query.join(Consultation).filter(
        Consultation.patient_id == current_user.id,
        RendezVous.statut == 'annule'
    ).count()
    total_rdv = rdv_termines + rdv_annules
    if total_rdv > 0:
        stats['taux_presence'] = round((rdv_termines / total_rdv) * 100)

    # Compter le nombre de praticiens consultés
    stats['praticiens_consultes'] = db.session.query(RendezVous.medecin_id).join(Consultation).filter(
        Consultation.patient_id == current_user.id
    ).distinct().count()

    # Récupérer la liste des spécialités pour le formulaire
    specialites = db.session.query(User.specialite).filter(
        User.role.in_(['medecin', 'veterinaire'])
    ).distinct().all()
    specialites = [s[0] for s in specialites]

    return render_template('consultations/rendez_vous.html',
                         title='Gestion des Rendez-vous',
                         rendez_vous=rendez_vous,
                         historique=historique,
                         stats=stats,
                         specialites=specialites,
                         now=datetime.now())

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
                RendezVous.date_debut >= date_obj,
                RendezVous.date_debut < date_obj + timedelta(days=1),
                RendezVous.statut == 'reserve'
            ).count()
            
            # Vérifier les consultations existantes pour cette date
            consultations = Consultation.query.filter(
                Consultation.medecin_id == pro.id,
                Consultation.date >= date_obj,
                Consultation.date < date_obj + timedelta(days=1),
                Consultation.statut == 'planifiee'
            ).count()
            
            # Si moins de 8 rendez-vous/consultations pour cette date, le professionnel est disponible
            if rendez_vous + consultations < 8:
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

@bp.route('/ordonnances')
@login_required
def liste_ordonnances():
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
    dossier = DossierMedical.query.filter_by(patient_id=current_user.id).first()
    if not dossier:
        flash('Dossier médical non trouvé.', 'danger')
        return redirect(url_for('consultations.dossier_medical'))
    
    documents = DocumentMedical.query.filter_by(dossier_id=dossier.id).order_by(DocumentMedical.date_emission.desc()).all()
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

@bp.route('/dossier-medical')
@login_required
def dossier_medical():
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    dossier = DossierMedical.query.filter_by(patient_id=current_user.id).first()
    if not dossier:
        dossier = DossierMedical(patient_id=current_user.id)
        db.session.add(dossier)
        db.session.commit()
    
    return render_template('consultations/dossier_medical.html',
                         title='Dossier Médical',
                         dossier=dossier)

@bp.route('/dossier-medical/modifier', methods=['GET', 'POST'])
@login_required
def modifier_dossier_medical():
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    dossier = DossierMedical.query.filter_by(patient_id=current_user.id).first()
    if not dossier:
        dossier = DossierMedical(patient_id=current_user.id)
        db.session.add(dossier)
    
    if request.method == 'POST':
        dossier.groupe_sanguin = request.form.get('groupe_sanguin')
        dossier.electrophorese = request.form.get('electrophorese')
        dossier.antecedents_medicaux = request.form.get('antecedents_medicaux')
        dossier.antecedents_familiaux = request.form.get('antecedents_familiaux')
        dossier.allergies = request.form.get('allergies')
        
        db.session.commit()
        flash('Dossier médical mis à jour avec succès.', 'success')
        return redirect(url_for('consultations.dossier_medical'))
    
    return render_template('consultations/modifier_dossier_medical.html',
                         title='Modifier Dossier Médical',
                         dossier=dossier)

@bp.route('/vaccinations')
@login_required
def vaccinations():
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    dossier = DossierMedical.query.filter_by(patient_id=current_user.id).first()
    if not dossier:
        flash('Dossier médical non trouvé.', 'danger')
        return redirect(url_for('consultations.dossier_medical'))
    
    vaccinations = Vaccination.query.filter_by(dossier_id=dossier.id).order_by(Vaccination.date_vaccination.desc()).all()
    return render_template('consultations/vaccinations.html',
                         title='Vaccinations',
                         vaccinations=vaccinations)

@bp.route('/vaccinations/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_vaccination():
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        dossier = DossierMedical.query.filter_by(patient_id=current_user.id).first()
        if not dossier:
            flash('Dossier médical non trouvé.', 'danger')
            return redirect(url_for('consultations.dossier_medical'))
        
        vaccination = Vaccination(
            dossier_id=dossier.id,
            nom_vaccin=request.form.get('nom_vaccin'),
            date_vaccination=datetime.strptime(request.form.get('date_vaccination'), '%Y-%m-%d').date(),
            date_rappel=datetime.strptime(request.form.get('date_rappel'), '%Y-%m-%d').date() if request.form.get('date_rappel') else None,
            lot=request.form.get('lot'),
            notes=request.form.get('notes')
        )
        
        db.session.add(vaccination)
        db.session.commit()
        flash('Vaccination ajoutée avec succès.', 'success')
        return redirect(url_for('consultations.vaccinations'))
    
    return render_template('consultations/ajouter_vaccination.html',
                         title='Ajouter Vaccination')

@bp.route('/medicaments')
@login_required
def medicaments():
    medicaments = Medicament.query.all()
    return render_template('consultations/medicaments.html',
                         title='Médicaments',
                         medicaments=medicaments)

@bp.route('/medicaments/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_medicament():
    if current_user.role not in ['admin', 'medecin']:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        medicament = Medicament(
            nom=request.form.get('nom'),
            type=request.form.get('type'),
            description=request.form.get('description'),
            prix=float(request.form.get('prix')),
            stock=int(request.form.get('stock')),
            categorie=request.form.get('categorie'),
            effets_secondaires=request.form.get('effets_secondaires'),
            contre_indications=request.form.get('contre_indications'),
            date_expiration=datetime.strptime(request.form.get('date_expiration'), '%Y-%m-%d').date() if request.form.get('date_expiration') else None
        )
        
        # Gestion de l'image
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                medicament.image = filename
        
        db.session.add(medicament)
        db.session.commit()
        flash('Médicament ajouté avec succès.', 'success')
        return redirect(url_for('consultations.medicaments'))
    
    return render_template('consultations/ajouter_medicament.html',
                         title='Ajouter Médicament')

@bp.route('/ordonnance/<int:consultation_id>', methods=['GET', 'POST'])
@login_required
def ordonnance(consultation_id):
    consultation = Consultation.query.get_or_404(consultation_id)
    
    if current_user.role not in ['medecin', 'admin'] or current_user.id != consultation.medecin_id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        medicaments = request.form.getlist('medicaments[]')
        posologies = request.form.getlist('posologies[]')
        
        medicaments_list = []
        for med, poso in zip(medicaments, posologies):
            medicaments_list.append({
                'medicament': med,
                'posologie': poso
            })
        
        ordonnance = Ordonnance(
            consultation_id=consultation_id,
            medicaments=json.dumps(medicaments_list),
            instructions=request.form.get('instructions'),
            duree_validite=int(request.form.get('duree_validite'))
        )
        
        db.session.add(ordonnance)
        db.session.commit()
        flash('Ordonnance créée avec succès.', 'success')
        return redirect(url_for('consultations.consultation', id=consultation_id))
    
    medicaments = Medicament.query.all()
    return render_template('consultations/ordonnance.html',
                         title='Créer Ordonnance',
                         consultation=consultation,
                         medicaments=medicaments)

@bp.route('/carnet-medical')
@login_required
def carnet_medical():
    if current_user.role != 'patient':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    dossier = DossierMedical.query.filter_by(patient_id=current_user.id).first()
    if not dossier:
        dossier = DossierMedical(patient_id=current_user.id)
        db.session.add(dossier)
        db.session.commit()
    
    # Récupérer les vaccinations
    vaccinations = Vaccination.query.filter_by(dossier_id=dossier.id).order_by(Vaccination.date_vaccination.desc()).all()
    
    # Récupérer les consultations
    consultations = Consultation.query.filter_by(patient_id=current_user.id).order_by(Consultation.date.desc()).all()
    
    # Récupérer les traitements en cours
    traitements = Traitement.query.filter_by(dossier_id=dossier.id, statut='en_cours').all()
    
    # Récupérer les documents médicaux
    documents = DocumentMedical.query.filter_by(dossier_id=dossier.id).order_by(DocumentMedical.date_emission.desc()).all()
    
    # Récupérer les suivis de pathologies
    suivis = SuiviPathologie.query.filter_by(dossier_id=dossier.id).all()
    
    return render_template('consultations/carnet_medical.html',
                         title='Carnet Médical',
                         dossier=dossier,
                         vaccinations=vaccinations,
                         consultations=consultations,
                         traitements=traitements,
                         documents=documents,
                         suivis=suivis)

@bp.route('/medecin/creneaux', methods=['GET', 'POST'])
@login_required
def gerer_creneaux():
    if current_user.role not in ['medecin', 'veterinaire']:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        date_debut = datetime.strptime(request.form.get('date_debut'), '%Y-%m-%dT%H:%M')
        date_fin = datetime.strptime(request.form.get('date_fin'), '%Y-%m-%dT%H:%M')
        
        # Créer les créneaux de 30 minutes
        creneaux = []
        current_time = date_debut
        while current_time < date_fin:
            creneau = RendezVous(
                date_debut=current_time,
                date_fin=current_time + timedelta(minutes=30),
                medecin_id=current_user.id,
                statut='disponible'
            )
            creneaux.append(creneau)
            current_time += timedelta(minutes=30)
            
        try:
            db.session.add_all(creneaux)
            db.session.commit()
            flash(f'{len(creneaux)} créneaux créés avec succès', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Erreur lors de la création des créneaux', 'error')
            
        return redirect(url_for('consultations.gerer_creneaux'))
        
    # Récupérer les créneaux existants
    creneaux = RendezVous.query.filter_by(medecin_id=current_user.id).order_by(RendezVous.date_debut).all()
    
    return render_template('consultations/gerer_creneaux.html',
                         title='Gérer les créneaux',
                         creneaux=creneaux)

@bp.route('/medecin/creneaux/<int:id>/supprimer', methods=['POST'])
@login_required
def supprimer_creneau(id):
    if current_user.role not in ['medecin', 'veterinaire']:
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    creneau = RendezVous.query.get_or_404(id)
    if creneau.medecin_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    if creneau.statut != 'disponible':
        return jsonify({'error': 'Impossible de supprimer un créneau réservé'}), 400
        
    try:
        db.session.delete(creneau)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erreur lors de la suppression'}), 500

@bp.route('/creer-medecins-test')
def creer_medecins_test():
    # Vérifier si les médecins existent déjà
    medecin1 = User.query.filter_by(email='dr.martin@meditech.com').first()
    medecin2 = User.query.filter_by(email='dr.bernard@meditech.com').first()
    
    if not medecin1:
        medecin1 = User(
            email='dr.martin@meditech.com',
            nom='Martin',
            prenom='Sophie',
            role='medecin',
            specialite='Médecine générale',
            password='password123',
            telephone='0123456789',
            disponible_urgence=True
        )
        db.session.add(medecin1)
    
    if not medecin2:
        medecin2 = User(
            email='dr.bernard@meditech.com',
            nom='Bernard',
            prenom='Pierre',
            role='medecin',
            specialite='Cardiologie',
            password='password123',
            telephone='0987654321',
            disponible_urgence=True
        )
        db.session.add(medecin2)
    
    try:
        db.session.commit()
        flash('Médecins de test créés avec succès', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la création des médecins de test', 'error')
    
    return redirect(url_for('consultations.recherche_medecin'))

@bp.route('/api/medecins/<specialite>')
@login_required
def get_medecins(specialite):
    if current_user.role != 'patient':
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    medecins = User.query.filter(
        User.role.in_(['medecin', 'veterinaire']),
        User.specialite == specialite
    ).all()
    
    return jsonify([{
        'id': medecin.id,
        'nom': medecin.nom,
        'prenom': medecin.prenom,
        'rating': medecin.rating if hasattr(medecin, 'rating') else 0
    } for medecin in medecins])

@bp.route('/api/calendrier/<int:year>/<int:month>')
@login_required
def get_calendrier(year, month):
    if current_user.role != 'patient':
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    # Récupérer tous les jours du mois
    import calendar
    cal = calendar.monthcalendar(year, month)
    jours = []
    
    for week in cal:
        for day in week:
            if day != 0:
                date = datetime(year, month, day)
                # Vérifier si le jour est disponible (pas de congés, pas complet)
                disponible = True
                if date < datetime.now():
                    disponible = False
                else:
                    # Vérifier le nombre de rendez-vous pour ce jour
                    rdv_count = RendezVous.query.filter(
                        RendezVous.date_debut >= date,
                        RendezVous.date_debut < date + timedelta(days=1),
                        RendezVous.statut == 'reserve'
                    ).count()
                    if rdv_count >= 8:  # Maximum 8 rendez-vous par jour
                        disponible = False
                
                jours.append({
                    'jour': day,
                    'disponible': disponible
                })
    
    return jsonify(jours)

@bp.route('/api/creneaux/<date>')
@login_required
def get_creneaux(date):
    if current_user.role != 'patient':
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Format de date invalide'}), 400
        
    # Générer les créneaux de 30 minutes de 9h à 18h
    creneaux = []
    debut = datetime.combine(date_obj.date(), datetime.min.time().replace(hour=9))
    fin = datetime.combine(date_obj.date(), datetime.min.time().replace(hour=18))
    
    current = debut
    while current < fin:
        # Vérifier si le créneau est disponible
        rdv = RendezVous.query.filter(
            RendezVous.date_debut == current,
            RendezVous.statut == 'reserve'
        ).first()
        
        creneaux.append({
            'heure': current.strftime('%H:%M'),
            'disponible': rdv is None
        })
        
        current += timedelta(minutes=30)
    
    return jsonify(creneaux)

@bp.route('/api/rendez-vous/<int:id>/reporter', methods=['POST'])
@login_required
def reporter_rendez_vous(id):
    if current_user.role != 'patient':
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    rdv = RendezVous.query.get_or_404(id)
    if rdv.consultation and rdv.consultation.patient_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    # Libérer l'ancien créneau
    rdv.statut = 'disponible'
    rdv.consultation = None
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/rendez-vous/<int:id>/annuler', methods=['POST'])
@login_required
def annuler_rendez_vous(id):
    if current_user.role != 'patient':
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    rdv = RendezVous.query.get_or_404(id)
    if rdv.consultation and rdv.consultation.patient_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    # Annuler le rendez-vous
    rdv.statut = 'annule'
    if rdv.consultation:
        rdv.consultation.statut = 'annulee'
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/rendez-vous/<int:id>')
@login_required
def get_rendez_vous_details(id):
    if current_user.role != 'patient':
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    rdv = RendezVous.query.get_or_404(id)
    if rdv.consultation and rdv.consultation.patient_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    details = {
        'date': rdv.date_debut.strftime('%d/%m/%Y'),
        'heure': rdv.date_debut.strftime('%H:%M'),
        'medecin': f"Dr. {rdv.medecin.prenom} {rdv.medecin.nom}",
        'specialite': rdv.medecin.specialite,
        'statut': rdv.statut
    }
    
    if rdv.consultation:
        details.update({
            'type': rdv.consultation.type,
            'description': rdv.consultation.description
        })
    
    return jsonify({'details': details})

@bp.route('/api/rendez-vous/<int:id>/reprendre')
@login_required
def reprendre_rendez_vous(id):
    if current_user.role != 'patient':
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    rdv = RendezVous.query.get_or_404(id)
    if rdv.consultation and rdv.consultation.patient_id != current_user.id:
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    return jsonify({
        'success': True,
        'medecin_id': rdv.medecin_id,
        'specialite': rdv.medecin.specialite
    })

@bp.route('/api/rendez-vous/historique/<filter>')
@login_required
def get_historique(filter):
    if current_user.role != 'patient':
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    query = RendezVous.query.join(Consultation).filter(
        Consultation.patient_id == current_user.id
    )
    
    if filter == 'completed':
        query = query.filter(RendezVous.statut == 'termine')
    elif filter == 'cancelled':
        query = query.filter(RendezVous.statut == 'annule')
    
    rdvs = query.order_by(RendezVous.date_debut.desc()).all()
    
    return jsonify([{
        'id': rdv.id,
        'date': rdv.date_debut.strftime('%d/%m/%Y'),
        'heure': rdv.date_debut.strftime('%H:%M'),
        'medecin': f"Dr. {rdv.medecin.prenom} {rdv.medecin.nom}",
        'specialite': rdv.medecin.specialite,
        'statut': rdv.statut,
        'type': rdv.consultation.type if rdv.consultation else None
    } for rdv in rdvs])

@bp.route('/api/rendez-vous/recherche/<term>')
@login_required
def rechercher_rendez_vous(term):
    if current_user.role != 'patient':
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    rdvs = RendezVous.query.join(Consultation).filter(
        Consultation.patient_id == current_user.id,
        or_(
            User.nom.ilike(f'%{term}%'),
            User.prenom.ilike(f'%{term}%'),
            User.specialite.ilike(f'%{term}%'),
            Consultation.type.ilike(f'%{term}%')
        )
    ).order_by(RendezVous.date_debut.desc()).all()
    
    return jsonify([{
        'id': rdv.id,
        'date': rdv.date_debut.strftime('%d/%m/%Y'),
        'heure': rdv.date_debut.strftime('%H:%M'),
        'medecin': f"Dr. {rdv.medecin.prenom} {rdv.medecin.nom}",
        'specialite': rdv.medecin.specialite,
        'statut': rdv.statut,
        'type': rdv.consultation.type if rdv.consultation else None
    } for rdv in rdvs]) 