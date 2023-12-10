# Gerekli importları ekleyin
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import SubmitField
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

# Kullanıcı yükleyiciyi tanımlayın
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class UploadForm(FlaskForm):
    file = FileField('Dosya Seç')
    submit = SubmitField('Yükle')

def create_user_folder(user_id):
    user_folder = os.path.join('repo', str(user_id))
    os.makedirs(user_folder, exist_ok=True)

def get_user_folder(user_id):
    return os.path.join('repo', str(user_id))

with app.app_context():
    db.create_all()

# Ana sayfa
@app.route('/')
def index():
    return render_template('index.html')

# Kayıt olma
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            create_user_folder(new_user.id)

            return render_template('login.html', success_message="Kayıt başarılı!")
        except IntegrityError:
            db.session.rollback()
            return render_template('register.html', error_message="Bu kullanıcı adı daha önce alınmış!")

    return render_template('register.html')

# Giriş
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard', user_id=user.id))
        else:
            return render_template('login.html', error_message="Giriş başarısız!")

    return render_template('login.html')

# Ana kontrol paneli
@app.route('/dashboard/<int:user_id>', methods=['GET', 'POST'])
@login_required
def dashboard(user_id):
    if current_user.id != user_id:
        return 'Erişim reddedildi!'

    user_folder = get_user_folder(user_id)
    files = os.listdir(user_folder)

    form = UploadForm()
    if form.validate_on_submit():
        for uploaded_file in request.files.getlist('file'):
            file_path = os.path.join(user_folder, uploaded_file.filename)
            uploaded_file.save(file_path)

        return redirect(url_for('dashboard', user_id=user_id))

    return render_template('dashboard.html', files=files, user_id=user_id, form=form)

# Dosya indirme
@app.route('/download/<int:user_id>/<filename>')
@login_required
def download(user_id, filename):
    user_folder = get_user_folder(user_id)
    file_path = os.path.join(user_folder, filename)
    return send_file(file_path, as_attachment=True)

# Dosya silme
@app.route('/delete/<int:user_id>/<filename>')
@login_required
def delete_file(user_id, filename):
    user_folder = get_user_folder(user_id)
    file_path = os.path.join(user_folder, filename)
    os.remove(file_path)
    return redirect(url_for('dashboard', user_id=user_id))
# Dosya yükleme
@app.route('/upload', methods=['POST'])
def upload():
    user_id = current_user.id
    user_folder = get_user_folder(user_id)

    # Gelen dosyaları al
    uploaded_files = request.files.getlist('file')

    for uploaded_file in uploaded_files:
        file_path = os.path.join(user_folder, uploaded_file.filename)
        uploaded_file.save(file_path)

    return redirect(url_for('dashboard', user_id=user_id))

# Uygulamayı çalıştırın
if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1" ,port=5000)
