# Naomi Face Studio - Comprehensive Case Study

## Executive Summary

**Naomi Face Studio** is a comprehensive Django-based web application designed for a premium beauty studio in Croatia. The platform provides a complete digital solution for managing facial treatments, blog content, online reservations, gift vouchers, and customer communications. Built with modern web technologies and best practices, the application serves both Croatian and English-speaking customers with a fully bilingual interface.

**Key Highlights:**
- **Platform Type:** B2C E-commerce & Booking System
- **Primary Market:** Croatia (with English support)
- **Technology:** Django 5.0.1, PostgreSQL, Cloudflare R2, SendGrid
- **Deployment:** Render.com (Cloud Platform)
- **Development Timeline:** Modern Django application with production-ready features

---

## 1. Project Overview

### 1.1 Business Context

Naomi Face Studio is a premium facial treatment studio offering:
- Professional facial treatments with varying durations
- Educational content and beauty tips
- Blog posts about skincare and beauty
- Online appointment booking system
- Gift voucher sales and delivery
- Customer relationship management

### 1.2 Project Objectives

1. **Digital Presence:** Establish a professional online presence for the beauty studio
2. **Booking System:** Enable customers to book appointments online with real-time availability
3. **Content Management:** Provide easy-to-use admin interface for managing treatments, blogs, and educational content
4. **Multilingual Support:** Serve both Croatian and English-speaking customers
5. **E-commerce:** Enable gift voucher sales with automated email delivery
6. **SEO Optimization:** Ensure high visibility in search engines
7. **Mobile-First Design:** Provide excellent user experience on all devices

### 1.3 Target Audience

- **Primary:** Croatian-speaking customers seeking facial treatments
- **Secondary:** English-speaking expatriates and tourists in Croatia
- **User Types:** 
  - End customers (booking appointments, purchasing vouchers)
  - Admin staff (managing content and reservations)

---

## 2. Technical Architecture

### 2.1 System Architecture

The application follows a **Model-View-Template (MVT)** architecture pattern using Django:

```
┌─────────────────────────────────────────────────────────┐
│                    Client Browser                        │
│              (Desktop, Tablet, Mobile)                    │
└────────────────────┬──────────────────────────────────────┘
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Render.com (Web Server)                 │
│              Gunicorn + Django Application                │
└────────────────────┬──────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
┌─────────────┐ ┌──────────┐ ┌──────────────┐
│ PostgreSQL  │ │Cloudflare│ │  SendGrid    │
│  Database   │ │    R2     │ │   Email API  │
│             │ │  Storage  │ │              │
└─────────────┘ └──────────┘ └──────────────┘
```

### 2.2 Application Structure

The project is organized into modular Django apps:

```
naomi_face_studio/
├── core/              # Core functionality (home, about, email collection)
├── treatments/        # Treatment management and display
├── blogs/            # Blog post management
├── education/        # Educational content management
├── reservations/      # Booking system
├── gift_vouchers/    # Gift voucher orders
├── contacts/         # Contact form submissions
├── templates/        # HTML templates (29 files)
├── static/           # Static files (CSS, JS, images)
└── locale/           # Translation files (Croatian)
```

### 2.3 Technology Stack

#### Backend
- **Framework:** Django 5.0.1
- **Database:** PostgreSQL (production), SQLite (development)
- **Python Version:** 3.x (specified in runtime.txt)
- **WSGI Server:** Gunicorn 21.2.0

#### Frontend
- **CSS Framework:** Tailwind CSS
- **UI Components:** Flowbite 2.3.0
- **Rich Text Editor:** CKEditor 5 (latest)
- **JavaScript:** Vanilla JS with Flowbite components

#### Third-Party Services
- **Cloud Storage:** Cloudflare R2 (S3-compatible)
- **Email Service:** SendGrid
- **Hosting:** Render.com
- **CDN:** Cloudflare (via custom domain)

#### Django Packages
- `django-modeltranslation` - Multilingual content management
- `django-ckeditor` - Rich text editing
- `django-storages` + `boto3` - Cloud storage integration
- `django-ratelimit` - Rate limiting for forms
- `django-honeypot` - Spam protection
- `django-import-export` - Data backup/restore
- `whitenoise` - Static file serving

---

## 3. Core Features & Implementation

### 3.1 Multilingual Support

