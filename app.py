import qrcode
import io
import base64
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import extract
from config import Config
from models import db, User, Course, Attendance, DemandeConge

app = Flask(__name__)
app.config.from_object(Config)

# Initialisation de la base de données et de Flask-Login
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Création automatique des tables et du compte Directeur principal uniquement
with app.app_context():
    db.create_all()

    admin_user = User.query.filter_by(role='directeur').first()
    if not admin_user:
        hashed_password = generate_password_hash('admin123', method='pbkdf2:sha256')
        default_admin = User(
            nom='Directeur',
            prenom='Principal',
            email='admin@boyajc.com',
            password_hash=hashed_password,
            role='directeur',
            is_active_account=True,
            matiere_fonction='Administration Générale'
        )
        db.session.add(default_admin)
        db.session.commit()
        print("Compte Directeur par défaut créé : admin@boyajc.com / admin123")


# --- ACCUEIL & AUTHENTIFICATION ---
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'enseignant')

        # Gestion dynamique du champ selon le rôle
        if role == 'enseignant':
            matiere_fonction = request.form.get('matiere')
        elif role == 'personnel':
            matiere_fonction = request.form.get('fonction')
        else:
            matiere_fonction = 'Comptabilité & Gestion'  # Pour le comptable

        # Vérifier si l'email existe déjà
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Cet email est déjà utilisé par un autre compte.", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(
            nom=nom,
            prenom=prenom,
            email=email,
            password_hash=hashed_password,
            role=role,
            is_active_account=False,  # En attente de validation par le directeur
            matiere_fonction=matiere_fonction
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Inscription réussie ! Votre compte est en attente de validation par la direction.", "warning")
        return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            if not user.is_active_account:
                flash("Votre compte est en attente de validation par la direction.", "warning")
                return redirect(url_for('login'))

            login_user(user)

            # Nettoyage et mise en minuscules pour être 100% sûr
            role = str(user.role).strip().lower()

            flash(f"Connexion réussie en tant que : {role}", "success")

            if role == 'directeur':
                return redirect(url_for('directeur_dashboard'))
            elif role == 'comptable':
                return redirect(url_for('comptable_dashboard'))
            else:
                return redirect(url_for('prof_dashboard'))
        else:
            flash("Email ou mot de passe incorrect.", "danger")

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()  # Déconnecte l'utilisateur
    flash("Vous avez été déconnecté avec succès.", "info")
    return redirect(url_for('home'))  # Redirige directement vers la page d'accueil


# --- TABLEAUX DE BORD DIRECTION ---
@app.route('/directeur/dashboard')
@login_required
def directeur_dashboard():
    if current_user.role != 'directeur':
        return redirect(url_for('login'))

    total_users = User.query.count()
    pending_users = User.query.filter_by(is_active_account=False).count()
    total_courses = Course.query.count()
    total_attendances = Attendance.query.count()

    return render_template('directeur/dashboard.html',
                           total_users=total_users,
                           pending_users=pending_users,
                           total_courses=total_courses,
                           total_attendances=total_attendances)


@app.route('/directeur/users')
@login_required
def directeur_users():
    if current_user.role != 'directeur':
        return redirect(url_for('login'))

    users = User.query.all()
    return render_template('directeur/manage_users.html', users=users)


@app.route('/directeur/user/toggle/<int:user_id>')
@login_required
def toggle_user(user_id):
    if current_user.role != 'directeur':
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Vous ne pouvez pas modifier votre propre statut administrateur.", "danger")
        return redirect(url_for('directeur_users'))

    user.is_active_account = not user.is_active_account
    db.session.commit()

    status_msg = "activé" if user.is_active_account else "désactivé"
    flash(f"Le compte de {user.prenom} {user.nom} a été {status_msg}.", "success")
    return redirect(url_for('directeur_users'))


@app.route('/directeur/cours', methods=['GET', 'POST'])
@login_required
def directeur_cours():
    if current_user.role != 'directeur':
        flash("Accès réservé au directeur.", "danger")
        return redirect(url_for('login'))

    enseignants = User.query.filter_by(role='enseignant', is_active_account=True).all()

    if request.method == 'POST':
        titre = request.form.get('titre')
        description = request.form.get('description')
        jour = request.form.get('jour')
        heure_debut = request.form.get('heure_debut')
        heure_fin = request.form.get('heure_fin')
        enseignant_id = request.form.get('enseignant_id')

        if not titre or not jour or not heure_debut or not heure_fin:
            flash("Veuillez remplir tous les champs obligatoires.", "warning")
        else:
            nouveau_cours = Course(
                titre=titre,
                description=description,
                jour=jour,
                heure_debut=heure_debut,
                heure_fin=heure_fin,
                enseignant_id=enseignant_id if enseignant_id else None
            )
            db.session.add(nouveau_cours)
            db.session.commit()
            flash("Cours planifié avec succès !", "success")
            return redirect(url_for('directeur_cours'))

    courses = Course.query.all()
    return render_template('directeur/cours.html', courses=courses, enseignants=enseignants)


