# Translation Files

Translation files (.po) will be generated here using:

```bash
# Exclude venv directory to avoid scanning third-party packages
# Only Serbian Latin translation file is needed since source strings are in English
python manage.py makemessages -l hr --ignore=venv --ignore=env --ignore=.venv
python manage.py compilemessages
```

**Note:** 
- The `--ignore` flags exclude the virtual environment directory so it won't scan third-party packages
- Only Serbian Latin translation file (`-l sr_Latn`) is needed because source strings in templates are already in English
- When language is set to English, Django uses the source strings directly (no translation file needed)
- Serbian Latin remains the default language (`LANGUAGE_CODE = 'sr-latn'` in settings.py)