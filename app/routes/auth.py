from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
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
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        role = request.form.get('role')
        telephone = request.form.get('telephone')
        adresse = request.form.get('adresse')
        
        # Vérifier si l'email existe déjà
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect(url_for('auth.register'))
            
        # Vérifier si les mots de passe correspondent
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('auth.register'))
            
        # Créer le nouvel utilisateur
        user = User(
            email=email,
            nom=nom,
            prenom=prenom,
            role=role,
            telephone=telephone,
            adresse=adresse
        )
        user.set_password(password)
        
        # Si c'est un médecin ou un vétérinaire, ajouter la spécialité
        if role in ['medecin', 'veterinaire']:
            user.specialite = request.form.get('specialite')
            
        db.session.add(user)
        db.session.commit()
        
        flash('Votre compte a été créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', title='Inscription')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login')) 