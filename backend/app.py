"""
=============================================================
  Abhyuday Bharat Food Cluster — Backend API
  File  : backend/app.py
  Stack : Flask + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
  Run   : python app.py          (development)
          gunicorn app:app       (production)
=============================================================
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart





import os
import json
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets

# ──────────────────────────────────────────────
#  APP SETUP
# ──────────────────────────────────────────────
BASE_DIR    = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')
DB_DIR      = os.path.join(BASE_DIR, '..', 'database')
os.makedirs(DB_DIR, exist_ok=True)

app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path=''
)

# Allow CORS for local dev (React/Vite dev servers, etc.)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ──────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 'abfc-dev-secret-change-in-production-2025'
)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    f"sqlite:///{os.path.join(DB_DIR, 'abfc.db')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ──────────────────────────────────────────────
#  MODELS
# ──────────────────────────────────────────────

class AdminUser(db.Model):
    """Admin login credentials."""
    __tablename__ = 'admin_users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def to_dict(self):
        return {'id': self.id, 'username': self.username}


class Category(db.Model):
    """Product category (e.g. Frozen Fries, Millet Premixes)."""
    __tablename__ = 'categories'
    id         = db.Column(db.Integer,  primary_key=True)
    slug       = db.Column(db.String(80),  unique=True, nullable=False)  # 'fries', 'millet'
    name       = db.Column(db.String(120), nullable=False)
    emoji      = db.Column(db.String(10),  default='📦')
    active     = db.Column(db.Boolean,  default=True)
    sort_order = db.Column(db.Integer,  default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products   = db.relationship('Product', backref='category_obj', lazy=True,
                                  foreign_keys='Product.cat_slug',
                                  primaryjoin='Category.slug == Product.cat_slug')

    def to_dict(self):
        return {
            'id':         self.id,
            'slug':       self.slug,
            'name':       self.name,
            'emoji':      self.emoji,
            'active':     self.active,
            'sort_order': self.sort_order,
        }


class Product(db.Model):
    """Individual product in the catalogue."""
    __tablename__ = 'products'
    id         = db.Column(db.Integer,  primary_key=True)
    cat_slug   = db.Column(db.String(80), db.ForeignKey('categories.slug'), nullable=False)
    sub        = db.Column(db.String(120), nullable=False)   # sub-category label
    name       = db.Column(db.String(200), nullable=False)
    qty        = db.Column(db.String(200), nullable=False)   # pack sizes
    img        = db.Column(db.String(300), nullable=False)
    note       = db.Column(db.Text, default='')
    tags       = db.Column(db.Text, default='[]')            # JSON array stored as text
    active     = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer,  default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def tags_list(self):
        try:
            return json.loads(self.tags)
        except Exception:
            return []

    @tags_list.setter
    def tags_list(self, val):
        self.tags = json.dumps(val)

    def to_dict(self):
        return {
            'id':         self.id,
            'cat':        self.cat_slug,
            'sub':        self.sub,
            'name':       self.name,
            'qty':        self.qty,
            'img':        self.img,
            'note':       self.note,
            'tags':       self.tags_list,
            'active':     self.active,
            'sort_order': self.sort_order,
        }


class Enquiry(db.Model):
    """B2B enquiry submitted via contact form."""
    __tablename__ = 'enquiries'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    company       = db.Column(db.String(200), nullable=False)
    phone         = db.Column(db.String(40),  nullable=False)
    email         = db.Column(db.String(200), default='')
    business_type = db.Column(db.String(100), default='')
    message       = db.Column(db.Text, default='')
    seen          = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':            self.id,
            'name':          self.name,
            'company':       self.company,
            'phone':         self.phone,
            'email':         self.email,
            'business_type': self.business_type,
            'message':       self.message,
            'seen':          self.seen,
            'date':          self.created_at.isoformat() if self.created_at else None,
        }


class SiteContact(db.Model):
    """Single-row table for editable contact details."""
    __tablename__ = 'site_contact'
    id      = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.Text, default='')
    phone   = db.Column(db.String(40), default='')
    email   = db.Column(db.String(200), default='')
    hours   = db.Column(db.String(200), default='')

    def to_dict(self):
        return {
            'address': self.address,
            'phone':   self.phone,
            'email':   self.email,
            'hours':   self.hours,
        }


class AdminSession(db.Model):
    """Simple token-based sessions for admin panel."""
    __tablename__ = 'admin_sessions'
    id         = db.Column(db.Integer, primary_key=True)
    token      = db.Column(db.String(64), unique=True, nullable=False)
    username   = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ──────────────────────────────────────────────
#  AUTH DECORATOR
# ──────────────────────────────────────────────

def require_auth(f):
    """Protect admin routes — checks Authorization: Bearer <token> header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        if not token:
            token = request.args.get('token')

        if not token:
            return jsonify({'error': 'Authentication required'}), 401

        session = AdminSession.query.filter_by(token=token).first()
        if not session:
            return jsonify({'error': 'Invalid or expired token'}), 401

        return f(*args, **kwargs)
    return decorated

