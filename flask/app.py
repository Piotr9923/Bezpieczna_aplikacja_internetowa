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
from random import randint
from Crypto.Cipher import AES
import hashlib
from base64 import b64encode, b64decode

db = mariadb.connect(host="mariadb", user="root", password="root")
sql = db.cursor()

SESSION_COOKIE_HTTPONLY = True

app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = getenv("SECRET_KEY")

app.debug = False

JWT_SECRET = getenv("JWT_SECRET")
CSRF_SECRET = getenv("CSRF_SECRET")
IV = getenv("IV")
PASSWORD = getenv("PASSWORD")


def delete_database():
    sql.execute("DROP TABLE users")
    sql.execute("DROP TABLE connections")
    sql.execute("DROP TABLE last_logins")
    sql.execute("DROP TABLE sms_codes")
    sql.execute("DROP DATABASE db")


def create_database():
    sql.execute("CREATE DATABASE IF NOT EXISTS db;")
    sql.execute("USE db;")
    sql.execute("CREATE TABLE IF NOT EXISTS users (username VARCHAR(32), password VARCHAR(128), master_password "
                "VARCHAR(128), phone_number VARCHAR(12), mail VARCHAR(64));")
    sql.execute("CREATE TABLE IF NOT EXISTS connections (username VARCHAR(32), ip VARCHAR(128));")
    sql.execute("CREATE TABLE IF NOT EXISTS sms_codes (username VARCHAR(32), code VARCHAR(128) NULL);")
    sql.execute(
        "CREATE TABLE IF NOT EXISTS passwords (id INT AUTO_INCREMENT PRIMARY KEY NOT NULL, username VARCHAR(32), website VARCHAR(64), password VARCHAR(128));")
    sql.execute(
        "CREATE TABLE IF NOT EXISTS last_logins (username VARCHAR(32), logged_time DATETIME NULL, ip VARCHAR(128) NULL, browser VARCHAR(32) NULL, op_sys VARCHAR(32));")
    sql.execute("set names 'utf8'");


def get_password(username):
    sql.execute(f"SELECT password FROM users WHERE username = '{username}'")
    password, = sql.fetchone() or (None,)
    return password


def get_master_password(username):
    sql.execute(f"SELECT master_password FROM users WHERE username = '{username}'")
    password, = sql.fetchone() or (None,)
    return password


def get_mail(username):
    sql.execute(f"SELECT mail FROM users WHERE username = '{username}'")
    password, = sql.fetchone() or (None,)
    return password


def get_sms_code(username):
    sql.execute(f"SELECT code FROM sms_codes WHERE username = '{username}'")
    password, = sql.fetchone() or (None,)
    return password


def is_user(login):
    sql.execute(f"SELECT 1 FROM users WHERE username = '{login}'")
    login, = sql.fetchone() or (None,)
    if login is None:
        return False
    return True


def verify_user(login, password):
    if not is_user(login):
        return False

    hashed = get_password(login)
    if hashed is None:
        return False
    hashed = hashed.encode()
    password = password.encode()

    if checkpw(password, hashed):
        return True

    return False


def verify_master_password(login, password):
    if not is_user(login):
        return False
    hashed = get_master_password(login)
    if hashed is None:
        return False
    hashed = hashed.encode()
    password = password.encode()

    if checkpw(password, hashed):
        return True

    return False


def save_user(phone_number, login, email, password, master_password):
    password = password.encode()
    master_password = master_password.encode()

    salt = gensalt(12)
    hashed_password = hashpw(password, salt).decode()

    salt = gensalt(12)
    hashed_master_password = hashpw(master_password, salt).decode()
    try:
        sql.execute(
            f"Insert into users (username, password, master_password, phone_number, mail) VALUES (%s,%s,%s,%s,%s)",
            (login, hashed_password, hashed_master_password, phone_number, email))
        sql.execute(f"Insert into last_logins(username) VALUES (%s)", (login,))
        sql.execute(f"Insert into sms_codes(username) VALUES (%s)", (login,))
        db.commit()
    except Exception as e:
        return False

    return True


def is_new_ip(ip):
    sql.execute(f"SELECT * FROM connections WHERE username='{session.get('login')}'")
    connections = sql.fetchall()

    for conn in connections:
        if checkpw(ip.encode(), conn[1].encode()):
            return False

    return True


def get_passwords():
    sql.execute(f"SELECT id, website, password FROM passwords WHERE username='{session.get('login')}'")
    passwords = sql.fetchall()

    return passwords


def get_password_record(pid):
    sql.execute(f"SELECT username, website, password FROM passwords WHERE id='{pid}'")
    passwords = sql.fetchall()

    return passwords


