# Translation Files

Translation files (.po) will be generated here using:

```bash
# Exclude venv directory to avoid scanning third-party packages
# Only Croatian translation file is needed since source strings are in English
python manage.py makemessages -l hr --ignore=venv --ignore=env --ignore=.venv
python manage.py compilemessages
```

**Note:** 
- The `--ignore` flags exclude the virtual environment directory so it won't scan third-party packages
- Only Croatian translation file (`-l hr`) is needed because source strings in templates are already in English
- When language is set to English, Django uses the source strings directly (no translation file needed)
- Croatian remains the default language (`LANGUAGE_CODE = 'hr'` in settings.py)

