# Local Development Guide

## Database Setup

For local development, the project uses **SQLite** by default (no setup required). For production on Render, it uses **PostgreSQL**.

### Local Development (SQLite - Default)

1. **No database setup needed!** SQLite uses a file (`db.sqlite3`) that is created automatically.

2. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

4. **Start development server:**
   ```bash
   python manage.py runserver
   ```

### Using PostgreSQL Locally (Optional)

If you want to use PostgreSQL locally (to match production environment):

1. **Install PostgreSQL** on your machine

2. **Create a database:**
   ```sql
   CREATE DATABASE naomi_face_studio;
   ```

3. **Update `.env` file:**
   ```env
   USE_POSTGRES=True
   DB_NAME=naomi_face_studio
   DB_USER=postgres
   DB_PASSWORD=your-password
   DB_HOST=localhost
   DB_PORT=5432
   ```

4. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

## Workflow: Making Changes and Deploying

### Step 1: Make Changes Locally

1. Edit your models in `models.py` files
2. Run `python manage.py makemigrations` to create migration files
3. Run `python manage.py migrate` to apply migrations locally
4. Test your changes locally

### Step 2: Commit and Push to Git

```bash
git add .
git commit -m "Add new model/field"
git push origin main
```

### Step 3: Deploy to Render

1. Render will automatically deploy when you push to Git
2. After deployment, go to Render Dashboard → Your Service → Shell
3. Run migrations in Render shell:
   ```bash
   python manage.py migrate
   ```

## Quick Commands

### Windows (PowerShell)
```powershell
# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver
```

### Or use the batch scripts:
```powershell
.\scripts\makemigrations.bat
.\scripts\migrate.bat
```

### Linux/Mac
```bash
# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver
```

### Or use the shell scripts:
```bash
chmod +x scripts/*.sh
./scripts/makemigrations.sh
./scripts/migrate.sh
```

## Important Notes

- **SQLite is fine for local development** - it's simpler and requires no setup
- **Migration files are version controlled** - they go to Git and are applied on Render
- **Always test migrations locally** before pushing to Git
- **Never commit `db.sqlite3`** - it's in `.gitignore`
- **Render uses PostgreSQL** - migrations work the same way, just different database

## Troubleshooting

### Migration conflicts
If you have migration conflicts:
```bash
# Reset migrations (LOCAL ONLY - never do this in production)
python manage.py migrate --fake-initial
```

### Reset local database
```bash
# Delete SQLite database
rm db.sqlite3  # Linux/Mac
del db.sqlite3  # Windows

# Recreate
python manage.py migrate
python manage.py createsuperuser
```