**Implementation:**
- Uses Django's built-in internationalization (i18n) framework
- Croatian (`hr`) as default language
- English (`en`) as secondary language
- Language switching via URL patterns and session-based selection

**Technical Details:**
- All user-facing strings use Django's translation system
- Models have separate fields for each language (e.g., `title_hr`, `title_en`)
- Admin interface supports bilingual content entry
- Language switcher in header (flag icons)
- URL patterns support language prefixes via `i18n_patterns`

**Code Example:**
```python
# settings.py
LANGUAGE_CODE = 'hr'
LANGUAGES = [
    ('hr', 'Croatian'),
    ('en', 'English'),
]

# Model example
class Treatment(models.Model):
    title_hr = models.CharField(_('Title (Croatian)'), max_length=200)
    title_en = models.CharField(_('Title (English)'), max_length=200)
    slug_hr = models.SlugField(_('Slug (Croatian)'), max_length=200, unique=True)
    slug_en = models.SlugField(_('Slug (English)'), max_length=200, unique=True)
```

### 3.2 Treatment Management System

**Features:**
- Bilingual treatment listings with detailed descriptions
- Rich text content using CKEditor
- Duration-based scheduling (hours and minutes)
- Pause periods after treatments (for staff rest time)
- Pricing information
- Thumbnail images with WebP support
- Active/inactive status for treatments

**Model Structure:**
```python
class Treatment(models.Model):
    # Croatian fields
    title_hr, slug_hr, short_description_hr, full_description_hr, meta_description_hr
    # English fields
    title_en, slug_en, short_description_en, full_description_en, meta_description_en
    # Common fields
    duration_hours, duration_minutes
    pause_hours, pause_minutes  # Hidden from users, used for scheduling
    price, thumbnail, is_active
```

**Key Methods:**
- `get_total_minutes()` - Calculate total treatment duration
- `get_total_pause_minutes()` - Calculate rest period
- `get_absolute_url(language_code)` - Generate language-specific URLs

### 3.3 Reservation System

**Overview:**
A sophisticated calendar-based booking system with intelligent time slot management.

**Working Hours Configuration:**
- **Monday:** 12:00 - 20:00
- **Tuesday - Friday:** 09:00 - 17:00
- **Saturday - Sunday:** Closed

**Key Features:**

1. **Real-Time Availability:**
   - 15-minute interval time slots
   - Automatic calculation based on treatment duration
   - Respects pause periods between treatments
   - Prevents double-booking
   - Blocks past time slots

2. **Time Slot Calculation:**
   ```python
   # Generates available slots considering:
   # - Working hours for the day
   # - Existing reservations
   # - Treatment duration
   # - Pause periods after treatments
   # - Current time (blocks past slots)
   ```

3. **Reservation States:**
   - `pending` - Awaiting confirmation
   - `confirmed` - Confirmed booking
   - `cancelled` - Cancelled reservation
   - `completed` - Treatment completed

4. **User Experience:**
   - Interactive calendar interface
   - AJAX-based slot loading
   - Real-time availability updates
   - User authentication required
   - Email notifications on booking

**Technical Implementation:**
- `Reservation.get_working_hours(day_of_week)` - Returns working hours for specific day
- `Reservation.is_available(date, start_time, treatment)` - Validates slot availability
- `get_available_slots()` - API endpoint returning JSON with available times
- Automatic `end_time` calculation based on treatment duration

**Email Notifications:**
- Confirmation email to customer
- Notification email to admin
- Bilingual email templates based on user's language preference

### 3.4 Blog System

**Features:**
- Bilingual blog posts with rich text content
- Pagination support
- SEO-optimized URLs with language-specific slugs
- Thumbnail images
- Meta descriptions for SEO
- Active/inactive status
- Created/updated timestamps

**Content Management:**
- CKEditor for rich text editing
- Image uploads via CKEditor
- Automatic image cleanup when posts are deleted
- Export/import functionality for backups

### 3.5 Gift Voucher System

**Features:**
- Purchase vouchers for specific treatments
- Email delivery options:
  - Send to purchaser's email
  - Send to recipient's email
- Personalization:
  - Recipient name
  - Personal message
  - From name
- Customer information collection:
  - Purchaser details (name, email, mobile)
  - Recipient details (name, email if different)

