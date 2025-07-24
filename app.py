# Nazwa pliku: app.py
import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

# --- KONFIGURACJA APLIKACJI ---
app = Flask(__name__)

# Konfiguracja bazy danych
db_path = os.path.join(os.environ.get('RENDER_DATABASE_DIR', os.getcwd()), 'typer.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'twoj_super_tajny_klucz_zmien_go_na_cos_innego'

db = SQLAlchemy(app)

# --- MODELE BAZY DANYCH (TABELE) ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    points = db.Column(db.Integer, default=0)
    bets = db.relationship('Bet', backref='user', cascade="all, delete-orphan")

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    home_team = db.Column(db.String(100), nullable=False)
    away_team = db.Column(db.String(100), nullable=False)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    is_finished = db.Column(db.Boolean, default=False)
    bets = db.relationship('Bet', backref='match', cascade="all, delete-orphan")

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    bet_home_score = db.Column(db.Integer, nullable=False)
    bet_away_score = db.Column(db.Integer, nullable=False)

# --- FUNKCJA DO PRZELICZANIA PUNKTÓW ---
def recalculate_all_points():
    for user in User.query.all():
        user.points = 0
    db.session.commit()
    for finished_match in Match.query.filter_by(is_finished=True).all():
        for bet in finished_match.bets:
            points_to_add = 0
            if bet.bet_home_score == finished_match.home_score and bet.bet_away_score == finished_match.away_score:
                points_to_add = 3
            elif (bet.bet_home_score > bet.bet_away_score and finished_match.home_score > finished_match.away_score) or \
                 (bet.bet_home_score < bet.bet_away_score and finished_match.home_score < finished_match.away_score) or \
                 (bet.bet_home_score == bet.bet_away_score and finished_match.home_score == finished_match.away_score):
                points_to_add = 1
            user_to_update = User.query.get(bet.user_id)
            if user_to_update:
                user_to_update.points += points_to_add
    db.session.commit()

# --- GŁÓWNA STRONA I LOGIKA ---
@app.route('/')
def index():
    users = User.query.order_by(User.points.desc()).all()
    matches = Match.query.order_by(Match.id.desc()).all()
    return render_template('index.html', users=users, matches=matches)

@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form.get('name')
    if name and not User.query.filter_by(name=name).first():
        new_user = User(name=name, points=0)
        db.session.add(new_user)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_match', methods=['POST'])
def add_match():
    home_team = request.form.get('home_team')
    away_team = request.form.get('away_team')
    if home_team and away_team:
        new_match = Match(home_team=home_team, away_team=away_team)
        db.session.add(new_match)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_bet/<int:match_id>', methods=['POST'])
def add_bet(match_id):
    user_id = request.form.get('user_id')
    bet_home_score = request.form.get('bet_home_score')
    bet_away_score = request.form.get('bet_away_score')
    if user_id and bet_home_score is not None and bet_away_score is not None:
        existing_bet = Bet.query.filter_by(user_id=user_id, match_id=match_id).first()
        if not existing_bet:
            new_bet = Bet(user_id=user_id, match_id=match_id, bet_home_score=int(bet_home_score), bet_away_score=int(bet_away_score))
            db.session.add(new_bet)
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/update_score/<int:match_id>', methods=['POST'])
def update_score(match_id):
    match = Match.query.get_or_404(match_id)
    home_score_str = request.form.get('home_score')
    away_score_str = request.form.get('away_score')
    if home_score_str and away_score_str:
        match.home_score = int(home_score_str)
        match.away_score = int(away_score_str)
        match.is_finished = True
        db.session.commit()
        recalculate_all_points()
    return redirect(url_for('index'))

# --- NOWE FUNKCJE DO USUWANIA ---
@app.route('/delete_match/<int:match_id>', methods=['POST'])
def delete_match(match_id):
    match_to_delete = Match.query.get_or_404(match_id)
    db.session.delete(match_to_delete)
    db.session.commit()
    recalculate_all_points()
    return redirect(url_for('index'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    recalculate_all_points()
    return redirect(url_for('index'))

@app.route('/delete_bet/<int:bet_id>', methods=['POST'])
def delete_bet(bet_id):
    bet_to_delete = Bet.query.get_or_404(bet_id)
    db.session.delete(bet_to_delete)
    db.session.commit()
    recalculate_all_points()
    return redirect(url_for('index'))

# Komenda do inicjacji bazy danych
@app.cli.command("init-db")
def init_db_command():
    db.create_all()
    print("Zainicjowano bazę danych.")