from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from base64 import b64encode  # Import b64encode function

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Replace with a secure random key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'uploads'  # Folder to store uploaded images
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif','jfif'}  # Allowed file extensions for images

db = SQLAlchemy(app)
bootstrap = Bootstrap(app)
migrate = Migrate(app, db)

# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    details = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.LargeBinary, nullable=True)

    def __repr__(self):
        return f"Item('{self.title}', '{self.category}', '{self.quantity}', '{self.price}')"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"User('{self.username}')"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Define user_loader callback
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from sqlalchemy import or_
# Routes
@app.route('/')
def index():
    search_query = request.args.get('search', '').strip()
    if search_query:
        items = Item.query.filter(or_(Item.category.contains(search_query))).all()
    else:
        items = Item.query.all()
    return render_template('index.html', items=items, b64encode=b64encode)  # Pass b64encode to template

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/add_item', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        quantity = request.form['quantity']
        details = request.form['details']
        price = request.form['price']
        
        image = request.files['image']
        if image.filename == '':
            flash('No image selected for upload', 'error')
            return redirect(request.url)
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Read the saved image file for database storage
            with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'rb') as f:
                image_data = f.read()

            new_item = Item(title=title, category=category, quantity=quantity, details=details, price=price, image=image_data)
            db.session.add(new_item)
            db.session.commit()
            flash('Item added successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid file type for image. Allowed types are png, jpg, jpeg, gif.', 'error')
            return redirect(request.url)
    return render_template('add_item.html')

@app.route('/admin/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    
    if request.method == 'POST':
        item.title = request.form['title']
        item.category = request.form['category']
        item.quantity = request.form['quantity']
        item.details = request.form['details']
        item.price = float(request.form['price'])  # Convert to float if necessary
        
        # Handle image update
        image = request.files['image']
        if image.filename != '':
            if image and allowed_file(image.filename):
                # Read the image file data as bytes
                image_data = image.read()
                item.image = image_data  # Assign bytes-like object to item.image
            else:
                flash('Invalid file type for image. Allowed types are png, jpg, jpeg, gif.', 'error')
                return redirect(request.url)
        
        db.session.commit()
        flash('Item updated successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('edit_item.html', item=item)

@app.route('/admin/delete_item/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('index'))

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Ensure the 'uploads' folder exists
os.makedirs(os.path.join(app.instance_path, 'uploads'), exist_ok=True)

def add_admin(username, password):
    with app.app_context():
        admin = User.query.filter_by(username=username).first()
        if admin:
            # Update the existing admin user
            admin.set_password(password)
        else:
            # Create a new admin user
            admin = User(username=username)
            admin.set_password(password)
            db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    add_admin('admin', '123')
    print('Admin user added successfully.')
    app.run(debug=False,host='0.0.0.0')