@app.route('/directeur/cours/supprimer/<int:course_id>', methods=['POST'])
@login_required
def supprimer_cours(course_id):
    if current_user.role != 'directeur':
        return redirect(url_for('login'))

    cours = Course.query.get_or_404(course_id)
    db.session.delete(cours)
    db.session.commit()
    flash("Le cours a été supprimé avec succès.", "success")
    return redirect(url_for('directeur_cours'))


@app.route('/directeur/pointages')
@login_required
def directeur_pointages():
    if current_user.role != 'directeur':
        flash("Accès réservé au directeur.", "danger")
        return redirect(url_for('login'))

    selected_date = request.args.get('date')       # YYYY-MM-DD
    selected_mois = request.args.get('mois')       # MM
    selected_annee = request.args.get('annee')     # YYYY

    query = Attendance.query

    if selected_date:
        query = query.filter(Attendance.date == selected_date)
    if selected_mois:
        query = query.filter(extract('month', Attendance.date) == int(selected_mois))
    if selected_annee:
        query = query.filter(extract('year', Attendance.date) == int(selected_annee))

    attendances = query.order_by(Attendance.date.desc(), Attendance.heure_pointage.desc()).all()

    return render_template('directeur/pointages.html',
                           attendances=attendances,
                           selected_date=selected_date,
                           selected_mois=selected_mois,
                           selected_annee=selected_annee)


# --- MODULE ENSEIGNANT / PERSONNEL ---
@app.route('/prof/dashboard')
@login_required
def prof_dashboard():
    if current_user.role not in ['enseignant', 'personnel']:
        return redirect(url_for('login'))
    return render_template('prof/dashboard.html')


@app.route('/display/qr')
def display_qr():
    current_time_slot = int(time.time() // 30)
    qr_data = f"BOYA_JC_POINTAGE_{current_time_slot}"

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)

    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template('display/dynamic_qr.html', qr_b64=qr_b64, token=qr_data)


@app.route('/prof/scan', methods=['GET', 'POST'])
@login_required
def prof_scan():
    if current_user.role not in ['enseignant', 'personnel']:
        flash("Accès réservé au personnel et enseignants.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        scanned_token = request.form.get('qr_code')

        if scanned_token and scanned_token.startswith("BOYA_JC_POINTAGE_"):
            now = datetime.now()
            today = now.date()

            # Jours en français pour la correspondance avec la base de données
            jours_fr = {
                0: 'Lundi', 1: 'Mardi', 2: 'Mercredi',
                3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'
            }
            jour_actuel = jours_fr[now.weekday()]

            # 1. Vérifier s'il y a déjà un pointage pour aujourd'hui
            attendance_today = Attendance.query.filter_by(
                user_id=current_user.id,
                date=today
            ).order_by(Attendance.id.desc()).first()

            # --- POINTAGE D'ARRIVÉE ---
            if not attendance_today or attendance_today.heure_fin is not None:

                # Recherche du cours correspondant à l'enseignant pour aujourd'hui
                cours_prevu = Course.query.filter(
                    Course.user_id == current_user.id,
                    Course.jour == jour_actuel
                ).first()

                # Calcul du statut (Ponctuel / Retard)
                if cours_prevu and cours_prevu.heure_debut:
                    statut_calcule = calculer_statut_retard(now.time(), cours_prevu.heure_debut)
                else:
                    statut_calcule = "Ponctuel"

                new_attendance = Attendance(
                    date=today,
                    heure_pointage=now.time(),
                    statut=statut_calcule,
                    user_id=current_user.id
                )
                db.session.add(new_attendance)
                db.session.commit()

                # Message personnalisé avec le statut
                if "Retard" in statut_calcule:
                    flash(f"Pointage d'ARRIVÉE enregistré à {now.strftime('%H:%M:%S')} ({statut_calcule}).", "warning")
                else:
                    flash(f"Pointage d'ARRIVÉE réussi à {now.strftime('%H:%M:%S')} ! Vous êtes ponctuel.", "success")

            # --- POINTAGE DE SORTIE ---
            elif attendance_today and attendance_today.heure_fin is None:
                attendance_today.heure_fin = now.time()
                db.session.commit()
                flash(f"Pointage de SORTIE réussi à {now.strftime('%H:%M:%S')} !", "success")

            return redirect(url_for('prof_dashboard'))
        else:
            flash("QR Code invalide ou expiré.", "danger")

    return render_template('prof/scanner.html')


# --- MODULE COMPTABILITÉ & RAPPORTS ---
@app.route('/comptable/dashboard')
@login_required
def comptable_dashboard():
    if current_user.role != 'comptable':
        flash("Accès réservé au comptable.", "danger")
        return redirect(url_for('login'))

    attendances = Attendance.query.order_by(Attendance.date.desc()).all()
    return render_template('comptable/dashboard.html', attendances=attendances)


@app.route('/comptable/export-pdf')
@login_required
def comptable_export_pdf():
    if current_user.role not in ['comptable', 'directeur']:
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('login'))

    attendances = Attendance.query.order_by(Attendance.date.desc(), Attendance.heure_pointage.desc()).all()
    return render_template('comptable/export_pdf.html', attendances=attendances)


