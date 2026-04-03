# Abhyuday Bharat Food Cluster — Database

## Engine
- **Development**: SQLite  (`database/abfc.db`)  — zero setup, file-based
- **Production**:  PostgreSQL — set `DATABASE_URL` in `.env`

SQLAlchemy is used as the ORM, so the same code works with both.

---

## Tables

### `admin_users`
| Column        | Type        | Notes                     |
|---------------|-------------|---------------------------|
| id            | INTEGER PK  | Auto-increment            |
| username      | VARCHAR(80) | Unique                    |
| password_hash | VARCHAR(256)| bcrypt hash via Werkzeug  |
| created_at    | DATETIME    | UTC                       |

### `categories`
| Column     | Type         | Notes                            |
|------------|--------------|----------------------------------|
| id         | INTEGER PK   |                                  |
| slug       | VARCHAR(80)  | Unique, URL-safe key e.g. `fries`|
| name       | VARCHAR(120) | Display name                     |
| emoji      | VARCHAR(10)  | e.g. 🍟                          |
| active     | BOOLEAN      | Whether shown on website         |
| sort_order | INTEGER      | Display order                    |
| created_at | DATETIME     |                                  |

### `products`
| Column     | Type         | Notes                        |
|------------|--------------|------------------------------|
| id         | INTEGER PK   |                              |
| cat_slug   | VARCHAR(80)  | FK → categories.slug         |
| sub        | VARCHAR(120) | Sub-category label           |
| name       | VARCHAR(200) | Product display name         |
| qty        | VARCHAR(200) | Pack sizes string            |
| img        | VARCHAR(300) | Relative path e.g. src/…    |
| note       | TEXT         | Short description            |
| tags       | TEXT         | JSON array e.g. ["Frozen"]  |
| active     | BOOLEAN      |                              |
| sort_order | INTEGER      |                              |
| created_at | DATETIME     |                              |
| updated_at | DATETIME     | Auto-updated on PUT          |

### `enquiries`
| Column        | Type         | Notes              |
|---------------|--------------|--------------------|
| id            | INTEGER PK   |                    |
| name          | VARCHAR(120) |                    |
| company       | VARCHAR(200) |                    |
| phone         | VARCHAR(40)  |                    |
| email         | VARCHAR(200) |                    |
| business_type | VARCHAR(100) |                    |
| message       | TEXT         |                    |
| seen          | BOOLEAN      | Read by admin?     |
| created_at    | DATETIME     |                    |

### `site_contact`
| Column  | Type         | Notes              |
|---------|--------------|--------------------|
| id      | INTEGER PK   | Always 1 row       |
| address | TEXT         |                    |
| phone   | VARCHAR(40)  |                    |
| email   | VARCHAR(200) |                    |
| hours   | VARCHAR(200) |                    |

### `admin_sessions`
| Column     | Type        | Notes             |
|------------|-------------|-------------------|
| id         | INTEGER PK  |                   |
| token      | VARCHAR(64) | Unique hex token  |
| username   | VARCHAR(80) |                   |
| created_at | DATETIME    |                   |

---

## Seeded Default Data
On first run (`python app.py`) the database is auto-created and seeded with:
- 1 admin user: **admin / admin123**
- 8 default categories
- 68 products (all fries, vegetables, snacks, breads, curries, millets, etc.)
- Default contact info

---

## Backup (SQLite)
```bash
# Simple file copy
cp database/abfc.db database/abfc_backup_$(date +%Y%m%d).db
```

## Backup (PostgreSQL)
```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```