**Workflow:**
1. Customer selects treatment
2. Fills in voucher details
3. Chooses email delivery option
4. System creates voucher record
5. Email sent automatically via SendGrid
5. Admin can track sent status

### 3.6 Contact Form System

**Security Features:**
- **Honeypot Field:** Hidden field to catch bots (`django-honeypot`)
- **Rate Limiting:** Prevents spam submissions (`django-ratelimit`)
- **CSRF Protection:** Django's built-in CSRF tokens

**Features:**
- Email collection for marketing
- Automatic email notifications to admin
- Form submission tracking
- Email deduplication via `EmailCollection` model

### 3.7 Email Collection System

**Purpose:**
Centralized email collection from multiple sources for marketing and communication.

**Collection Points:**
- User registration
- Contact form submissions
- Reservation bookings
- Gift voucher purchases

**Features:**
- Automatic deduplication
- Source tracking (where email was collected)
- User profile linking
- Export functionality for marketing campaigns

**Implementation:**
```python
EmailCollection.collect_email(
    email=email,
    source='Reservation',  # or 'Contact Form', 'User Registration', etc.
    first_name=first_name,
    last_name=last_name,
    mobile=mobile,
    user=user,
    update_user_info=False
)
```

---

## 4. Media Management & Cloud Storage

### 4.1 Cloudflare R2 Integration

**Why R2?**
- S3-compatible API (familiar development experience)
- Cost-effective cloud storage
- CDN integration via Cloudflare
- Custom domain support
- Automatic file cleanup

**Implementation:**

1. **Custom Storage Backend:**
   ```python
   class R2Storage(S3Boto3Storage):
       location = 'media'
       default_acl = 'public-read'
       
       def url(self, name):
           # Uses custom domain if configured
           # Falls back to endpoint URL
   ```

2. **Configuration:**
   - Environment-based activation (`USE_R2` flag)
   - Custom domain support for CDN delivery
   - Automatic URL generation
   - Local fallback for development

3. **File Organization:**
   ```
   media/
   ├── treatments/thumbnails/
   ├── blogs/thumbnails/
   ├── education/thumbnails/
   └── uploads/  (CKEditor uploads)
   ```

### 4.2 Automatic Orphaned File Cleanup

**Problem Solved:**
When content is deleted or updated, associated media files can become orphaned, wasting storage space and increasing costs.

**Solution:**
- Signal-based cleanup on model deletion
- Scans HTML content for image references
- Identifies unused files in uploads folder
- Automatic deletion from R2 storage
- Logging of cleanup operations

**Implementation:**
- `pre_delete` signals on Blog, Treatment, Education models
- `cleanup_orphaned_ckeditor_uploads()` function
- HTML parsing to extract image URLs
- Comparison with R2 bucket contents
- Safe deletion with error handling

**Code Flow:**
```python
@receiver(pre_delete, sender=Blog)
def delete_blog_files(sender, instance, **kwargs):
    # Extract image URLs from HTML content
    # Delete thumbnail
    # Delete all referenced images from R2
    # Clean up orphaned uploads
```

---

## 5. SEO Implementation

### 5.1 On-Page SEO

**Meta Tags:**
- Unique meta descriptions per page
- Language-specific meta descriptions
- Open Graph tags for social sharing
- Twitter Card tags
- Canonical URLs (prevents duplicate content)

**Implementation:**
```html
<!-- Base template structure -->
<meta name="description" content="{% block meta_description %}{% endblock %}">
<meta property="og:title" content="{% block og_title %}{% endblock %}">
<meta property="og:description" content="{% block og_description %}{% endblock %}">
<link rel="canonical" href="{% block canonical_url %}{% endblock %}">
```

**URL Structure:**
- Language-specific slugs (e.g., `/treatments/facial-treatment/` vs `/en/treatments/facial-treatment/`)
- SEO-friendly URLs
- Pagination support in canonical URLs

### 5.2 Structured Data

**JSON-LD Implementation:**
- FAQ structured data (where applicable)
- Organization schema
- Breadcrumb navigation
- Article schema for blog posts

### 5.3 Sitemap Support

- Django's sitemap framework configured
- Automatic generation of sitemap.xml
- Includes all active content (treatments, blogs, education)

### 5.4 Performance SEO

- WebP image format support
- CDN delivery via Cloudflare
- Optimized static file serving (WhiteNoise)
- Mobile-first responsive design

