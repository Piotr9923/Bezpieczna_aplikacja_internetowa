from flask import Flask, request, make_response, session, g
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
from user_agents import parse


db = mariadb.connect(host="mariadb", user="root", password="root")
sql = db.cursor()

SESSION_COOKIE_HTTPONLY = True

app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = getenv("SECRET_KEY")

app.debug = False


def delete_database():
    sql.execute("DROP TABLE users")
    sql.execute("DROP TABLE connections")
    sql.execute("DROP TABLE last_logins")
    sql.execute("DROP DATABASE db")


def create_database():

    sql.execute("CREATE DATABASE IF NOT EXISTS db;")
    sql.execute("USE db;")
    sql.execute("CREATE TABLE IF NOT EXISTS users (username VARCHAR(32), password VARCHAR(128), master_password "
                "VARCHAR(128), phone_number VARCHAR(12), mail VARCHAR(64));")
    sql.execute("CREATE TABLE IF NOT EXISTS connections (username VARCHAR(32), ip VARCHAR(128));")
    sql.execute("CREATE TABLE IF NOT EXISTS last_logins (username VARCHAR(32), logged_time DATETIME NULL, ip VARCHAR(128) NULL, browser VARCHAR(32) NULL, op_sys VARCHAR(32));")


def get_password(username):
    sql.execute(f"SELECT password FROM users WHERE username = '{username}'")
    password, = sql.fetchone() or (None,)
    return password


def get_mail(username):
    sql.execute(f"SELECT mail FROM users WHERE username = '{username}'")
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
    try:
        sql.execute(f"Insert into users (username, password, master_password, phone_number, mail) VALUES ('{login}','{hashed_password}','{hashed_master_password}','{phone_number}','{email}')")
        sql.execute(f"Insert into last_logins(username) VALUES ('{login}');")
        db.commit()
    except Exception as e:
        return False

    return True


def is_new_ip(ip):

    sql.execute(f"SELECT * FROM connections WHERE username='{session.get('login')}'")
    connections = sql.fetchall()

    for conn in connections:
        if checkpw(ip.encode(),conn[1].encode()):
            return False

    return True


def save_new_ip(ip):

    ip = ip.encode()
    salt = gensalt(8)
    hashed_ip = hashpw(ip, salt).decode()

    sql.execute(f"Insert into connections (username, ip) VALUES ('{session.get('login')}','{hashed_ip}');")

    db.commit()
    return True


def set_last_login():
    sql.execute(f"SELECT logged_time, ip, browser, op_sys FROM last_logins where username = '{session['login']}'")
    last_login = sql.fetchall()

    ua = parse(request.headers.get('User-Agent'))

    if last_login[0][0] is None:
        session["last_login"] = "To jest Twoje pierwsze logowanie"
    else:
        session["last_login"] = f"{last_login[0][0]} z adresu IP {last_login[0][1]} z przeglądarki {last_login[0][2]} w systemie operacyjnym {last_login[0][3]}"
    actual_time = datetime.utcnow() + timedelta(minutes=60);
    sql.execute(f"UPDATE last_logins SET logged_time = '{actual_time}', ip='{request.remote_addr}', browser='{ua.browser.family}', op_sys='{ua.os.family}';")
    db.commit()


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
        return render_template("index.html")

    return render_template('logged_index.html',last_login_info=session["last_login"], ip=request.remote_addr)


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
        flash("Błąd rejestracji! Sprawdź długość wprowadzonych danych")
        return redirect(url_for('registration_form'))

    return redirect(url_for('login_form'))


@app.route('/user/login', methods=["GET"])
def login_form():

    if session.get('login') is None:
        return render_template("login.html")

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

    set_last_login()

    if is_new_ip(request.remote_addr):
        print(f"Wysłałbym do Użytkownika maila o logowaniu na jego konto z nowego adresu IP - {request.remote_addr}", flush=True)
        save_new_ip(request.remote_addr)

    return redirect(url_for('dashboard'))


@app.route('/user/dashboard')
def dashboard():

    if session.get('login') is None:
        flash("Najpierw musisz się zalogować")
        return redirect(url_for('login_form'))

    if session.get('login') == "admin" or session.get('login') == "Piotr9923":
        print("Użytkownik zalogował się na konto-pułapka. W tym momencie zablokowałbym możliwość korzystania z aplikacji dla wszystkich Użytkowników, w celu ochrony zapisanych w bazie haseł", flush=True)

    return render_template("dashboard.html",last_login_info=session["last_login"], ip=request.remote_addr)


@app.route('/user/password_change', methods=["GET"])
def change_password_form():

    return render_template("change_password.html")


@app.route('/user/password_change', methods=["POST"])
def change_password():

    login = request.form.get("login")
    mail = request.form.get("mail")

    if is_user(login):
        if get_mail(login) is not None and get_mail(login) == mail:
            print("Wysłałbym maila do Użytkownika o treści:\n"
                  "Aby zmienić hasło kliknij w poniższy link:\n"
                  "LINK", flush=True)
            flash("Mail i SMS zostały wysłane",category="info")
            return redirect(url_for('index'))
        else:
            flash("Login i/lub mail są niepoprawne")
            return render_template("change_password.html")
    else:
        flash("Login i/lub mail są niepoprawne")
        return render_template("change_password.html")


@app.route('/password/add', methods=['GET'])
def add_label_form():

    if session.get('login') is None:
        flash("Najpierw musisz się zalogować")
        return redirect(url_for('login_form'))

    return render_template("add_password.html",last_login_info=session["last_login"], ip=request.remote_addr)


@app.route('/user/logout')
def user_logout():

    session.clear()

    return render_template("logout.html")


if __name__ == '__main__':
    app.run(threaded=True, port=5000)