# ──────────────────────────────────────────────
#  HELPER — JSON success / error
# ──────────────────────────────────────────────

def ok(data=None, msg='Success', **kwargs):
    payload = {'success': True, 'message': msg}
    if data is not None:
        payload['data'] = data
    payload.update(kwargs)
    return jsonify(payload)

def err(msg='Error', code=400):
    return jsonify({'success': False, 'error': msg}), code



# ──────────────────────────────────────────────
#  EMAIL SENDER (UPDATED)
# ──────────────────────────────────────────────

def send_enquiry_email(enquiry):
    try:
        EMAIL_USER = os.environ.get("EMAIL_USER")   # sender Gmail
        EMAIL_PASS = os.environ.get("EMAIL_PASS")   # app password
        EMAIL_TO   = "food@abhyuday.in"             # admin email (fixed)

        if not EMAIL_USER or not EMAIL_PASS:
            print("⚠️ Email credentials not set")
            return

        # 📌 Subject
        subject = f"📩 New Enquiry - {enquiry.name}"

        # 📌 Email Body (well formatted)
        body = f"""
========================================
        NEW ENQUIRY RECEIVED
========================================

👤 Name          : {enquiry.name}
🏢 Company       : {enquiry.company}
📞 Phone         : {enquiry.phone}
📧 Email         : {enquiry.email or 'N/A'}
💼 Business Type : {enquiry.business_type or 'N/A'}

----------------------------------------
📝 Message:
{enquiry.message or 'No message provided'}
----------------------------------------

🕒 Date: {enquiry.created_at}

========================================
Abhyuday Bharat Food Cluster Website
========================================
        """

        # 📌 Create Email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject

        # ✅ IMPORTANT: Reply goes to customer directly
        if enquiry.email:
            msg['Reply-To'] = enquiry.email

        msg.attach(MIMEText(body, 'plain'))

        # 📌 SMTP Setup
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()

        print(f"✅ Enquiry email sent to {EMAIL_TO}")

    except Exception as e:
        print("❌ Email sending failed:", str(e))





# ──────────────────────────────────────────────
#  SERVE FRONTEND
# ──────────────────────────────────────────────

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/admin')
@app.route('/admin.html')
def serve_admin():
    return send_from_directory(FRONTEND_DIR, 'admin.html')

# Catch-all: serve any static asset from frontend/
@app.route('/<path:path>')
def serve_static(path):
    full = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(full):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')

# ──────────────────────────────────────────────
#  AUTH ROUTES  /api/auth/...
# ──────────────────────────────────────────────

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return err('Username and password required')

    user = AdminUser.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return err('Invalid credentials', 401)

    # Create session token
    token = secrets.token_hex(32)
    session = AdminSession(token=token, username=username)
    db.session.add(session)
    db.session.commit()

    return ok({'token': token, 'username': username}, 'Login successful')


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    auth_header = request.headers.get('Authorization', '')
    token = auth_header[7:] if auth_header.startswith('Bearer ') else None
    if token:
        AdminSession.query.filter_by(token=token).delete()
        db.session.commit()
    return ok(msg='Logged out')