---

## 6. Security Features

### 6.1 Application Security

**Django Security Middleware:**
- XSS protection (`SECURE_BROWSER_XSS_FILTER`)
- Content type sniffing protection (`SECURE_CONTENT_TYPE_NOSNIFF`)
- Clickjacking protection (`X_FRAME_OPTIONS = 'DENY'`)

**Production Security (when `DEBUG=False`):**
- HTTPS redirect (`SECURE_SSL_REDIRECT`)
- Secure cookies (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`)
- HSTS headers (`SECURE_HSTS_SECONDS = 31536000`)
- HSTS subdomain inclusion
- HSTS preload support

### 6.2 Form Security

**Contact Form Protection:**
- **Honeypot:** Hidden field named `website` to catch bots
- **Rate Limiting:** Prevents excessive form submissions
- **CSRF Tokens:** All forms protected with CSRF tokens

**Authentication:**
- Django's built-in user authentication
- Password validation (strength requirements)
- Session management (24-hour sessions)

### 6.3 Data Protection

- Environment variables for sensitive data
- Secret key management
- Database credentials in environment variables
- API keys stored securely

---

## 7. Database Design

### 7.1 Core Models

**User & Profile:**
- `User` (Django's built-in)
- `UserProfile` (extended user information)
- `EmailCollection` (marketing email database)

**Content Models:**
- `Treatment` - Facial treatment details
- `Blog` - Blog posts
- `Education` - Educational content
- All support bilingual fields

**Business Models:**
- `Reservation` - Appointment bookings
- `GiftVoucher` - Gift voucher orders
- `Contact` - Contact form submissions

### 7.2 Relationships

```
User ──┬──> UserProfile (OneToOne)
       │
       ├──> Reservation (ForeignKey)
       │
       └──> EmailCollection (ForeignKey, nullable)

Treatment ──┬──> Reservation (ForeignKey)
            │
            └──> GiftVoucher (ForeignKey)
```

### 7.3 Database Features

- **PostgreSQL** in production (scalable, robust)
- **SQLite** in development (easy setup)
- Automatic migrations
- Indexes on frequently queried fields
- Unique constraints (e.g., `unique_together` on Reservation date+time)

---

## 8. User Interface & Design

### 8.1 Design System

**Framework:** Tailwind CSS
- Utility-first CSS framework
- Responsive design utilities
- Custom color scheme (brown/gold theme: `#593d09`)

**Component Library:** Flowbite
- Pre-built UI components
- Interactive elements (modals, dropdowns, carousels)
- Mobile-friendly navigation

### 8.2 Responsive Design

**Breakpoints:**
- Mobile-first approach
- Tablet and desktop optimizations
- Hamburger menu for mobile
- Desktop navigation bar

**Features:**
- Touch-friendly buttons
- Responsive images
- Mobile-optimized forms
- Adaptive layouts

### 8.3 User Experience

**Navigation:**
- Language switcher (flag icons)
- Main menu (Treatments, Education, Blog, etc.)
- User account menu (when logged in)
- Mobile offcanvas menu

**Interactive Elements:**
- Calendar-based booking interface
- Real-time slot availability
- AJAX form submissions
- Loading states and feedback
- Success/error messages

**Accessibility:**
- Semantic HTML
- ARIA labels where needed
- Keyboard navigation support
- Alt text for images

---

## 9. Email System

### 9.1 SendGrid Integration

**Configuration:**
- SMTP backend via SendGrid
- API key authentication
- TLS encryption
- Custom from email address

**Email Types:**
1. **Reservation Confirmations:**
   - Customer confirmation
   - Admin notification
   - Bilingual templates

2. **Gift Voucher Delivery:**
   - Automated voucher emails
   - Personalized messages
   - Treatment details

3. **Contact Form Notifications:**
   - Admin alerts
   - Customer acknowledgments

### 9.2 Email Features

- HTML email templates
- Language-specific content
- Professional branding
- Delivery tracking (via SendGrid dashboard)

---

## 10. Deployment & Infrastructure

### 10.1 Hosting Platform: Render.com

**Why Render?**
- Easy Django deployment
- PostgreSQL database integration
- Environment variable management
- Automatic SSL certificates
- Git-based deployments

**Configuration:**
- `render.yaml` for infrastructure as code
- Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- Start command: `gunicorn naomi_face_studio.wsgi:application`
- Automatic database linking

### 10.2 Environment Configuration

**Development:**
- SQLite database (no setup required)
- Local file storage
- Debug mode enabled
- Console email backend

**Production:**
- PostgreSQL database
- Cloudflare R2 storage
- SendGrid email
- Debug mode disabled
- Security headers enabled
- Custom domain with SSL

### 10.3 Static Files

**Development:**
- Served by Django development server
- Local file system

**Production:**
- WhiteNoise middleware for static files
- `collectstatic` during build
- CDN for media files (Cloudflare R2)

### 10.4 Monitoring & Logging

**Logging Configuration:**
- Console logging (development)
- File logging for errors (`logs/django_errors.log`)
- Application-specific loggers
- Log levels: DEBUG (dev), INFO (production)

**Startup Logging:**
- Database connection info
- Storage configuration
- Email backend status
- Environment details

---

## 11. Development Workflow

### 11.1 Local Development Setup

**Requirements:**
1. Python virtual environment
2. `.env` file with configuration
3. Database migrations
4. Superuser creation
5. Static file collection

**Scripts:**
- `makemigrations.bat/sh` - Create migrations
- `migrate.bat/sh` - Apply migrations
- `manage_local.py` - Local development management

### 11.2 Code Organization

**Best Practices:**
- Modular app structure
- Separation of concerns
- Reusable components
- Signal-based cleanup
- Environment-based configuration

**File Structure:**
- Models in `models.py`
- Views in `views.py`
- URLs in `urls.py`
- Templates in `templates/` directory
- Static files in `static/` directory

### 11.3 Data Management

**Export/Import:**
- Django Import-Export for treatments and blogs
- CSV/Excel format support
- Backup and restore functionality
- Admin interface integration

---

## 12. Performance Optimizations

### 12.1 Database Optimization

- Indexed fields on frequently queried columns
- Efficient queries (select_related, prefetch_related where needed)
- Database connection pooling (via Render)

### 12.2 Caching

- Local memory cache configured
- Session caching
- Template fragment caching (where applicable)

### 12.3 Static Assets

- WhiteNoise for efficient static file serving
- CDN delivery for media files
- WebP image format (smaller file sizes)
- Optimized CSS/JS delivery

### 12.4 Code Optimization

- Efficient time slot calculation algorithms
- Minimal database queries
- Lazy loading where appropriate
- Pagination for large datasets

---

## 13. Challenges & Solutions

### 13.1 Challenge: Time Slot Management

**Problem:**
Complex scheduling logic considering:
- Variable treatment durations
- Pause periods between treatments
- Working hours that vary by day
- Preventing double bookings
- Blocking past time slots

**Solution:**
- Centralized `get_working_hours()` method
- `is_available()` validation method
- 15-minute interval slot generation
- Timezone-aware datetime handling
- Comprehensive overlap detection

### 13.2 Challenge: Orphaned File Cleanup

**Problem:**
When content is deleted, associated media files remain in cloud storage, increasing costs.

**Solution:**
- Signal-based automatic cleanup
- HTML content parsing to find referenced images
- Comparison with storage bucket contents
- Safe deletion with error handling
- Logging for audit trail

### 13.3 Challenge: Multilingual Content Management

**Problem:**
Managing bilingual content efficiently without duplicating models.

**Solution:**
- Separate fields for each language (`_hr`, `_en` suffixes)
- Helper methods (`get_title()`, `get_slug()`) for language-specific access
- Django's i18n for UI strings
- Language-aware URL generation

### 13.4 Challenge: Spam Prevention

**Problem:**
Contact forms vulnerable to bot submissions.

**Solution:**
- Honeypot field (hidden, catches bots)
- Rate limiting (prevents excessive submissions)
- CSRF protection (Django built-in)
- Email validation

---

## 14. Testing & Quality Assurance

### 14.1 Testing Strategy

**Manual Testing:**
- Reservation system (all scenarios)
- Form submissions
- Email delivery
- File uploads and cleanup
- Language switching
- Mobile responsiveness

**Browser Testing:**
- Chrome, Firefox, Safari, Edge
- Mobile browsers (iOS Safari, Chrome Mobile)

### 14.2 Error Handling

- Graceful error handling
- User-friendly error messages
- Admin error logging
- Email notification for critical errors

---

## 15. Future Enhancements

### 15.1 Potential Features

1. **Payment Integration:**
   - Online payment for treatments
   - Gift voucher payment processing
   - Stripe/PayPal integration

2. **Advanced Booking:**
   - Recurring appointments
   - Waitlist functionality
   - SMS notifications
   - Reminder emails

3. **Customer Portal:**
   - Booking history
   - Treatment history
   - Profile management
   - Loyalty program

4. **Analytics:**
   - Google Analytics integration
   - Booking analytics dashboard
   - Revenue tracking
   - Customer insights

5. **Marketing:**
   - Newsletter system
   - Email campaigns
   - Promotional codes
   - Social media integration

6. **Admin Enhancements:**
   - Advanced reporting
   - Calendar view for reservations
   - Bulk operations
   - Export capabilities

---

## 16. Project Metrics & Statistics

### 16.1 Codebase Statistics

- **Django Apps:** 7 (core, treatments, blogs, education, reservations, gift_vouchers, contacts)
- **Templates:** 29 HTML files
- **Models:** 8+ database models
- **URL Patterns:** Multiple routes per app
- **Static Files:** Images, CSS, JavaScript

### 16.2 Technology Versions

- Django: 5.0.1
- Python: 3.x
- PostgreSQL: Latest (via Render)
- Tailwind CSS: Latest
- Flowbite: 2.3.0
- CKEditor: Latest (6.7.0)

### 16.3 Third-Party Integrations

- **Cloudflare R2:** Media storage
- **SendGrid:** Email delivery
- **Render.com:** Hosting and database
- **Cloudflare CDN:** Content delivery

---

## 17. Conclusion

### 17.1 Project Success Factors

1. **Comprehensive Feature Set:**
   - All business requirements met
   - User-friendly interfaces
   - Admin-friendly content management

2. **Modern Technology Stack:**
   - Latest Django version
   - Industry-standard tools
   - Scalable architecture

3. **Production-Ready:**
   - Security best practices
   - Error handling
   - Logging and monitoring
   - Performance optimizations

4. **Maintainable Code:**
   - Modular structure
   - Clear separation of concerns
   - Well-documented
   - Environment-based configuration

### 17.2 Business Impact

- **Digital Transformation:** Complete online presence
- **Operational Efficiency:** Automated booking and email delivery
- **Customer Experience:** 24/7 booking availability
- **Marketing:** Centralized email collection
- **Scalability:** Cloud-based infrastructure

### 17.3 Technical Achievements

- Sophisticated booking system with intelligent scheduling
- Automated media file management
- Bilingual content management
- Production-ready security
- SEO optimization
- Mobile-first responsive design

---

## Appendix A: Environment Variables

### Required Variables

```env
# Security
SECRET_KEY=your-secret-key-here
DEBUG=True/False

# Database
DATABASE_URL=postgresql://... (or individual DB_* variables)
USE_POSTGRES=True/False

# Cloudflare R2
USE_R2=True/False
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_ENDPOINT_URL=
R2_CUSTOM_DOMAIN=

# SendGrid
SENDGRID_API_KEY=
DEFAULT_FROM_EMAIL=
ADMIN_EMAIL=

# Site Configuration
SITE_URL=
ALLOWED_HOSTS=
```

---

## Appendix B: Key URLs

### Public URLs
- `/` - Home page
- `/treatments/` - Treatment listings
- `/education/` - Educational content
- `/blogs/` - Blog posts
- `/reservations/` - Booking calendar
- `/gift-vouchers/` - Gift voucher purchase
- `/contact/` - Contact form

### Admin URLs
- `/admin/` - Django admin interface
- `/i18n/setlang/` - Language switcher

---

## Appendix C: API Endpoints

### Reservation API
- `GET /reservations/calendar/` - Calendar view
- `GET /reservations/api/available-slots/` - Get available time slots (JSON)
- `POST /reservations/api/create/` - Create reservation (JSON)
- `GET /reservations/my-reservations/` - User's reservations

---

## Document Information

**Version:** 1.0  
**Last Updated:** 2024  
**Author:** Development Team  
**Status:** Final

---

*This case study provides a comprehensive overview of the Naomi Face Studio web application, covering technical architecture, features, implementation details, and business context.*
