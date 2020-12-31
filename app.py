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
import time
from datetime import datetime, timedelta


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


def verify_user(login,password):
    if not is_user(login):
        return False

    hashed = get_password(login)
    if hashed is None:
        return False
    hashed = hashed.encode()
    password = password.encode()

    if checkpw(password,hashed):
        return True

    return False


def save_user(phone_number,login,email,password,master_password):

    password = password.encode()
    master_password = master_password.encode()

    salt = gensalt(12)
    hashed_password = hashpw(password, salt).decode()

    salt = gensalt(12)
    hashed_master_password = hashpw(master_password, salt).decode()

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

    if session.get('login') is None:
        return render_template("index.html", ip=request.remote_addr)

    return render_template('logged_index.html', ip=request.remote_addr)


@app.route('/user/register', methods=['GET'])
def registration_form():

    if session.get('login') is None:
        return render_template("registration.html", ip=request.remote_addr)

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
        flash(f"Hasła nie są takie same")
        return redirect(url_for('registration_form'))

    if master_password != master_password2:
        flash(f"Hasła główne nie są takie same")
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
        return render_template("login.html", ip=request.remote_addr)

    return redirect(url_for('index'))


@app.route('/user/login', methods=["POST"])
def login():
    if session.get("login_block_time") is not None:
        if datetime.utcnow() > session.get("login_block_time"):
            session.clear()

    if session.get("bad_login") is not None and session.get("bad_login")>2:
        delta = session.get("login_block_time")-datetime.utcnow()
        flash("Logowanie możliwe za: "+str(delta.seconds//60)+" minut "+str(delta.seconds%60)+" sekund")
        return redirect(url_for('login_form'))

    login = request.form.get("login")
    password = request.form.get("password")

    if not is_database_available():
        flash("Błąd połączenia z bazą danych")
        return redirect(url_for('login_form'))

    if not login or not password:
        flash("Brak nazwy użytkownika lub hasła")
        return redirect(url_for('login_form'))
    if not verify_user(login,password):
        print(session.get("bad_login"))
        if session.get("bad_login") is None:
            session["bad_login"]=0
        session["bad_login"]=session.get("bad_login")+1
        if session.get("bad_login")==3:
            session["login_block_time"] = datetime.utcnow() + timedelta(seconds=300)
        time.sleep(3)
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

    return render_template("dashboard.html", ip=request.remote_addr)


@app.route('/password/add', methods=['GET'])
def add_label_form():

    if session.get('login') is None:
        flash("Najpierw musisz się zalogować")
        return redirect(url_for('login_form'))

    return render_template("add_label.html", ip=request.remote_addr)


@app.route('/user/logout')
def user_logout():

    session.clear()

    return render_template("logout.html", ip=request.remote_addr)


if __name__ == '__main__':
    app.run(threaded=True, port=5000)
