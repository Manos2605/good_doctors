from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db
import re

bp = Blueprint('auth', __name__)

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    # Au moins 8 caractères, une majuscule, une minuscule et un chiffre
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        remember = request.form.get('remember', False)
        
        # Validation des champs
        if not email or not password:
            flash('Tous les champs sont obligatoires.', 'danger')
            return redirect(url_for('auth.login'))
            
        if not validate_email(email):
            flash('Format d\'email invalide.', 'danger')
            return redirect(url_for('auth.login'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
            return redirect(next_page)
            
        flash('Email ou mot de passe incorrect.', 'danger')
        
    return render_template('auth/login.html', title='Connexion')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        telephone = request.form.get('telephone', '').strip()
        adresse = request.form.get('adresse', '').strip()
        
        # Validation des champs obligatoires
        if not all([email, password, confirm_password, nom, prenom, telephone, adresse]):
            flash('Tous les champs sont obligatoires.', 'danger')
            return redirect(url_for('auth.register'))
            
        # Validation de l'email
        if not validate_email(email):
            flash('Format d\'email invalide.', 'danger')
            return redirect(url_for('auth.register'))
            
        # Validation du mot de passe
        if not validate_password(password):
            flash('Le mot de passe doit contenir au moins 8 caractères, une majuscule, une minuscule et un chiffre.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Vérifier si l'email existe déjà
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect(url_for('auth.register'))
            
        # Vérifier si les mots de passe correspondent
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('auth.register'))
            
        try:
            # Créer le nouvel utilisateur avec le rôle patient
            user = User(
                email=email,
                nom=nom,
                prenom=prenom,
                role='patient',  # Forcer le rôle patient
                telephone=telephone,
                adresse=adresse
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # Connecter automatiquement l'utilisateur
            login_user(user, remember=True)
            
            flash('Votre compte a été créé avec succès!', 'success')
            
            # Rediriger vers le dashboard
            return redirect(url_for('consultations.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash('Une erreur est survenue lors de la création du compte.', 'danger')
            return redirect(url_for('auth.register'))
        
    return render_template('auth/register.html', title='Inscription')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login')) 