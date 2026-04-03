# Abhyuday Bharat Food Cluster — Full Stack Project

```
project/
├── frontend/
│   ├── src/products/       ← all product images
│   ├── index.html          ← main website
│   └── admin.html          ← admin panel
├── backend/
│   ├── app.py              ← Flask API server
│   ├── requirements.txt    ← Python dependencies
│   └── .env.example        ← environment variable template
├── database/
│   ├── abfc.db             ← SQLite file (auto-created on first run)
│   └── README.md           ← schema documentation
├── .gitignore
└── README.md               ← this file
```

---

## Quick Start (Local Development)

### 1. Clone / place files
```
project/
├── frontend/   ← your existing index.html + admin.html + src/
├── backend/    ← app.py + requirements.txt
├── database/   ← auto-created by app.py
```

### 2. Create Python virtual environment
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment (optional)
```bash
cp .env.example .env
# Edit .env if needed — defaults work fine for development
```

### 5. Run the server
```bash
python app.py
```

You will see:
```
✅  Abhyuday Foods backend ready
   http://127.0.0.1:5000       ← website
   http://127.0.0.1:5000/admin ← admin panel
   http://127.0.0.1:5000/api/  ← REST API
```

Open `http://127.0.0.1:5000` in your browser.

**Default admin login:** `admin` / `admin123`

---

## How the Frontend Connects to the Backend

The `index.html` and `admin.html` files currently use `localStorage` for data storage.
To switch them to use the real API, replace the localStorage calls with `fetch()` to the API endpoints below.

> The backend already **serves** the frontend files — Flask acts as both the API server
> and the static file server. No separate web server (nginx/Apache) is needed for development.

---

## API Reference

### Public Endpoints (no auth)

| Method | URL                  | Description                     |
|--------|----------------------|---------------------------------|
| GET    | `/api/categories`    | All active categories           |
| GET    | `/api/products`      | All active products             |
| GET    | `/api/products?cat=fries` | Products filtered by category |
| GET    | `/api/contact`       | Business contact info           |
| POST   | `/api/enquiry`       | Submit B2B enquiry              |

**POST /api/enquiry — request body:**
```json
{
  "name":          "John Doe",
  "company":       "ABC Foods",
  "phone":         "+91 9876543210",
  "email":         "john@abc.com",
  "business_type": "QSR / Cloud Kitchen",
  "message":       "Need 100kg of fries per week"
}
```

---

### Auth Endpoints

| Method | URL                         | Description        |
|--------|-----------------------------|--------------------|
| POST   | `/api/auth/login`           | Get bearer token   |
| POST   | `/api/auth/logout`          | Invalidate token   |
| POST   | `/api/auth/change-password` | Change password    |

**POST /api/auth/login:**
```json
{ "username": "admin", "password": "admin123" }
```
Returns: `{ "data": { "token": "abc123...", "username": "admin" } }`

Use the token in all admin requests:
```
Authorization: Bearer abc123...
```

---

### Admin Endpoints (require Bearer token)

#### Categories
| Method | URL                            | Description             |
|--------|--------------------------------|-------------------------|
| GET    | `/api/admin/categories`        | All categories          |
| POST   | `/api/admin/categories`        | Add category            |
| PUT    | `/api/admin/categories/<id>`   | Update category         |
| DELETE | `/api/admin/categories/<id>`   | Delete category         |

**POST/PUT body:**
```json
{
  "slug":   "chinese",
  "name":   "Frozen Chinese",
  "emoji":  "🥡",
  "active": true
}
```

#### Products
| Method | URL                          | Description         |
|--------|------------------------------|---------------------|
| GET    | `/api/admin/products`        | All products        |
| GET    | `/api/admin/products?cat=fries` | Filtered by cat  |
| POST   | `/api/admin/products`        | Add product         |
| PUT    | `/api/admin/products/<id>`   | Update product      |
| DELETE | `/api/admin/products/<id>`   | Delete product      |

**POST/PUT body:**
```json
{
  "cat":    "fries",
  "sub":    "French Fries",
  "name":   "Sweet Potato Fries",
  "qty":    "400g · 1kg · 2.5kg",
  "img":    "src/products/sweet-potato-fries.jpg",
  "note":   "Crispy sweet potato fries.",
  "tags":   ["Frozen", "RTE"],
  "active": true
}
```

#### Enquiries
| Method | URL                                      | Description           |
|--------|------------------------------------------|-----------------------|
| GET    | `/api/admin/enquiries`                   | All enquiries         |
| PUT    | `/api/admin/enquiries/<id>/seen`         | Mark one as read      |
| PUT    | `/api/admin/enquiries/mark-all-seen`     | Mark all as read      |
| DELETE | `/api/admin/enquiries/<id>`             | Delete one            |
| DELETE | `/api/admin/enquiries`                  | Clear all             |

#### Contact
| Method | URL                    | Description          |
|--------|------------------------|----------------------|
| GET    | `/api/admin/contact`   | Get contact info     |
| PUT    | `/api/admin/contact`   | Update contact info  |

#### Stats
| Method | URL                 | Description       |
|--------|---------------------|-------------------|
| GET    | `/api/admin/stats`  | Dashboard counts  |

---

## Production Deployment

### Option A — Single VPS / DigitalOcean Droplet

```bash
# 1. Install system dependencies
sudo apt update && sudo apt install python3-pip python3-venv nginx

# 2. Set up project
git clone <your-repo> /var/www/abfc
cd /var/www/abfc/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Create .env with production values
cp .env.example .env
nano .env   # set SECRET_KEY and DATABASE_URL

# 4. Run with Gunicorn (production WSGI server)
gunicorn --bind 0.0.0.0:5000 --workers 3 app:app

# 5. Configure nginx to proxy to port 5000
#    (see nginx config below)
```

**nginx config** (`/etc/nginx/sites-available/abfc`):
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
    }

    # Serve product images directly (faster)
    location /src/products/ {
        alias /var/www/abfc/frontend/src/products/;
    }
}
```

### Option B — Railway / Render / Heroku

1. Push project to GitHub
2. Create a new Web Service pointing to `/backend`
3. Set start command: `gunicorn app:app`
4. Add environment variable: `SECRET_KEY=<random-string>`
5. For PostgreSQL: add a Postgres plugin and set `DATABASE_URL` automatically

### Option C — Vercel / Netlify (frontend only)

Host `frontend/` as a static site on Vercel/Netlify, and deploy the backend
separately on Railway/Render. Update the API base URL in the frontend JS.

---

## Changing Default Admin Password

Either:
- Log into the admin panel → Profile → Change Password
- Or via the API: `POST /api/auth/change-password`

---

## Database Backup

```bash
# SQLite
cp database/abfc.db database/abfc_backup_$(date +%Y%m%d).db

# PostgreSQL
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```