@app.route('/api/auth/change-password', methods=['POST'])
@require_auth
def change_password():
    data        = request.get_json() or {}
    current_pw  = data.get('current_password', '')
    new_pw      = data.get('new_password', '')

    auth_header = request.headers.get('Authorization', '')
    token       = auth_header[7:] if auth_header.startswith('Bearer ') else None
    session_obj = AdminSession.query.filter_by(token=token).first()
    if not session_obj:
        return err('Not authenticated', 401)

    user = AdminUser.query.filter_by(username=session_obj.username).first()
    if not user:
        return err('User not found', 404)
    if not user.check_password(current_pw):
        return err('Current password is incorrect')
    if len(new_pw) < 6:
        return err('New password must be at least 6 characters')

    user.set_password(new_pw)
    db.session.commit()
    return ok(msg='Password updated successfully')

# ──────────────────────────────────────────────
#  PUBLIC ROUTES  (no auth required — read-only)
# ──────────────────────────────────────────────

@app.route('/api/categories', methods=['GET'])
def get_categories():
    cats = Category.query.filter_by(active=True).order_by(Category.sort_order).all()
    return ok([c.to_dict() for c in cats])


@app.route('/api/products', methods=['GET'])
def get_products():
    cat_filter = request.args.get('cat')
    query = Product.query.filter_by(active=True)
    if cat_filter and cat_filter != 'all':
        query = query.filter_by(cat_slug=cat_filter)
    products = query.order_by(Product.sort_order, Product.id).all()
    return ok([p.to_dict() for p in products])


@app.route('/api/contact', methods=['GET'])
def get_contact():
    c = SiteContact.query.first()
    return ok(c.to_dict() if c else {})






@app.route('/api/enquiry', methods=['POST'])
def submit_enquiry():
    data = request.get_json() or {}

    name    = (data.get('name') or '').strip()
    company = (data.get('company') or '').strip()
    phone   = (data.get('phone') or '').strip()

    if not name or not company or not phone:
        return err('Name, company and phone are required')

    enq = Enquiry(
        name          = name,
        company       = company,
        phone         = phone,
        email         = (data.get('email') or '').strip(),
        business_type = (data.get('business_type') or '').strip(),
        message       = (data.get('message') or '').strip(),
    )

    db.session.add(enq)
    db.session.commit()

    # ✅ SEND EMAIL AFTER SAVE
    send_enquiry_email(enq)

    return ok(enq.to_dict(), 'Enquiry submitted successfully')




# ──────────────────────────────────────────────
#  ADMIN ROUTES  (auth required)
# ──────────────────────────────────────────────

# ── Categories ──

@app.route('/api/admin/categories', methods=['GET'])
@require_auth
def admin_get_categories():
    cats = Category.query.order_by(Category.sort_order).all()
    return ok([c.to_dict() for c in cats])


@app.route('/api/admin/categories', methods=['POST'])
@require_auth
def admin_add_category():
    data   = request.get_json() or {}
    slug   = (data.get('slug') or data.get('id') or '').strip().lower()
    name   = (data.get('name')  or '').strip()
    emoji  = (data.get('emoji') or '📦').strip()
    active = data.get('active', True)

    if not slug or not name:
        return err('slug and name are required')

    if Category.query.filter_by(slug=slug).first():
        return err(f'Category slug "{slug}" already exists')

    max_order = db.session.query(db.func.max(Category.sort_order)).scalar() or 0
    cat = Category(slug=slug, name=name, emoji=emoji, active=active, sort_order=max_order + 1)
    db.session.add(cat)
    db.session.commit()
    return ok(cat.to_dict(), 'Category added')


@app.route('/api/admin/categories/<int:cat_id>', methods=['PUT'])
@require_auth
def admin_update_category(cat_id):
    cat  = Category.query.get_or_404(cat_id)
    data = request.get_json() or {}

    if 'name'   in data: cat.name   = data['name'].strip()
    if 'emoji'  in data: cat.emoji  = data['emoji'].strip()
    if 'active' in data: cat.active = bool(data['active'])

    # If slug changes, update all products
    new_slug = (data.get('slug') or '').strip().lower()
    if new_slug and new_slug != cat.slug:
        if Category.query.filter_by(slug=new_slug).first():
            return err(f'Slug "{new_slug}" already in use')
        Product.query.filter_by(cat_slug=cat.slug).update({'cat_slug': new_slug})
        cat.slug = new_slug

    db.session.commit()
    return ok(cat.to_dict(), 'Category updated')


