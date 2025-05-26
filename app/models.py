from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'medecin', 'veterinaire', 'patient'
    specialite = db.Column(db.String(100))  # Pour les médecins et vétérinaires
    telephone = db.Column(db.String(20))
    adresse = db.Column(db.String(200))
    bio = db.Column(db.Text)
    date_inscription = db.Column(db.DateTime, default=datetime.utcnow)
    date_naissance = db.Column(db.Date)
    sexe = db.Column(db.String(10))  # 'M', 'F', 'Autre'
    contact_urgence = db.Column(db.String(200))
    disponible_urgence = db.Column(db.Boolean, default=False)
    
    # Relations
    consultations_medecin = db.relationship('Consultation', backref='medecin', lazy='dynamic', foreign_keys='Consultation.medecin_id')
    consultations_patient = db.relationship('Consultation', backref='patient', lazy='dynamic', foreign_keys='Consultation.patient_id')
    messages_envoyes = db.relationship('Message', backref='expediteur', lazy='dynamic', foreign_keys='Message.expediteur_id')
    messages_recus = db.relationship('Message', backref='destinataire', lazy='dynamic', foreign_keys='Message.destinataire_id')
    dossier_medical = db.relationship('DossierMedical', backref='patient', uselist=False, foreign_keys='DossierMedical.patient_id')
    dossiers_referents = db.relationship('DossierMedical', backref='medecin_referent', lazy='dynamic', foreign_keys='DossierMedical.medecin_referent_id')
    rendez_vous = db.relationship('RendezVous', backref='medecin', lazy='dynamic')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class DossierMedical(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    medecin_referent_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    groupe_sanguin = db.Column(db.String(5))  # A+, B-, AB+, O-, etc.
    electrophorese = db.Column(db.String(100))
    antecedents_medicaux = db.Column(db.Text)
    antecedents_familiaux = db.Column(db.Text)
    allergies = db.Column(db.Text)
    
    # Relations
    vaccinations = db.relationship('Vaccination', backref='dossier_medical', lazy='dynamic')
    examens = db.relationship('Examen', backref='dossier_medical', lazy='dynamic')
    traitements = db.relationship('Traitement', backref='dossier_medical', lazy='dynamic')
    documents = db.relationship('DocumentMedical', backref='dossier_medical', lazy='dynamic')
    suivis = db.relationship('SuiviPathologie', backref='dossier_medical', lazy='dynamic')

class Vaccination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossier_medical.id'), nullable=False)
    nom_vaccin = db.Column(db.String(100), nullable=False)
    date_vaccination = db.Column(db.Date, nullable=False)
    date_rappel = db.Column(db.Date)
    lot = db.Column(db.String(50))
    medecin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.Text)

class Examen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossier_medical.id'), nullable=False)
    type_examen = db.Column(db.String(100), nullable=False)  # Radio, IRM, Analyse sanguine, etc.
    date_examen = db.Column(db.Date, nullable=False)
    resultat = db.Column(db.Text)
    medecin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    fichier_resultat = db.Column(db.String(200))  # Chemin vers le fichier stocké

class Traitement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossier_medical.id'), nullable=False)
    medicament = db.Column(db.String(200), nullable=False)
    posologie = db.Column(db.String(200))
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date)
    medecin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    effets_secondaires = db.Column(db.Text)
    statut = db.Column(db.String(20), default='en_cours')  # en_cours, termine, interrompu

class DocumentMedical(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossier_medical.id'), nullable=False)
    type_document = db.Column(db.String(50), nullable=False)  # Ordonnance, Certificat, etc.
    date_emission = db.Column(db.Date, nullable=False)
    medecin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    fichier = db.Column(db.String(200))  # Chemin vers le fichier stocké
    description = db.Column(db.Text)

class SuiviPathologie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dossier_id = db.Column(db.Integer, db.ForeignKey('dossier_medical.id'), nullable=False)
    type_pathologie = db.Column(db.String(100), nullable=False)  # Diabète, Hypertension, etc.
    date_mesure = db.Column(db.DateTime, nullable=False)
    valeur = db.Column(db.Float)
    unite = db.Column(db.String(20))  # mg/dL, mmHg, etc.
    notes = db.Column(db.Text)

class Consultation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    duree = db.Column(db.Integer, nullable=False)  # Durée en minutes
    type = db.Column(db.String(20), nullable=False)  # 'video', 'chat', 'message'
    statut = db.Column(db.String(20), nullable=False, default='planifiee')  # 'planifiee', 'en_cours', 'terminee', 'annulee'
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    lien_video = db.Column(db.String(200))  # Pour les consultations vidéo
    
    # Relations
    medecin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    messages = db.relationship('Message', backref='consultation', lazy='dynamic')
    ordonnance = db.relationship('Ordonnance', backref='consultation', uselist=False)

class Ordonnance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(db.Integer, db.ForeignKey('consultation.id'), nullable=False)
    date_emission = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    medicaments = db.Column(db.Text, nullable=False)  # Format JSON pour stocker la liste des médicaments
    instructions = db.Column(db.Text)
    duree_validite = db.Column(db.Integer)  # Durée en jours

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contenu = db.Column(db.Text, nullable=False)
    date_envoi = db.Column(db.DateTime, default=datetime.utcnow)
    lu = db.Column(db.Boolean, default=False)
    
    # Relations
    expediteur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    destinataire_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    consultation_id = db.Column(db.Integer, db.ForeignKey('consultation.id'))

class RendezVous(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_debut = db.Column(db.DateTime, nullable=False)
    date_fin = db.Column(db.DateTime, nullable=False)
    statut = db.Column(db.String(20), nullable=False, default='disponible')  # 'disponible', 'reserve', 'annule'
    
    # Relations
    medecin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    consultation_id = db.Column(db.Integer, db.ForeignKey('consultation.id'))

class Medicament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'africain', 'moderne'
    description = db.Column(db.Text)
    prix = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    image = db.Column(db.String(200))  # Chemin vers l'image du médicament
    categorie = db.Column(db.String(100))  # Catégorie thérapeutique
    effets_secondaires = db.Column(db.Text)
    contre_indications = db.Column(db.Text)
    date_expiration = db.Column(db.Date) 