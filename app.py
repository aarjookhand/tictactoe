from flask import *
import sqlite3
from pymongo import MongoClient
from gridfs import GridFS
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from bson import ObjectId
from flask_login import current_user
from werkzeug.utils import secure_filename
from functools import wraps
from flask import flash, redirect, url_for
from dotenv import load_dotenv
from functools import wraps

load_dotenv()
import os


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "default_secret_key")

MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DB = os.environ.get("MONGODB_DB")
SQLITE_URI = os.environ.get('SQLITE_URI', 'ttt.db')

board = [''] * 9
current_player = 'X'


# conn to MongoDB
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]


fs = GridFS(db)

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

conn = sqlite3.connect(SQLITE_URI)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  email TEXT NOT NULL,
                  password TEXT NOT NULL,
                  is_admin INTEGER DEFAULT 0)''')

conn.commit()
conn.close()



login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)



class User(UserMixin):
    def __init__(self, id,  username, email, password):
         self.id = id
         self.username = username
         self.email = email
         self.password = password       
         
    def is_active(self):
         return self.authenticated
    def is_anonymous(self):
         return False
    def is_authenticated(self):
         return self.authenticated

    def get_id(self):
         return str(self.email)


@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(SQLITE_URI)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        user = User(user_data[0], user_data[1], user_data[2], user_data[3])
        return user

    return None



class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log in')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, field):
        conn = sqlite3.connect(SQLITE_URI)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (field.data,))
        existing_user = cursor.fetchone()
        conn.close()

        if existing_user:
            raise ValidationError('username alr taken')


    def validate_email(self, field):
        conn = sqlite3.connect(SQLITE_URI)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (field.data,))
        existing_user = cursor.fetchone()
        conn.close()

        if existing_user:
            raise ValidationError('email alr taken')
        

@app.route('/', methods=['GET'])
def display_welcome():
    return render_template('welcome.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
   
        conn = sqlite3.connect(SQLITE_URI)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
        else:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
            conn.commit()

            user_doc = {
                '_id': str(email),          
            }
            db.users.insert_one(user_doc)

            conn.close()

            flash("Successfully registered. You can now log in.")
            return redirect(url_for('login'))

    return render_template('register.html', form=form)




@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.is_submitted():
        print('form validated')
        username = form.username.data
        password = form.password.data

        conn = sqlite3.connect(SQLITE_URI)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            user = User(user_data[0], user_data[1], user_data[2], user_data[3])
            login_user(user)
            current_user.email = user_data[2] 
            session['player1'] = current_user.username  
            flash("Successfully logged in")
            print("Login email:", current_user.email)

            return redirect(url_for('home'))
    
        else:
            flash('Login Failed. Invalid Credentials')

    return render_template('login.html', form=form)

@app.route('/loginpvp', methods=['GET', 'POST'])
def loginpvp():
    form = LoginForm()

    if form.is_submitted():
        username = form.username.data
        password = form.password.data

        conn = sqlite3.connect(SQLITE_URI)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            user = User(user_data[0], user_data[1], user_data[2], user_data[3])
            login_user(user)
            current_user.email = user_data[2]
            session['player2'] = current_user.username  
            flash("Successfully logged in")
            return redirect(url_for('tictactoe'))

        else:
            flash('Login Failed. Invalid Credentials')

    return render_template('loginpvp.html', form=form)




@app.route('/home')
@login_required
def home():
    return render_template('home.html')


@app.route('/pvp', methods=['GET'])
@login_required
def pvp():
    if 'player2' not in session:
        return redirect(url_for('loginpvp'))


@app.route('/tictactoe', methods=['GET', 'POST'])
@login_required
def tictactoe():
    player1 = session.get('player1')
    player2 = session.get('player2')

    if not player1 or not player2:
        return redirect(url_for('pvp'))

    if 'board' not in session:
        session['board'] = [""] * 9

    board = session['board']
    current_player = player1 if session['current_player'] == 'X' else player2

    if request.method == 'POST':
        if current_user.username == current_player:
            position = int(request.form['position'])

            if board[position] == "":
                board[position] = current_player
                winner = check_winner(board)

                if winner:
                    reset_game()
                    return render_template('tictactoe.html', board=board, current_player=current_player, winner=winner)
                elif not "" in board:
                    reset_game()
                    return render_template('tictactoe.html', board=board, current_player=current_player, draw=True)
                else:
                    session['current_player'] = 'O' if session['current_player'] == 'X' else 'X'

    return render_template('tictactoe.html', board=board, current_player=current_player)


# ... Your Flask app setup ...

@app.route('/pve', methods=['GET', 'POST'])
@login_required
def pve():
    if 'board' not in session:
        session['board'] = [""] * 9
    if 'current_player' not in session:
        session['current_player'] = "X"

    if request.method == 'POST':
        board = session['board']
        current_player = session['current_player']
        position = int(request.form['position'])

        if board[position] == "" and current_user.username == 'human':
            board[position] = current_player
            session['board'] = board

            if check_winner(board):
                reset_game()
                return render_template('pve.html', board=board, current_player=current_player, winner=current_user.username)
            elif "" not in board:
                reset_game()
                return render_template('pve.html', board=board, draw=True)

            current_player = "O"
            session['current_player'] = current_player

            # Provide moves for the computer (for example)
            computer_moves = [0, 4, 2, 6, 7]
            for move in computer_moves:
                if board[move] == "":
                    board[move] = current_player
                    session['board'] = board

                    if check_winner(board):
                        reset_game()
                        return render_template('pve.html', board=board, current_player=current_player, winner="Computer")
                    elif "" not in board:
                        reset_game()
                        return render_template('pve.html', board=board, draw=True)

                    current_player = "X"
                    session['current_player'] = current_player

    return render_template('pve.html', board=session['board'], current_player=session['current_player'])

# ... The rest of your Flask app ...

def reset_game():
    session['board'] = [""] * 9
    session['current_player'] = 'X'



def check_winner(board):
    winning_combinations = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
    for combo in winning_combinations:
        if board[combo[0]] == board[combo[1]] == board[combo[2]] and board[combo[0]] != "":
            return board[combo[0]]
    return None


def reset_game():
    session['board'] = [""] * 9
    session['current_player'] = "X"


if __name__ == '__main__':
    app.run(debug=True)
