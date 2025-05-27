from app import create_app, db
from app.models import User, DossierMedical, Vaccination, Examen, Traitement, DocumentMedical, SuiviPathologie, Consultation, Ordonnance, Message, RendezVous, Medicament
from datetime import date

app = create_app()

with app.app_context():
    # Créer toutes les tables
    db.create_all()
        
    # Vérifier si l'admin existe déjà
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        # Créer un utilisateur admin
        admin = User(
            email='admin@example.com',
            nom='Admin',
            prenom='System',
            role='admin',
            telephone='0123456789'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Créer un médecin de test
        medecin = User(
            email='medecin@example.com',
            nom='Dupont',
            prenom='Jean',
            role='medecin',
            specialite='Médecine générale',
            telephone='0123456789'
        )
        medecin.set_password('medecin123')
        db.session.add(medecin)
        
        # Créer des médecins camerounais
        medecins_camerounais = [
            User(
                email='nkengue@example.com',
                nom='Nkengue',
                prenom='François',
                role='medecin',
                specialite='Cardiologie',
                telephone='237612345678'
            ),
            User(
                email='tchokouani@example.com',
                nom='Tchokouani',
                prenom='Marie-Claire',
                role='medecin',
                specialite='Pédiatrie',
                telephone='237623456789'
            ),
            User(
                email='mboua@example.com',
                nom='Mboua',
                prenom='Jean-Pierre',
                role='medecin',
                specialite='Dermatologie',
                telephone='237634567890'
            ),
            User(
                email='nguimfack@example.com',
                nom='Nguimfack',
                prenom='Aurélie',
                role='medecin',
                specialite='Gynécologie',
                telephone='237645678901'
            ),
            User(
                email='kamga@example.com',
                nom='Kamga',
                prenom='Samuel',
                role='medecin',
                specialite='Neurologie',
                telephone='237656789012'
            )
        ]
        
        for med in medecins_camerounais:
            med.set_password('medecin123')
            db.session.add(med)
        
        # Créer un patient de test
        patient = User(
            email='patient@example.com',
            nom='Martin',
            prenom='Marie',
            role='patient',
            telephone='0123456789',
            date_naissance=date(1990, 1, 1),
            sexe='F'
        )
        patient.set_password('patient123')
        db.session.add(patient)
        
        # Créer un dossier médical pour le patient
        dossier = DossierMedical(
            patient=patient,
            medecin_referent=medecin,
            groupe_sanguin='A+',
            allergies='Aucune allergie connue',
            antecedents_medicaux='Aucun antécédent médical',
            antecedents_familiaux='Aucun antécédent familial'
        )
        db.session.add(dossier)
        
        # Créer quelques médicaments de test
        medicaments = [
            Medicament(
                nom='Paracétamol',
                type='moderne',
                description='Antidouleur et antipyrétique',
                prix=2500,
                stock=100,
                categorie='Antalgique',
                effets_secondaires='Rarement des réactions allergiques',
                contre_indications='Insuffisance hépatique'
            ),
            Medicament(
                nom='Artemisia',
                type='africain',
                description='Plante médicinale traditionnelle',
                prix=5500,
                stock=50,
                categorie='Antipaludique',
                effets_secondaires='Aucun effet secondaire connu',
                contre_indications='Grossesse'
            )
        ]
        db.session.add_all(medicaments)
        
        db.session.commit()
        print("Base de données initialisée avec succès !")
    else:
        print("La base de données est déjà initialisée.") 