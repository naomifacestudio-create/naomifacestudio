# Naomi Face Studio - Web Application

A comprehensive Django web application for a beauty studio featuring treatments, blog posts, reservations, gift vouchers, and contact forms.

## Features

- **Multilingual Support**: Croatian (default) and English
- **Treatment Management**: Admin interface for managing facial treatments with bilingual content
- **Blog System**: Blog posts with pagination and bilingual support
- **Reservation System**: Calendar-based booking with working hours and duration-based blocking
- **Gift Vouchers**: Purchase and email delivery system
- **Contact Forms**: With spam protection (rate limiting + honeypot)
- **Email Notifications**: SendGrid integration for all email communications
- **Cloudflare R2 Storage**: For media files with automatic orphaned file cleanup
- **SEO Optimized**: Modern SEO practices including canonical URLs, meta tags, and structured data
- **Mobile-First Design**: Fully responsive with Tailwind CSS and Flowbite
- **Export/Import**: Backup functionality for treatments and blogs

## Tech Stack

- Django 5.0.1
- PostgreSQL
- Tailwind CSS + Flowbite
- CKEditor 5 (latest)
- SendGrid
- Cloudflare R2
- WhiteNoise (for static files)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd "Naomi Face Studio"
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_NAME=naomi_face_studio
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Cloudflare R2 (optional for local development)
USE_R2=False
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_ENDPOINT_URL=
R2_CUSTOM_DOMAIN=

# SendGrid
SENDGRID_API_KEY=your-sendgrid-api-key
DEFAULT_FROM_EMAIL=info@naomifacestudio.com
ADMIN_EMAIL=info@naomifacestudio.com

# Site Configuration
SITE_URL=https://www.naomifacestudio.com
ALLOWED_HOSTS=localhost,127.0.0.1,naomifacestudio.com,www.naomifacestudio.com
```

5. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Collect static files:
```bash
python manage.py collectstatic --noinput
```

8. Run the development server:
```bash
python manage.py runserver
```

## Project Structure

```
naomi_face_studio/
├── core/              # Core app (home, about us, email collection)
├── treatments/        # Treatment management
├── blogs/            # Blog posts
├── reservations/      # Reservation system
├── gift_vouchers/    # Gift voucher orders
├── contacts/         # Contact form submissions
├── templates/        # HTML templates
├── static/           # Static files (CSS, JS, images)
└── locale/           # Translation files
```

## Key Features Implementation

### Multilingual Support
- Uses Django's i18n framework
- Croatian as default language
- All user-facing content translatable
- Admin fields support both languages

### Reservation System
- Calendar-based booking
- Working hours: Monday (12-20), Tuesday-Friday (9-17), Saturday-Sunday (Closed)
- Duration-based time slot blocking
- User authentication required
- Email notifications for bookings

### Media Management
- Cloudflare R2 integration
- Automatic cleanup of orphaned files
- Support for WebP format
- CDN delivery via Cloudflare

### SEO Features
- Canonical URLs with pagination support
- Meta descriptions per page
- Open Graph and Twitter Card tags
- FAQ JSON-LD structured data
- Sitemap support

## Deployment to Render

1. Push code to Git repository
2. Connect repository to Render
3. Set environment variables in Render dashboard
4. Configure build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
5. Configure start command: `gunicorn naomi_face_studio.wsgi:application`
6. Set up PostgreSQL database in Render
7. Run migrations: `python manage.py migrate`

## Environment Variables for Production

Set these in Render's environment variables:

- `SECRET_KEY`
- `DEBUG=False`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `USE_R2=True`
- R2 credentials
- `SENDGRID_API_KEY`
- `ALLOWED_HOSTS`
- `SITE_URL`

## Admin Features

- Treatment management with bilingual fields
- Blog management with bilingual fields
- Reservation management
- Gift voucher orders
- Contact submissions
- Email collection with export functionality
- Export/Import for backups

## License

Copyright © 2024 Naomi Face Studio. All rights reserved.

