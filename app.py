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
    sql.execute("CREATE DATABASE IF NOT EXISTS db;")
    sql.execute("USE db;")
    sql.execute("CREATE TABLE IF NOT EXISTS users (username VARCHAR(32), password VARCHAR(128));")


def get_password(username):
    sql.execute(f"SELECT password FROM users WHERE username = '{username}'")
    password, = sql.fetchone() or (None,)
    return password


create_database()


@app.route('/')
def index():

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
    firstname = request.form.get("firstname")
    lastname = request.form.get("lastname")
    adress = request.form.get("adress")
    email = request.form.get("mail")
    login = request.form.get("login")
    password = request.form.get("password")
    password2 = request.form.get("password2")

    if not is_database_available():
        flash("Błąd połączenia z bazą danych")
        return redirect(url_for('registration_form'))

    if not firstname:
        flash("Brak imienia")
    if not lastname:
        flash("Brak nazwiska")
    if not adress:
        flash("Brak adresu")
    if not email:
        flash("Brak adresu e-mail")
    if not login:
        flash("Brak nazwy użytkownika")
    if not password:
        flash("Brak hasła")
    if password != password2:
        flash(f"Hasła nie są takie same {password} _ {password2}")
        return redirect(url_for('registration_form'))

    if email and login and password and firstname and lastname and adress:
        if is_user(login):
            flash(f"Użytkownik {login} istnieje")
            return redirect(url_for('registration_form'))
    else:
        return redirect(url_for('registration_form'))

    success = save_user(firstname,lastname,login,email,password,adress)

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


@app.route('/password/add',methods=['GET'])
def add_label_form():

    if session.get('login') is None:
        flash("Najpierw musisz się zalogować")
        return redirect(url_for('login_form'))

    return render_template("add_label.html")


if __name__ == '__main__':
    app.run(threaded=True, port=5000)
