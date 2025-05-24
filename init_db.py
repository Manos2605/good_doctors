from app import create_app, db
from app.models import User

app = create_app()

def create_test_users():
    with app.app_context():
        # Supprimer toutes les tables existantes
        db.drop_all()
        # Créer toutes les tables
        db.create_all()
        
        users = [
            {
                'email': 'sonwadimitry26@gmail.com',
                'password': '1234',
                'nom': 'Admin',
                'prenom': 'System',
                'role': 'admin'
            },
            {
                'email': 'dr.dupont@gooddoctors.com',
                'password': 'medecin123',
                'nom': 'Dupont',
                'prenom': 'Jean',
                'role': 'medecin',
                'specialite': 'Médecine générale',
                'telephone': '0123456789',
                'adresse': '123 rue de la Santé, Paris',
                'bio': 'Médecin généraliste avec 15 ans d\'expérience'
            },
            {
                'email': 'dr.martin@gooddoctors.com',
                'password': 'vet123',
                'nom': 'Martin',
                'prenom': 'Sophie',
                'role': 'veterinaire',
                'specialite': 'Vétérinaire canin',
                'telephone': '0987654321',
                'adresse': '456 avenue des Animaux, Lyon',
                'bio': 'Vétérinaire spécialisée dans les soins canins'
            },
            {
                'email': 'patient@example.com',
                'password': 'patient123',
                'nom': 'Patient',
                'prenom': 'Test',
                'role': 'patient',
                'telephone': '0123456789',
                'adresse': '789 rue du Patient, Marseille'
            }
        ]

        for user_data in users:
            user = User(
                email=user_data['email'],
                nom=user_data['nom'],
                prenom=user_data['prenom'],
                role=user_data['role']
            )
            if 'specialite' in user_data:
                user.specialite = user_data['specialite']
            if 'telephone' in user_data:
                user.telephone = user_data['telephone']
            if 'adresse' in user_data:
                user.adresse = user_data['adresse']
            if 'bio' in user_data:
                user.bio = user_data['bio']
            
            user.set_password(user_data['password'])
            db.session.add(user)
            print(f'Utilisateur {user_data["email"]} créé avec succès!')
        
        db.session.commit()

if __name__ == '__main__':
    create_test_users() 