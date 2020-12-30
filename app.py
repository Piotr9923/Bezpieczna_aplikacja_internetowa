from flask import Flask, request, make_response, session
from dotenv import load_dotenv
from flask import render_template, flash, url_for
from os import getenv
from bcrypt import hashpw, gensalt, checkpw
from redis import StrictRedis
from datetime import datetime
from uuid import uuid4
from jwt import encode, decode
from redis.exceptions import ConnectionError
import jwt
import os
import mysql.connector as mariadb


db = mariadb.connect(host="mariadb", user="root", password="root")
sql = db.cursor()

SESSION_COOKIE_HTTPONLY = True

app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = getenv("SECRET_KEY")

app.debug = False


def delete_database():
    sql.execute("DROP TABLE users")
    sql.execute("DROP DATABASE db")


def create_database():
    sql.execute("USE db;")
    sql.execute("SELECT password FROM users WHERE username = 'test'")
    password, = sql.fetchone() or (None,)

    sql.execute("CREATE DATABASE IF NOT EXISTS db;")
    sql.execute("USE db;")
    sql.execute("CREATE TABLE IF NOT EXISTS users (username VARCHAR(32), password VARCHAR(128), master_password "
                "VARCHAR(128), phone_number VARCHAR(12), mail VARCHAR(64));")


def get_password(username):
    sql.execute(f"SELECT password FROM users WHERE username = '{username}'")
    password, = sql.fetchone() or (None,)
    return password


def is_user(login):
    sql.execute(f"SELECT 1 FROM users WHERE username = '{login}'")
    login, = sql.fetchone() or (None,)
    if login is None:
        return False
    return True


def save_user(phone_number,login,email,password,master_password):

    password = password.encode()
    master_password = master_password.encode()

    salt = gensalt(5)
    hashed_password = hashpw(password, salt)
    salt = gensalt(5)
    hashed_password = hashpw(hashed_password, salt).decode()

    salt = gensalt(5)
    hashed_master_password = hashpw(master_password, salt)
    salt = gensalt(5)
    hashed_master_password = hashpw(hashed_master_password, salt).decode()

    sql.execute(f"Insert into users (username, password, master_password, phone_number, mail) VALUES ('{login}','{hashed_password}','{hashed_master_password}','{phone_number}','{email}')")

    db.commit()
    return True


def is_database_available():
    try:
        db.ping()
    except ConnectionError as e:
        print(str(e))
        return False
    return True


def redirect(url, status=301):
    response = make_response('', status)
    response.headers['Location'] = url
    return response


create_database()


@app.route('/')
def index():

    print(request.remote_addr, flush=True)

    if session.get('login') is None:
        return render_template("index.html")

    return render_template('logged_index.html')


@app.route('/user/register', methods=['GET'])
def registration_form():

    if session.get('login') is None:
        return render_template("registration.html")

    return redirect(url_for('index'))


@app.route('/user/register', methods=['POST'])
def registration():
    email = request.form.get("mail")
    phone_number = request.form.get("phone_number")
    login = request.form.get("login")
    password = request.form.get("password")
    password2 = request.form.get("password2")
    master_password = request.form.get("master_password")
    master_password2 = request.form.get("master_password2")

    if not is_database_available():
        flash("Błąd połączenia z bazą danych")
        return redirect(url_for('registration_form'))

    if not email:
        flash("Brak adresu e-mail")
    if not phone_number:
        flash("Brak numeru telefonu")
    if not login:
        flash("Brak nazwy użytkownika")
    if not password:
        flash("Brak hasła")
    if not master_password:
            flash("Brak hasła głównego")
    if password != password2:
        flash(f"Hasła nie są takie same {password} _ {password2}")
        return redirect(url_for('registration_form'))

    if master_password != master_password2:
        flash(f"Hasła główne nie są takie same {password} _ {password2}")
        return redirect(url_for('registration_form'))

    if email and login and password and master_password and phone_number:
        if is_user(login):
            flash(f"Użytkownik {login} istnieje")
            return redirect(url_for('registration_form'))
    else:
        return redirect(url_for('registration_form'))

    success = save_user(phone_number,login,email,password,master_password)

    if not success:
        flash("Błąd rejestracji")
        return redirect(url_for('registration_form'))

    return redirect(url_for('login_form'))


@app.route('/user/login', methods=["GET"])
def login_form():

    if session.get('login') is None:
        return render_template("login.html")

    return redirect(url_for('index'))


@app.route('/user/login', methods=["POST"])
def login():
    login = request.form.get("login")
    password = request.form.get("password")

    if not is_database_available():
        flash("Błąd połączenia z bazą danych")
        return redirect(url_for('login_form'))

    if not login or not password:
        flash("Brak nazwy użytkownika lub hasła")
        return redirect(url_for('login_form'))
    if not verify_user(login,password):
        flash("Błędna nazwa użytkownika i/lub hasła")
        return redirect(url_for('login_form'))

    session["login"] = login
    session["logged-at"] = datetime.now()

    return redirect(url_for('dashboard'))


@app.route('/user/dashboard')
def dashboard():

    if session.get('login') is None:
        flash("Najpierw musisz się zalogować")
        return redirect(url_for('login_form'))

    labels = {}

    for key in db.scan_iter("label:*"):

        if db.hget(key, "sender")==session.get('login'):
            labels[db.hget(key,"id").decode()]={
                "id":db.hget(key,"id").decode(),
                "name":db.hget(key,"name").decode(),
                "delivery_id":db.hget(key,"delivery_id").decode(),
                "size":db.hget(key,"size").decode()
            }

    delete_tokens = {}

    for label in labels:
        delete_tokens[label] = generate_delete_token(label, session.get('login')).decode()

    return render_template("dashboard.html", labels=labels.items(), haslabels=(len(labels)>0), delete_tokens=delete_tokens)


@app.route('/password/add', methods=['GET'])
def add_label_form():

    if session.get('login') is None:
        flash("Najpierw musisz się zalogować")
        return redirect(url_for('login_form'))

    return render_template("add_label.html")


if __name__ == '__main__':
    app.run(threaded=True, port=5000)
