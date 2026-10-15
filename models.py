from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # Rôles possibles : 'directeur', 'enseignant', 'comptable', 'personnel'
    role = db.Column(db.String(50), nullable=False, default='enseignant')

    # Statut du compte : False = En attente de validation par le directeur, True = Actif
    is_active_account = db.Column(db.Boolean, default=False)

    matiere_fonction = db.Column(db.String(150), nullable=True)  # Matière enseignée ou fonction

    # Relations
    courses = db.relationship('Course', backref='enseignant', lazy=True)

    def get_id(self):
        return str(self.id)


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    jour = db.Column(db.String(20), nullable=False)  # Ex: Lundi, Mardi...
    heure_debut = db.Column(db.String(10), nullable=False)  # Ex: '08:00'
    heure_fin = db.Column(db.String(10), nullable=False)  # Ex: '10:00'
    classe = db.Column(db.String(50), nullable=False)  # Ex: '6ème A'
    matiere = db.Column(db.String(100), nullable=False)

    # Statut de l'emploi du temps : False = En attente / Proposition, True = Approuvé par le directeur
    is_approved = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)


class Attendance(db.Model):
    __tablename__ = 'attendances'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    heure_pointage = db.Column(db.Time, nullable=False)  # Heure d'arrivée
    heure_fin = db.Column(db.Time, nullable=True)  # Heure de départ / sortie

    # Statuts : 'Ponctuel', 'En retard', 'Absent'
    statut = db.Column(db.String(50), nullable=False, default='Ponctuel')

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relation inverse avec User (permet d'accéder à att.user et user.attendances)
    user = db.relationship('User', backref=db.backref('attendances', lazy=True))


# ⚠️ Correctement replacé au même niveau que les autres classes (hors de Attendance)
class DemandeConge(db.Model):
    __tablename__ = 'demandes_conge'

    id = db.Column(db.Integer, primary_key=True)
    prof_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type_demande = db.Column(db.String(50), nullable=False)  # ex: Permission, Congé maladie, etc.
    date_debut = db.Column(db.String(20), nullable=False)
    date_fin = db.Column(db.String(20), nullable=False)
    motif = db.Column(db.Text, nullable=False)
    statut = db.Column(db.String(20), default='En attente')  # En attente, Approuvé, Refusé
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    prof = db.relationship('User', backref=db.backref('demandes_conge', lazy=True))