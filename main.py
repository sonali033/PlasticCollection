from flask import Flask, render_template, request, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_mysqldb import MySQL
from werkzeug.utils import redirect
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from datetime import datetime
from functools import wraps
import json

with open("config.json", 'r') as file:
    params = json.load(file)['params']

local_server = params['local_server']

app = Flask(__name__, template_folder="templates")

app.config['MYSQL_HOST'] = 'PlasticCollection.mysql.pythonanywhere-services.com'
app.config['MYSQL_USER'] = 'PlasticCollectio'
app.config['MYSQL_PASSWORD'] = 'Sagar@123'
app.config['MYSQL_DB'] = 'PlasticCollectio$PlasticCollection'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail_user'],
    MAIL_PASSWORD=params['gmail_password']
)
mail = Mail(app)
if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

db = SQLAlchemy(app)


class Contacts(db.Model):
    """ Sr,First_name,Last_name,Phone,msg,Date,Email """
    Sr = db.Column(db.Integer, primary_key=True)
    First_name = db.Column(db.String(40), nullable=False)
    Last_name = db.Column(db.String(40), nullable=False)
    Phone = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    Date = db.Column(db.String(12), nullable=True)
    Email = db.Column(db.String(20), nullable=False)


@app.route("/")
def home():
    return render_template('Plastic_collection.html', params=params)


@app.route("/Aboutus")
def Aboutus():
    return render_template('Aboutus.html', params=params)


@app.route("/FindOutHow")
def Organization():
    return render_template('Organization.html', params=params)


class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)",
                    (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('Login'))
    return render_template('register.html', form=form)


@app.route("/Login", methods=['GET', 'POST'])
def Login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            if sha256_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = "Invalid login"
                return render_template('Login.html', error=error)
        else:
            error = "username not found"
            return render_template('Login.html', error=error)
        cur.close()

    return render_template('Login.html')


# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('Login'))
    return wrap


@app.route("/logout")
@is_logged_in
def logout():
    session.clear()
    flash("You are now logged out",'success')
    return redirect(url_for('Login'))


@app.route("/index")
def index():
    return render_template('index.html')


@app.route("/dashboard", methods=['GET', 'POST'])
@is_logged_in
def dashboard():
    if request.method == 'POST':
        # Get Form Fields
        City = request.form['City']
        City = City.lower()

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by City
        result = cur.execute("SELECT * FROM organization WHERE City = %s", [City])

        articles = cur.fetchall()
        if result > 0:
            return render_template('Dashboard.html', articles=articles)
        else:
            msg = "No plastic Collection Centres Found"
            return render_template('Dashboard.html', msg=msg)
        # Close connection
        cur.close()
    return render_template('Dashboard.html')


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contacts(First_name=first_name, Last_name=last_name, Phone=phone, msg=message, Date=datetime.now(),
                         Email=email)
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New message from' + first_name + last_name,
                          sender=email,
                          recipients=[params['gmail_user']],
                          body=message + "\n" + phone
                          )
    return render_template('Contact.html', params=params)


app.secret_key = 'secret123'
app.run(debug=True)