@app.route('/api/admin/categories/<int:cat_id>', methods=['DELETE'])
@require_auth
def admin_delete_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    return ok(msg='Category deleted')

# ── Products ──

@app.route('/api/admin/products', methods=['GET'])
@require_auth
def admin_get_products():
    cat_filter = request.args.get('cat')
    query      = Product.query
    if cat_filter and cat_filter != 'all':
        query = query.filter_by(cat_slug=cat_filter)
    products = query.order_by(Product.cat_slug, Product.sort_order, Product.id).all()
    return ok([p.to_dict() for p in products])


@app.route('/api/admin/products', methods=['POST'])
@require_auth
def admin_add_product():
    data = request.get_json() or {}
    cat  = (data.get('cat')  or '').strip()
    sub  = (data.get('sub')  or '').strip()
    name = (data.get('name') or '').strip()
    qty  = (data.get('qty')  or '').strip()
    img  = (data.get('img')  or '').strip()

    if not all([cat, sub, name, qty, img]):
        return err('cat, sub, name, qty and img are required')

    if not Category.query.filter_by(slug=cat).first():
        return err(f'Category "{cat}" does not exist')

    max_order = db.session.query(db.func.max(Product.sort_order)).scalar() or 0
    p = Product(
        cat_slug   = cat,
        sub        = sub,
        name       = name,
        qty        = qty,
        img        = img,
        note       = (data.get('note') or '').strip(),
        active     = data.get('active', True),
        sort_order = max_order + 1,
    )
    p.tags_list = data.get('tags', [])
    db.session.add(p)
    db.session.commit()
    return ok(p.to_dict(), 'Product added')


@app.route('/api/admin/products/<int:prod_id>', methods=['PUT'])
@require_auth
def admin_update_product(prod_id):
    p    = Product.query.get_or_404(prod_id)
    data = request.get_json() or {}

    if 'cat'    in data: p.cat_slug   = data['cat'].strip()
    if 'sub'    in data: p.sub        = data['sub'].strip()
    if 'name'   in data: p.name       = data['name'].strip()
    if 'qty'    in data: p.qty        = data['qty'].strip()
    if 'img'    in data: p.img        = data['img'].strip()
    if 'note'   in data: p.note       = data['note'].strip()
    if 'active' in data: p.active     = bool(data['active'])
    if 'tags'   in data: p.tags_list  = data['tags']

    p.updated_at = datetime.utcnow()
    db.session.commit()
    return ok(p.to_dict(), 'Product updated')


@app.route('/api/admin/products/<int:prod_id>', methods=['DELETE'])
@require_auth
def admin_delete_product(prod_id):
    p = Product.query.get_or_404(prod_id)
    db.session.delete(p)
    db.session.commit()
    return ok(msg='Product deleted')

# ── Enquiries ──

@app.route('/api/admin/enquiries', methods=['GET'])
@require_auth
def admin_get_enquiries():
    enqs = Enquiry.query.order_by(Enquiry.created_at.desc()).all()
    return ok([e.to_dict() for e in enqs])


@app.route('/api/admin/enquiries/<int:enq_id>/seen', methods=['PUT'])
@require_auth
def admin_mark_seen(enq_id):
    e      = Enquiry.query.get_or_404(enq_id)
    e.seen = True
    db.session.commit()
    return ok(msg='Marked as seen')


@app.route('/api/admin/enquiries/mark-all-seen', methods=['PUT'])
@require_auth
def admin_mark_all_seen():
    Enquiry.query.filter_by(seen=False).update({'seen': True})
    db.session.commit()
    return ok(msg='All enquiries marked as seen')


@app.route('/api/admin/enquiries/<int:enq_id>', methods=['DELETE'])
@require_auth
def admin_delete_enquiry(enq_id):
    e = Enquiry.query.get_or_404(enq_id)
    db.session.delete(e)
    db.session.commit()
    return ok(msg='Enquiry deleted')