@app.route('/prof/emploi-du-temps', methods=['GET', 'POST'])
@login_required
def prof_schedule():
    if current_user.role not in ['enseignant', 'prof']:
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        jour = request.form.get('jour')
        matiere = request.form.get('matiere')
        classe = request.form.get('classe')
        heure_debut = request.form.get('heure_debut')
        heure_fin = request.form.get('heure_fin')

        if not (jour and matiere and heure_debut and heure_fin):
            flash("Veuillez remplir tous les champs obligatoires.", "warning")
        else:
            new_course = Course(
                user_id=current_user.id,
                jour=jour,
                matiere=matiere,
                classe=classe,
                heure_debut=heure_debut,
                heure_fin=heure_fin
            )
            db.session.add(new_course)
            db.session.commit()
            flash("Créneau ajouté avec succès à votre emploi du temps !", "success")
            return redirect(url_for('prof_schedule'))

    user_courses = Course.query.filter_by(user_id=current_user.id).order_by(Course.jour).all()
    return render_template('prof/emploi_du_temps.html', courses=user_courses)


@app.route('/directeur/qr-code', methods=['POST'])
@login_required
def directeur_verify_qr():
    if current_user.role != 'directeur':
        flash("Accès refusé.", "danger")
        return redirect(url_for('home'))

    password = request.form.get('password')

    if not check_password_hash(current_user.password_hash, password):
        flash("Mot de passe incorrect. Impossible d'accéder au QR Code.", "danger")
        return redirect(url_for('directeur_dashboard'))

    return redirect(url_for('display_qr'))


def calculer_statut_retard(heure_actuelle, heure_debut_cours_str):
    """
    Compare l'heure actuelle avec l'heure de début du cours (format HH:MM).
    Retourne 'Ponctuel' ou 'Retard de X min'.
    """
    try:
        format_heure = "%H:%M"
        heure_debut = datetime.strptime(heure_debut_cours_str, format_heure).time()

        aujourdhui = datetime.now().date()
        dt_actuel = datetime.combine(aujourdhui, heure_actuelle)
        dt_debut = datetime.combine(aujourdhui, heure_debut)

        if dt_actuel <= dt_debut + timedelta(minutes=5):
            return "Ponctuel"
        else:
            minutes_retard = int((dt_actuel - dt_debut).total_seconds() // 60)
            return f"Retard de {minutes_retard} min"
    except Exception:
        return "Ponctuel"


# --- MODULE CONGÉS ET PERMISSIONS ---
@app.route('/prof/demande-conge', methods=['GET', 'POST'])
@login_required
def prof_demande_conge():
    if current_user.role not in ['enseignant', 'personnel']:
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        type_demande = request.form.get('type_demande')
        date_debut = request.form.get('date_debut')
        date_fin = request.form.get('date_fin')
        motif = request.form.get('motif')

        if not (type_demande and date_debut and date_fin and motif):
            flash("Veuillez remplir tous les champs obligatoires.", "warning")
        else:
            nouvelle_demande = DemandeConge(
                prof_id=current_user.id,
                type_demande=type_demande,
                date_debut=date_debut,
                date_fin=date_fin,
                motif=motif
            )
            db.session.add(nouvelle_demande)
            db.session.commit()
            flash("Votre demande a été soumise avec succès !", "success")
            return redirect(url_for('prof_demande_conge'))

    mes_demandes = DemandeConge.query.filter_by(prof_id=current_user.id).order_by(
        DemandeConge.date_creation.desc()).all()
    return render_template('prof/demande_conge.html', demandes=mes_demandes)


@app.route('/directeur/demandes-conge')
@login_required
def directeur_demandes_conge():
    if current_user.role != 'directeur':
        flash("Accès réservé au directeur.", "danger")
        return redirect(url_for('login'))

    demandes = DemandeConge.query.order_by(DemandeConge.date_creation.desc()).all()
    return render_template('directeur/demandes_conge.html', demandes=demandes)


@app.route('/directeur/demande-conge/<int:id>/<action>')
@login_required
def traiter_demande_conge(id, action):
    if current_user.role != 'directeur':
        flash("Accès refusé.", "danger")
        return redirect(url_for('login'))

    demande = DemandeConge.query.get_or_404(id)
    if action == 'approuver':
        demande.statut = 'Approuvé'
    elif action == 'refuser':
        demande.statut = 'Refusé'

    db.session.commit()
    flash("La demande a été mise à jour avec succès.", "success")
    return redirect(url_for('directeur_demandes_conge'))


if __name__ == '__main__':
    import os

    base_dir = os.path.dirname(os.path.abspath(__file__))
    cert_path = os.path.join(base_dir, 'localhost+2.pem')
    key_path = os.path.join(base_dir, 'localhost+2-key.pem')

    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"🔒 Certificats SSL détectés avec succès !")
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            ssl_context=(cert_path, key_path)
        )
    else:
        print(f"❌ ERREUR : Fichiers SSL introuvables dans {base_dir}")
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True
        )