def save_new_ip(ip):
    ip = ip.encode()
    salt = gensalt(8)
    hashed_ip = hashpw(ip, salt).decode()

    sql.execute(f"Insert into connections (username, ip) VALUES (%s,%s)", (session.get('login'), hashed_ip))

    db.commit()
    return True


def save_password(website, password):
    password = encrypt(password)
    try:
        sql.execute(f"Insert into passwords (username, website, password) VALUES (%s,%s,%s)",
                    (session.get('login'), website, password))
        db.commit()
        return True
    except Exception as e:
        return False


def encrypt(password):
    key = hashlib.sha256((PASSWORD+get_aes_password()).encode()).digest()
    mode = AES.MODE_CBC
    cipher = AES.new(key, mode, IV.encode())
    padded = pad_password(password).encode()
    encrypted = cipher.encrypt(padded)
    return b64encode(encrypted).decode()


def decrypt(password):
    password = b64decode(password.encode())
    key = hashlib.sha256((PASSWORD+get_aes_password()).encode()).digest()
    mode = AES.MODE_CBC
    cipher = AES.new(key, mode, IV.encode())
    decrypted_text = cipher.decrypt(password)
    return decrypted_text.rstrip().decode()


def get_aes_password():
    master_pass = get_master_password(session.get("login"))
    return master_pass[3] + master_pass[7] + master_pass[4]


def pad_password(password):
    while len(password) % 16 != 0:
        password = password + " "
    return password


def set_last_login():
    sql.execute(f"SELECT logged_time, ip, browser, op_sys FROM last_logins where username = '{session['login']}'")
    last_login = sql.fetchall()

    ua = parse(request.headers.get('User-Agent'))

    if len(last_login) == 0 or last_login[0][0] is None:
        session["last_login"] = "To jest Twoje pierwsze logowanie"
    else:
        session[
            "last_login"] = f"{last_login[0][0]} z adresu IP {last_login[0][1]} z przeglądarki {last_login[0][2]} w systemie operacyjnym {last_login[0][3]}"
    actual_time = datetime.utcnow() + timedelta(minutes=60);
    sql.execute(
        f"UPDATE last_logins SET logged_time = '{actual_time}', ip='{request.remote_addr}', browser='{ua.browser.family}', op_sys='{ua.os.family}' WHERE username='{session['login']}';")
    db.commit()


def is_database_available():
    try:
        db.ping()
    except ConnectionError as e:
        return False
    return True


def redirect(url, status=301):
    response = make_response('', status)
    response.headers['Location'] = url
    return response


def get_link(token):
    links = []
    link = "https://127.0.0.1/user/password/new?token=" + token
    links.append(link)
    link = "https://localhost/user/password/new?token=" + token
    links.append(link)
    return links


def set_new_password(login, password):
    password = password.encode()

    salt = gensalt(12)
    hashed_password = hashpw(password, salt).decode()
    sql.execute(f"UPDATE users SET password = '{hashed_password}' WHERE username = '{login}';")
    db.commit()


def generate_token(login):
    payload = {
        "iss": "Bezpiecznik",
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "usr": login,
    }
    token = encode(payload, JWT_SECRET, algorithm='HS256')
    return token


def generate_csrf_token(login):
    payload = {
        "iss": "Bezpiecznik",
        "usr": login,
        "exp": datetime.utcnow()+timedelta(seconds=300)
    }
    token = encode(payload, CSRF_SECRET, algorithm='HS256')
    return token


def generate_sms_code(login):
    code = generate_code()

    code = code.encode()

    salt = gensalt(12)
    hashed_code = hashpw(code, salt).decode()

    sql.execute(f"UPDATE sms_codes SET code='{hashed_code}' WHERE username = '{login}';")
    db.commit()

    return code


def generate_code():
    code = str(randint(0, 9)) + str(randint(0, 9)) + str(randint(0, 9)) + str(randint(0, 9))

    return code


def check_field(value, letters):
    for v in value:
        if v not in letters:
            return False

    return True


create_database()