@app.route('/api/admin/enquiries', methods=['DELETE'])
@require_auth
def admin_clear_enquiries():
    Enquiry.query.delete()
    db.session.commit()
    return ok(msg='All enquiries cleared')

# ── Contact Info ──

@app.route('/api/admin/contact', methods=['GET'])
@require_auth
def admin_get_contact():
    c = SiteContact.query.first()
    return ok(c.to_dict() if c else {})


@app.route('/api/admin/contact', methods=['PUT'])
@require_auth
def admin_update_contact():
    data = request.get_json() or {}
    c    = SiteContact.query.first()
    if not c:
        c = SiteContact()
        db.session.add(c)

    if 'address' in data: c.address = data['address'].strip()
    if 'phone'   in data: c.phone   = data['phone'].strip()
    if 'email'   in data: c.email   = data['email'].strip()
    if 'hours'   in data: c.hours   = data['hours'].strip()

    db.session.commit()
    return ok(c.to_dict(), 'Contact info updated')

# ── Stats ──

@app.route('/api/admin/stats', methods=['GET'])
@require_auth
def admin_stats():
    return ok({
        'total_products':  Product.query.filter_by(active=True).count(),
        'total_cats':      Category.query.filter_by(active=True).count(),
        'total_enquiries': Enquiry.query.count(),
        'new_enquiries':   Enquiry.query.filter_by(seen=False).count(),
    })

# ──────────────────────────────────────────────
#  DATABASE SEED  (run once on first start)
# ──────────────────────────────────────────────

