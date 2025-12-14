@echo off
REM Script to run makemigrations locally with SQLite
echo Running makemigrations for local development...
python manage.py makemigrations
pause

