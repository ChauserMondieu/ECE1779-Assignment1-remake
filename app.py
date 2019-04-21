from flask import Flask, render_template, redirect, url_for, flash, session, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
import os
import faceDetection_function as faced_function
import imageThumbnail_function as imageThumbnail


# Define the path for saving photos
UPLOAD_FOLDER = '/static/picture'
ALLOWED_EXTENSIONS = ['png', 'jpg', 'JPG', 'PNG']
base_path = os.path.dirname(__file__)
raw_photo_address = os.path.join(base_path, 'static/picture/raw_picture/')
thumbnail_address = os.path.join(base_path, 'static/picture/thumbnail_picture/')
faced_detected_picture = os.path.join(base_path, 'static/picture/face_detected_picture/')


# Initialize the instance
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:ece1779pass@127.0.0.1/faced?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'Happy Wind Man'
# Define the pointer for database
db = SQLAlchemy(app)
# Initialize security
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'welcome_function'
login_manager.login_message = 'Please login to enter'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# Define WTF class in the welcome page
class WelcomeForm(FlaskForm):
    name = StringField('Name: ', validators=[DataRequired()])
    password = PasswordField('Password: ', validators=[DataRequired()])
    submit = SubmitField('Submit')


# Define WTF class in the registration page
class RegistrationForm(FlaskForm):
    name = StringField('Name: ', validators=[DataRequired()])
    password = PasswordField('Password: ', validators=[DataRequired()])
    password_check = PasswordField('Password Confirmation: ', validators=[DataRequired()])
    submit = SubmitField('Submit')


# Define WTF class in the upload page
class UploadForm(FlaskForm):
    file = FileField('Upload your photo: ',
                     validators=[FileRequired(), FileAllowed(['png', 'jpg', 'JPG', 'PNG'], 'Images only!')])
    submit = SubmitField('Submit')


# Define WTF class in the uploadF page
class UploadFForm(FlaskForm):
    username = StringField('Name: ', validators=[DataRequired()])
    password = StringField('Password: ', validators=[DataRequired()])
    file = FileField('Upload your photo: ',
                     validators=[FileRequired(), FileAllowed(['png', 'jpg', 'JPG', 'PNG'], 'Images only!')])
    submit = SubmitField('Submit')


# Build the class of the user
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100), unique=False)
    photo_address_thumbnail = db.Column(db.String(100), unique=False)
    photo_address_detected = db.Column(db.String(100), unique=False)
    photo_address_raw = db.Column(db.String(100), unique=False)
    photo_count = db.Column(db.Integer, unique=False)


@login_manager.user_loader
def user_loader(user_id):
    user = User.query.get(user_id)
    return user


@app.route('/', methods=['GET', 'POST'])
def welcome_function():
    form = WelcomeForm()
    if form.validate_on_submit():
        session['name'] = form.name.data
        session['password'] = form.password.data
        if User.query.filter_by(name=session.get('name')).first() is not None and \
                check_password_hash(User.query.filter_by(name=session.get('name')).first().password,
                                    session.get('password')):
            login_user(User.query.filter_by(name=session.get('name')).first())
            return redirect(url_for('visit_function', user_name=session.get('name')))
        else:
            flash('Invalid pair of the user name and the password!')
            return redirect(url_for('welcome_function'))
    else:
        return render_template("welcome_page.html", form=form, name=session.get('name'))


# Define the register page
@app.route('/api/register', methods=['GET', 'POST'])
def registration_function():
    form = RegistrationForm()
    if form.validate_on_submit():
        session['name'] = form.name.data
        session['password'] = form.password.data
        session['password_check'] = form.password_check.data
        if User.query.filter_by(name=session.get('name')).first() is None:
            if session.get('password') == session.get('password_check'):
                password = generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)
                user = User(name=form.name.data, password=password, photo_count=0)
                db.session.add(user)
                db.session.commit()
                flash('Creating successfully!')
                return redirect(url_for('welcome_function'))
            else:
                flash('The confirmation not pass!')
                return redirect(url_for('registration_function'))
        else:
            flash('The user name already existed!')
            return redirect(url_for('registration_function'))
    else:
        return render_template("registration_page.html", form=form, name=session.get('name'))


