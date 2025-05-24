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
    
    # Relations
    consultations_medecin = db.relationship('Consultation', backref='medecin', lazy='dynamic', foreign_keys='Consultation.medecin_id')
    consultations_patient = db.relationship('Consultation', backref='patient', lazy='dynamic', foreign_keys='Consultation.patient_id')
    messages_envoyes = db.relationship('Message', backref='expediteur', lazy='dynamic', foreign_keys='Message.expediteur_id')
    messages_recus = db.relationship('Message', backref='destinataire', lazy='dynamic', foreign_keys='Message.destinataire_id')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

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