def seed_database():
    """Populate the database with default data if tables are empty."""

    # ── Admin user ──
    if not AdminUser.query.first():
        admin = AdminUser(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        print('  ✓ Default admin created  (user: admin / pass: admin123)')

    # ── Contact info ──
    if not SiteContact.query.first():
        c = SiteContact(
            address='1001 & 1020 Time Square Arcade, Nr Bagban Party Plot, '
                    'Thaltej Shilaj Road, Thaltej, Ahmedabad – 380059, Gujarat, India',
            phone='+91 9904166522',
            email='food@abhyuday.in',
            hours='Mon – Sat, 9 AM – 6 PM IST',
        )
        db.session.add(c)
        print('  ✓ Default contact info seeded')

    # ── Categories ──
    default_cats = [
        ('vegs',      'Frozen Vegetables',      '🥦', 1),
        ('fries',     'Frozen Fries',            '🍟', 2),
        ('snacks',    'Frozen Snacks',           '🥟', 3),
        ('breads',    'Breads & Paratha',        '🫓', 4),
        ('curries',   'Curries & Gravy',         '🍛', 5),
        ('combo',     'Combo Meals',             '🍱', 6),
        ('millet',    'Millet Based Premixes',   '🌾', 7),
        ('nonmillet', 'Non-Millet Premixes',     '🍚', 8),
    ]
    if not Category.query.first():
        for slug, name, emoji, order in default_cats:
            db.session.add(Category(slug=slug, name=name, emoji=emoji,
                                    active=True, sort_order=order))
        db.session.flush()
        print('  ✓ Default categories seeded')

    # ── Products ──
    if not Product.query.first():
        products = [
            # FRIES
            ('fries','French Fries','Straight Cut French Fries','400g · 1kg · 2.5kg · 10kg','src/products/Stright Fries.png','Classic straight-cut fries.',['Frozen','RTE'],1),
            ('fries','French Fries','Crinkle Cut French Fries','400g · 1kg · 2.5kg · 10kg','src/products/Crinkle Fries.png','Crinkle-cut for extra crunch.',['Frozen','RTE'],2),
            ('fries','French Fries','Curly French Fries','400g · 1kg · 2.5kg · 10kg','src/products/Curly Fries.png','Fun spiral curly fries.',['Frozen','RTE'],3),
            ('fries','Wedges','Potato Wedges','400g · 1kg · 2.5kg · 10kg','src/products/Coted Fries.png','Thick seasoned potato wedges.',['Frozen','RTE'],4),
            # VEGETABLES
            ('vegs','IQF Vegetables','Green Peas','400g · 1kg · 2.5kg · 10kg','src/products/IQF Green Peas.png','Flash-frozen at peak freshness.',['IQF'],1),
            ('vegs','IQF Vegetables','Sweet Corn','400g · 1kg · 2.5kg · 10kg','src/products/IQF Sweet Corn.png','Golden sweet corn kernels.',['IQF'],2),
            ('vegs','IQF Vegetables','Mixed Vegetables','400g · 1kg · 2.5kg · 10kg','src/products/IQF Mix Veg.png','Pre-cut blend of seasonal vegetables.',['IQF'],3),
            ('vegs','IQF Vegetables','Okra','400g · 1kg · 2.5kg · 10kg','src/products/IQF Cut Okra (2).png','Tender okra individually quick frozen.',['IQF'],4),
            ('vegs','IQF Vegetables','Cauliflower','400g · 1kg · 2.5kg · 10kg','src/products/IQF Cualiflower.png','Florets frozen at peak freshness.',['IQF'],5),
            ('vegs','IQF Vegetables','French Beans','400g · 1kg · 2.5kg · 10kg','src/products/IQF French Beans.png','Tender green beans trimmed and frozen.',['IQF'],6),
            ('vegs','IQF Vegetables','Carrot','400g · 1kg · 2.5kg · 10kg','src/products/IQF Carrot.png','Diced carrots flash-frozen.',['IQF'],7),
            ('vegs','IQF Vegetables','Broccoli','400g · 1kg · 2.5kg · 10kg','src/products/IQF Broccoli.png','Premium broccoli florets.',['IQF'],8),
            ('vegs','IQF Vegetables','Baby Corn','400g · 1kg · 2.5kg · 10kg','src/products/IQF Baby Corn.png','Tender baby corn.',['IQF'],9),
            ('vegs','IQF Vegetables','Spinach','400g · 1kg · 2.5kg · 10kg','src/products/IQF Spinach.png','Washed chopped spinach flash-frozen.',['IQF'],10),
            # SNACKS
            ('snacks','Snacks','Punjabi Samosa','400g · 1kg · 2.5kg · 10kg','src/products/Punjabi Samosa.jpg','Classic Punjabi samosa.',['Frozen','RTE'],1),
            ('snacks','Snacks','Aloo Tikki','400g · 1kg · 2.5kg · 10kg','src/products/Aloo Tikki.jpg','Ready-to-fry potato tikkis.',['Frozen','RTE'],2),
            ('snacks','Snacks','Hara Bhara Kabab','400g · 1kg · 2.5kg · 10kg','src/products/Harabhara Kabab.jpg','Spinach and pea-based kabab.',['Frozen'],3),
            # BREADS
            ('breads','Naan','Plain Naan','320g · 400g · 1kg · 5kg','src/products/Plain Naan.jpg','Soft fluffy naans.',['Frozen'],1),
            ('breads','Naan','Garlic Butter Naan','400g · 1kg · 5kg','src/products/Garlic Butter Naan.jpg','Pre-loaded with garlic butter.',['Frozen'],2),
            ('breads','Paratha','Plain Paratha','400g · 1kg · 5kg','src/products/Plain Paratha.jpg','Layered flaky plain paratha.',['Frozen'],3),
            ('breads','Paratha','Aloo Paratha','400g · 1kg · 5kg','src/products/Aloo Paratha.jpg','Classic spiced potato stuffed paratha.',['Frozen'],4),
            ('breads','Paratha','Lachha Paratha','400g · 1kg · 5kg','src/products/Laccha Paratha.jpg','Crispy multi-layered lachha paratha.',['Frozen'],5),
            ('breads','Paratha','Malabar Paratha','400g · 1kg · 5kg','src/products/Malabar paratha.png','Soft Kerala-style paratha.',['Frozen'],6),
            # CURRIES
            ('curries','Dal','Dal Makhani','300g · 500g · 1kg','src/products/Dal-Makhani.jpg','Slow-cooked creamy dal makhani.',['Frozen'],1),
            ('curries','Curry','Chole Chana','300g · 500g · 1kg','src/products/Amritsari-Cholle.jpg','Punjabi-style chole.',['Frozen'],2),
            ('curries','Curry','Rajma Masala','300g · 500g · 1kg','src/products/Shahi-Rajma.jpg','Rich kidney bean curry.',['Frozen'],3),
            ('curries','Dal','Dal Tadka','300g · 500g · 1kg','src/products/Dal-Tadka.jpg','Classic tempered dal.',['Frozen'],4),
            ('curries','Curry','Pav Bhaji','300g · 500g · 1kg','src/products/Pav-Bhaji.jpg','Mumbai-style pav bhaji.',['Frozen','RTE'],5),
            # COMBO
            ('combo','Rice','Jeera Rice','300g · 500g · 1kg','src/products/Plain-Rice.jpg','Cumin-tempered rice.',['Frozen'],1),
            ('combo','Combo Meal','Rice + Dal Makhani','300g · 500g · 1kg','src/products/Rice-With-Dal-Makhani.jpg','Complete meal combo.',['Frozen'],2),
            ('combo','Combo Meal','Rice + Chole','300g · 500g · 1kg','src/products/Rice-With-Amritsarichole.jpg','High-protein combo meal.',['Frozen'],3),
            ('combo','Combo Meal','Rice + Rajma','300g · 500g · 1kg','src/products/Rice-With-Rajma.jpg','Wholesome comfort meal combo.',['Frozen'],4),
            # MILLET
            ('millet','Idli','Multi Millet Idli','1 KG','src/products/multi millet idli.jpg','Blend of 5 millets.',['Millet'],1),
            ('millet','Idli','Jowar & Oats Idli','1 KG','src/products/jowar idli.png','Sustained energy from jowar and oats.',['Millet'],2),
            ('millet','Idli','Ragi & Jowar Idli','1 KG','src/products/ragi-idli.png','Excellent for bone health.',['Millet'],3),
            ('millet','Idli','Quinoa Idli','1 KG','src/products/quinoa idli.jpg','All 9 essential amino acids.',['Millet'],4),
            ('millet','Dosa','Multi Millet Dosa','1 KG','src/products/multi millet dosa.png','Crispy dosa from 5 millets.',['Millet'],5),
            ('millet','Dosa','Jowar Dosa','1 KG','src/products/jowar dosa.png','Antioxidant-rich jowar dosa.',['Millet'],6),
            ('millet','Dosa','Ragi Dosa','1 KG','src/products/Ragi Dosa.png','Finger millet dosa.',['Millet'],7),
            ('millet','Dosa','Oats Dosa','1 KG','src/products/oats dosa.png','Beta-glucan rich oats dosa.',['Millet'],8),
            ('millet','Khichdi','Multi Millet Khichdi','1 KG','src/products/millet_khichdi.png','Complete one-pot meal.',['Millet'],9),
            ('millet','Khichdi','Foxtail Khichdi','1 KG','src/products/Foxtail-Khichdi.jpg','Low GI foxtail millet.',['Millet'],10),
            ('millet','Khichdi','Kodo Khichdi','1 KG','src/products/Kodo Khichdi.png','Polyphenol-rich kodo millet.',['Millet'],11),
            ('millet','Khichdi','Quinoa Khichdi','1 KG','src/products/Quinoa Khichdi.png','Quinoa + lentil khichdi.',['Millet'],12),
            ('millet','Biryani','Kodo Millet Biryani','1 KG','src/products/Kodo Millet Biryani.png','Whole spice biryani.',['Millet'],13),
            ('millet','Lemon Rice','Little Millet Lemon Rice','1 KG','src/products/Little Millet Lemon Rice.png','Vitamin C enriched lemon rice.',['Millet'],14),
            ('millet','Upma','Jowar Oats Upma','1 KG','src/products/Jowar Oats Upma.png','Sustained energy upma.',['Millet'],15),
            ('millet','Pongal','Foxtail Millet Sweet Pongal','1 KG','src/products/Foxtail Millet Sweet Pongal.png','Naturally sweetened with jaggery.',['Millet'],16),
            ('millet','Sheera','Multi Millet Sheera (Jaggery)','1 KG','src/products/sheera.png','Nutritious jaggery sheera.',['Millet'],17),
            ('millet','Malt','Ragi Malt','1 KG','src/products/Ragi Malt.png','Sprouted ragi malt.',['Millet'],18),
            ('millet','Malt','Ragi Malt (Sweet)','1 KG','src/products/Ragi Malt (Sweet).png','Pre-sweetened with jaggery.',['Millet'],19),
            ('millet','Chilla','Sprouted Moong Chilla','1 KG','src/products/Sprouted Moong Chilla.png','High protein bioavailability.',['Millet'],20),
            ('millet','Chilla','Sprouted Moong + Foxtail Chilla','1 KG','src/products/foxtail chilla.jpg','Low-GI balanced protein chilla.',['Millet'],21),
            ('millet','Chilla','Sprouted Moong + Jowar Chilla','1 KG','src/products/jowar chilla.png','Gluten-free high-fibre chilla.',['Millet'],22),
            ('millet','Soup','Bajra Soup','1 KG','src/products/Bajra Soup.png','Iron-rich bajra soup.',['Millet'],23),
            ('millet','Pasta Sauce','Oats White Pasta Sauce (GF)','1 KG','src/products/White-Gravy.jpg','Gluten-free pasta sauce.',['Millet'],24),
            # NON-MILLET
            ('nonmillet','Sheera','Pineapple Sheera','1 KG','src/products/PINEAPPLE SHEERA.png','Tangy-sweet pineapple sheera.',['Premix'],1),
            ('nonmillet','Halwa','Moong Dal Halwa','1 KG','src/products/moong daal halwa.png','High-protein moong dal halwa.',['Premix'],2),
            ('nonmillet','Halwa','Sooji / Rava Halwa','1 KG','src/products/rava halwa.png','Traditional rava halwa.',['Premix'],3),
            ('nonmillet','Kheer','Rice Kheer','1 KG','src/products/rice kheer.png','Creamy rice kheer mix.',['Premix'],4),
            ('nonmillet','Kheer','Vermicelli Kheer','1 KG','src/products/VERMICELLI KHEER.png','Fast-prep kheer.',['Premix'],5),
            ('nonmillet','Pasta Sauce','White Sauce for Pasta','1 KG','src/products/White-Gravy.jpg','Bechamel-style pasta sauce.',['Premix'],6),
            ('nonmillet','Dosa','Rice Dosa Mix','1 KG','src/products/rice dosa mix.png','Crispy dosas every time.',['Premix'],7),
            ('nonmillet','Idli','Rice Idli Mix','1 KG','src/products/sheera.png','Classic soft fluffy idli.',['Premix'],8),
            ('nonmillet','Dhokla','Rice Dhokla Mix','1 KG','src/products/rice_dhokla.png','Light steamed Gujarati snack.',['Premix'],9),
            ('nonmillet','Upma','Sooji / Rava Upma','1 KG','src/products/Rava Upma.jpg','Pre-seasoned rava upma.',['Premix'],10),
            ('nonmillet','Khichdi','Rice Masala Khichdi','1 KG','src/products/rice masala khichdi.jpg','Complete meal.',['Premix'],11),
            ('nonmillet','Biryani','Rice Biryani','1 KG','src/products/Veg-Biryani-Rice.jpg','Restaurant-quality biryani blend.',['Premix'],12),
            ('nonmillet','Lemon Rice','Lemon Rice Mix','1 KG','src/products/Lemon-Rice.jpg','Quick consistent lemon rice.',['Premix'],13),
        ]
        for cat, sub, name, qty, img, note, tags, order in products:
            p = Product(cat_slug=cat, sub=sub, name=name, qty=qty, img=img,
                        note=note, active=True, sort_order=order)
            p.tags_list = tags
            db.session.add(p)
        print(f'  ✓ {len(products)} default products seeded')

    db.session.commit()

# ──────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_database()
        print('\n✅  Abhyuday Foods backend ready')
        print('   http://127.0.0.1:5000       ← website')
        print('   http://127.0.0.1:5000/admin ← admin panel')
        print('   http://127.0.0.1:5000/api/  ← REST API\n')

    app.run(debug=True, host='0.0.0.0', port=5000)