# Define the user page
@app.route('/api/user/<user_name>', methods=['GET', 'POST'])
@login_required
def visit_function(user_name):
    thumbnail_used_address = []
    count = []
    photo_count = User.query.filter_by(name=user_name).first().photo_count
    for i in range(photo_count):
        photo_thumbnail_address = "/static/picture/thumbnail_picture/" + user_name + str(i+1) + ".jpg"
        thumbnail_used_address.append(photo_thumbnail_address)
        count.append(i+1)
    return render_template("visit_page.html", name=user_name, thumbnail_used_address=thumbnail_used_address,
                           count=count)


# Define the result page
@app.route('/api/user/<user_name>/<photo_id>/result', methods=['GET', 'POST'])
@login_required
def result_function(user_name, photo_id):
    raw_photo_used_address = "/static/picture/raw_picture/" + user_name + str(photo_id) + ".jpg"
    faced_detected_used_picture = "/static/picture/face_detected_picture/" + user_name + str(photo_id) + ".jpg"
    return render_template("result_page.html", name=user_name, raw_photo_address=raw_photo_used_address,
                           faced_detected_picture=faced_detected_used_picture)


# Define the upload page
@app.route('/api/upload/<user_name>', methods=['GET', 'POST'])
@login_required
def upload_function(user_name):
    form = UploadForm()
    if form.validate_on_submit():
        user = User.query.filter_by(name=user_name).first()
        user.photo_count = user.photo_count + 1
        photo_address = raw_photo_address + user_name + str(user.photo_count) + '.jpg'
        form.file.data.save(photo_address)
        photo_detected_address = faced_detected_picture + user_name + str(user.photo_count) + '.jpg'
        photo_thumbnail_address = thumbnail_address + user_name + str(user.photo_count) + '.jpg'
        faced_function.fd_function(photo_address, photo_detected_address)
        imageThumbnail.it_function(photo_address, photo_thumbnail_address)
        user.photo_address_raw = raw_photo_address
        user.photo_address_detected = faced_detected_picture
        user.photo_address_thumbnail = thumbnail_address
        db.session.add(user)
        db.session.commit()
        flash("Picture successfully uploaded!")
        return redirect(url_for('visit_function', user_name=user_name))
    else:
        return render_template("upload_page.html", form=form, name=user_name)


# Define the guest upload page
@app.route('/api/upload', methods=['GET', 'POST'])
def uploadF_function():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        file = request.files['file']
        if User.query.filter_by(name=username).first() is not None and \
                check_password_hash(User.query.filter_by(name=username).first().password, password) and file and \
                allowed_file(file.filename):
            login_user(User.query.filter_by(name=username).first())
            user = User.query.filter_by(name=username).first()
            user.photo_count = user.photo_count + 1
            photo_address = raw_photo_address + username + str(user.photo_count) + '.jpg'
            file.save(photo_address)
            photo_detected_address = faced_detected_picture + username + str(user.photo_count) + '.jpg'
            photo_thumbnail_address = thumbnail_address + username + str(user.photo_count) + '.jpg'
            faced_function.fd_function(photo_address, photo_detected_address)
            imageThumbnail.it_function(photo_address, photo_thumbnail_address)
            user.photo_address_raw = raw_photo_address
            user.photo_address_detected = faced_detected_picture
            user.photo_address_thumbnail = thumbnail_address
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('visit_function', user_name=user.name))
        else:
            flash('Incorrect Input')
            return redirect(url_for('uploadF_function'))
    else:
        return render_template("uploadF_page.html")


@app.route('/api/user/logout')
@login_required
def logout_function():
    logout_user()
    return render_template("logout_page.html")


if __name__ == '__main__':
    app.run(host='0.0.0.0')
