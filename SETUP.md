# Setup Guide for Naomi Face Studio

## Initial Setup

1. **Install Python 3.11+** if not already installed

2. **Create and activate virtual environment:**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Database Setup (Optional for local development):**
   - **For local development**: SQLite is used by default (no setup needed!)
   - **For PostgreSQL locally**: Install PostgreSQL and create a database, then set `USE_POSTGRES=True` in `.env`
   - See `LOCAL_DEVELOPMENT.md` for details

5. **Create `.env` file** in the root directory:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database (SQLite is default for local - no setup needed!)
# Set USE_POSTGRES=True only if you want PostgreSQL locally
USE_POSTGRES=False
# DB_NAME=naomi_face_studio
# DB_USER=postgres
# DB_PASSWORD=your-password
# DB_HOST=localhost
# DB_PORT=5432

USE_R2=False
SENDGRID_API_KEY=your-sendgrid-api-key
DEFAULT_FROM_EMAIL=info@naomifacestudio.com
ADMIN_EMAIL=info@naomifacestudio.com
SITE_URL=http://localhost:8000
ALLOWED_HOSTS=localhost,127.0.0.1
```

6. **Run migrations (SQLite will be created automatically):**
```bash
python manage.py makemigrations
python manage.py migrate
```

   **Note:** SQLite database file (`db.sqlite3`) will be created automatically - no database setup needed!

7. **Create superuser:**
```bash
python manage.py createsuperuser
```

8. **Collect static files:**
```bash
python manage.py collectstatic --noinput
```

9. **Generate translation files:**
```bash
python manage.py makemessages -l hr
python manage.py makemessages -l en
python manage.py compilemessages
```

10. **Add required static files:**
   - Place logo.png in `static/images/`
   - Place croatia-flag.png in `static/images/`
   - Place uk-flag.png in `static/images/`
   - Place favicon.ico in `static/images/`
   - Place og-image.jpg in `static/images/`
   - Place company-logo.png in `static/images/`

11. **Run development server:**
```bash
python manage.py runserver
```

## Admin Setup

1. Access admin at: `http://localhost:8000/admin/`
2. Login with superuser credentials
3. Start creating:
   - Treatments (with Croatian and English content)
   - Blog posts (with Croatian and English content)

## Production Deployment (Render)

1. Push code to Git repository
2. Connect repository to Render
3. Set environment variables in Render dashboard
4. Configure PostgreSQL database in Render
5. Set up Cloudflare R2 bucket and configure credentials
6. Deploy!

## Important Notes

- **CKEditor**: Latest version is configured. Images uploaded through CKEditor will be stored in R2 when `USE_R2=True`
- **Email Collection**: All emails from contact forms and user registrations are automatically collected
- **File Cleanup**: Orphaned files are automatically deleted from R2 when treatments/blogs are deleted or updated
- **Reservations**: Users must create accounts before booking. The system redirects to login if not authenticated
- **Working Hours**: Configured in `reservations/models.py` - Reservation.get_working_hours()

## Troubleshooting

- If static files don't load: Run `python manage.py collectstatic`
- If translations don't work: Run `python manage.py compilemessages`
- If R2 uploads fail: Check credentials and bucket configuration
- If emails don't send: Verify SendGrid API key