@app.route('/')
def index():
    if session.get('login') is None:
        return render_template("index.html")

    return render_template('logged_index.html', last_login_info=session["last_login"], ip=request.remote_addr)


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

    if not check_field(email,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-@"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('registration_form'))

    if not check_field(phone_number,"0123456789"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('registration_form'))

    if not check_field(login,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('registration_form'))

    if not check_field(password,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-!$*"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('registration_form'))

    if not check_field(password2,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-!$*"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('registration_form'))

    if not check_field(master_password,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-!$*"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('registration_form'))

    if not check_field(master_password2,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-!$*"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('registration_form'))


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

    success = save_user(phone_number, login, email, password, master_password)

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

    if session.get("bad_login") is not None and session.get("bad_login") > 2:
        delta = session.get("login_block_time") - datetime.utcnow()
        flash("Logowanie możliwe za: " + str(delta.seconds // 60) + " minut " + str(delta.seconds % 60) + " sekund")
        return redirect(url_for('login_form'))

    login = request.form.get("login")
    password = request.form.get("password")

    if not is_database_available():
        flash("Błąd połączenia z bazą danych")
        return redirect(url_for('login_form'))

    if not check_field(login,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('login_form'))

    if not check_field(password,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-!$*"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('login_form'))

    if not login or not password:
        flash("Brak nazwy użytkownika lub hasła")
        return redirect(url_for('login_form'))
    if not verify_user(login, password):
        if session.get("bad_login") is None:
            session["bad_login"] = 0
        session["bad_login"] = session.get("bad_login") + 1
        if session.get("bad_login") == 3:
            session["login_block_time"] = datetime.utcnow() + timedelta(seconds=300)
        time.sleep(3)
        flash("Błędna nazwa użytkownika i/lub hasła")
        return redirect(url_for('login_form'))

    session["login"] = login
    session["logged-at"] = datetime.now()

    session["master_password_incorrect"] = 0
    session["master_password_time_block"] = datetime.utcnow()

    set_last_login()

    if is_new_ip(request.remote_addr):
        print(
            f"\n\n\nWysłałbym do Użytkownika maila o logowaniu na jego konto z nowego adresu IP - {request.remote_addr}\n\n\n",
            flush=True)
        save_new_ip(request.remote_addr)

    return redirect(url_for('dashboard'))


@app.route('/user/dashboard')
def dashboard():
    if session.get('login') is None:
        flash("Najpierw musisz się zalogować")
        return redirect(url_for('login_form'))

    if session.get('login') == "admin" or session.get('login') == "Piotr9923":
        print(
            "\n\n\nUżytkownik zalogował się na konto-pułapka. W tym momencie zablokowałbym możliwość korzystania z aplikacji dla wszystkich Użytkowników, w celu ochrony zapisanych w bazie haseł oraz poinformowałbym Użytkowników o możliwym wycieku danych i zalecił im zmianę haseł\n\n\n",
            flush=True)

    session["csrf_token"] = generate_csrf_token(login)

    return render_template("dashboard.html", last_login_info=session["last_login"], ip=request.remote_addr,
                           haspasswords=(len(get_passwords()) > 0), passwords=get_passwords(), csrf=session.get("csrf_token"))


@app.route('/user/password/change', methods=["GET"])
def change_password_form():
    return render_template("change_password.html")


@app.route('/user/password/change', methods=["POST"])
def change_password():
    login = request.form.get("login")
    mail = request.form.get("mail")

    if not check_field(login,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('index'))

    if not check_field(mail,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-@"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('index'))

    if is_user(login):
        if get_mail(login) is not None and get_mail(login) == mail:

            code = generate_sms_code(login).decode()
            token = generate_token(login)
            print("\n\n\nWysłałbym maila do Użytkownika o treści:\n"
                  "Aby zmienić hasło, w ciągu 15 minut, kliknij w poniższy link:\n"
                  f"{get_link(token)[0]}\n\n"
                  "Jeśli powyższy link nie działa spróbuj kliknąć w link alternatywny podany poniżej:\n"
                  f"{get_link(token)[1]}\n\n"
                  "Wysłałbym do Użytkownika SMS-a z kodem:\n"
                  f"{code}\n\n\n", flush=True)

            flash("Mail i SMS zostały wysłane", category="info")
            return redirect(url_for('index'))
        else:
            flash("Login i/lub mail są niepoprawne")
            return render_template("change_password.html")
    else:
        flash("Login i/lub mail są niepoprawne")
        return render_template("change_password.html")


@app.route('/user/password/new', methods=["GET"])
def new_password_form():
    token = request.args.get('token')

    if token is None:
        flash("Nie masz dostępu zmiany hasła")
        return redirect(url_for('index'))
    try:
        payload = decode(token, JWT_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        flash("Czas na zmianę hasła minął. Spróbuj ponownie.")
        return redirect(url_for('index'))
    except jwt.InvalidTokenError:
        flash("Brak dostępu do zmiany hasła")
        return redirect(url_for('index'))

    return render_template("new_password.html", token=token)


@app.route('/user/password/new', methods=["POST"])
def new_password():
    password = request.form.get("password")
    password2 = request.form.get("password2")
    code = request.form.get("code")
    token = request.args.get('token')

    if not check_field(password2,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-!$*"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('login_form'))

    if not check_field(password2,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-!$*"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('login_form'))

    if not is_database_available():
        flash("Błąd połączenia z bazą danych")
        return render_template("new_password.html")

    if not password or not password2 or not code:
        flash("Brak hasła, powtórzonego hasła lub kodu")
        return render_template("new_password.html", token=token)

    if password != password2:
        flash("Hasła nie są takie same")
        return render_template("new_password.html", token=token)

    try:
        payload = decode(token, JWT_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        flash("Czas na zmianę hasła minął. Spróbuj ponownie.")
        return redirect(url_for('index'))
    except jwt.InvalidTokenError:
        flash("Brak dostępu do zmiany hasła")
        return redirect(url_for('index'))

    if get_sms_code(payload.get('usr')) is not None and not checkpw(code.encode(),
                                                                    get_sms_code(payload.get('usr')).encode()):
        flash("Błędny kod SMS")
        return render_template("new_password.html", token=token)

    set_new_password(payload.get('usr'), password)

    flash("Hasło zostało zmienione")
    return redirect(url_for('login_form'))


@app.route('/password/add', methods=['GET'])
def add_password_form():
    if session.get('login') is None:
        flash("Najpierw musisz się zalogować")
        return redirect(url_for('login_form'))

    session["csrf_token"] = generate_csrf_token(login)

    return render_template("add_password.html", last_login_info=session["last_login"], ip=request.remote_addr, csrf=session.get("csrf_token"))


@app.route('/password/add', methods=['POST'])
def add_password():
    if session.get('login') is None:
        flash("Najpierw musisz się zalogować")
        return redirect(url_for('login_form'))

    website = request.form.get("website")
    password = request.form.get("password")

    if not check_field(website,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-$*:/ "):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('add_password_form'))

    if check_field(password,"<>()"):
        flash("Formularz zawiera niedozwolone znaki")
        return redirect(url_for('add_password_form'))

    if not is_database_available():
        flash("Błąd połączenia z bazą danych")
        return redirect(url_for('add_password_form'))

    if not website or not password:
        flash("Brak nazwy serwisu lub hasła")
        return redirect(url_for('add_password_form'))

    csrf_token = request.args.get('csrf')
    if csrf_token is None:
        flash("Wystąpił błąd! Spróbuj ponownie!")
        return redirect(url_for('add_password_form'),401)
    try:
        payload = decode(csrf_token, CSRF_SECRET, algorithms=['HS256'])
    except jwt.InvalidTokenError:
        flash("Wystąpił błąd!")
        return redirect(url_for('add_password_form'),401)
    except jwt.ExpiredSignatureError:
        flash("Wystąpił błąd! Spróbuj ponownie!")
        return redirect(url_for('add_password_form'), 401)

    if payload["usr"] != session.get("login"):
        flash("Wystąpił błąd!")
        return redirect(url_for('add_password_form'),401)

    success = save_password(website, password)

    if not success:
        flash("Błąd zapisu hasła")
        return redirect(url_for('add_password_form'))

    return redirect(url_for('dashboard'))


@app.route('/passwords/<pid>')
def get_decrypted_password(pid):
    if session.get('login') is None:
        flash("Najpierw musisz się zalogować")
        return redirect(url_for('login_form'))

    if not is_database_available():
        return "Błąd połączenia z bazą danych", 500

    db_record = get_password_record(pid)[0]

    if (session.get("login") != db_record[0]):
        flash("To nie Twoje hasło")
        return redirect(url_for('dashboard'))

    if datetime.utcnow() > session.get("master_password_time_block") and session.get("master_password_incorrect") > 2:
        session["master_password_incorrect"] = 0

    if session.get("master_password_incorrect") > 2:
        delta = session.get("master_password_time_block") - datetime.utcnow()
        return ("Odszyfrowanie hasła możliwe za: " + str(delta.seconds // 60) + " minut " + str(
            delta.seconds % 60) + " sekund"), 400

    password = request.args.get('password')
    time.sleep(0.3)

    if (not verify_master_password(session.get('login'), password)):
        session["master_password_incorrect"] =  session["master_password_incorrect"] + 1
        if session.get("master_password_incorrect")>2:
            session["master_password_time_block"] = datetime.utcnow() + timedelta(seconds=120)
        return "Błędne hasło główne", 401

    csrf_token = request.args.get('csrf')
    if csrf_token is None:
        return "Wystąpił błąd!",401
    try:
        payload = decode(csrf_token, CSRF_SECRET, algorithms=['HS256'])
    except jwt.InvalidTokenError:
        return "Wystąpił błąd!",401
    except jwt.ExpiredSignatureError:
        flash("Wystąpił błąd! Spróbuj ponownie!")
        return redirect(url_for('add_password_form'), 401)

    if payload["usr"] != session.get("login"):
        return "Wystąpił błąd!",401

    session["master_password_incorrect"] = 0

    decrypted_password = decrypt(db_record[2])
    return decrypted_password, 200


@app.route('/user/logout')
def user_logout():
    session.clear()

    return render_template("logout.html")
