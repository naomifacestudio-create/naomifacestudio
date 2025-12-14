@echo off
REM Script to run migrations locally with SQLite
echo Running migrations for local development...
python manage.py migrate
pause

