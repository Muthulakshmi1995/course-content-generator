# Course Content Generator (Django + Gemini AI)

A Django learning-management application that generates course notes, key points, summaries and multiple-choice quizzes with Gemini AI. Students can read course material, submit quizzes, view scores and download study material as PDF.

## Included features

- Teacher-authored course topics
- Gemini-powered notes, key points, summary and MCQ generation
- Quiz, question and answer database models
- Student dashboard and course content pages
- Automatic quiz scoring with answer review
- PDF export using ReportLab and Django `FileResponse`
- Django admin integration
- Model and view tests
- SQLite by default; optional MySQL configuration
- `.env`-based secrets and Gunicorn WSGI entry point

## Requirements

- Python 3.10+
- Internet connection for Gemini API calls
- A Gemini API key from Google AI Studio
- MySQL Server only if you choose MySQL; SQLite works out of the box

## Windows setup (VS Code terminal / PowerShell)

1. Extract the ZIP and open the `course_content_generator` folder in VS Code.
2. Create a virtual environment:

   ```powershell
   python -m venv venv
   ```

3. Activate it:

   ```powershell
   .\\venv\\Scripts\\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt:

   ```cmd
   venv\\Scripts\\activate.bat
   ```

4. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

5. Create your environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

6. Open `.env` and replace `GEMINI_API_KEY` with your own key. Keep the key private. The default database is SQLite, so no MySQL setup is needed to start.

7. Create database tables:

   ```powershell
   python manage.py makemigrations generator
   python manage.py migrate
   ```

8. Create an admin / teacher login:

   ```powershell
   python manage.py createsuperuser
   ```

9. Start the development server:

   ```powershell
   python manage.py runserver
   ```

10. Open `http://127.0.0.1:8000/` and sign in using the superuser account. Use **Generate Course** to create a course. The admin site is at `http://127.0.0.1:8000/admin/`.

## macOS / Linux setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your Gemini API key
python manage.py makemigrations generator
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Use MySQL instead of SQLite (optional)

1. Create a MySQL database, for example:

   ```sql
   CREATE DATABASE course_content_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. In `.env`, set:

   ```env
   DB_ENGINE=mysql
   DB_NAME=course_content_db
   DB_USER=your_mysql_username
   DB_PASSWORD=your_mysql_password
   DB_HOST=127.0.0.1
   DB_PORT=3306
   ```

3. Ensure MySQL Server is running, then run:

   ```bash
   python manage.py migrate
   ```

PyMySQL is included as the MySQL database driver. If your MySQL server uses a different host or port, update the `.env` values.

## Tests

Run the full test suite:

```bash
python manage.py test
```

Tests cover model relationships and CRUD/cascade behavior, course generation (using a mocked AI response so no API key is needed), dashboard/content pages, quiz scoring and PDF response headers.

## Production checklist

Do not deploy with the example secret key. Set strong values in the deployment environment:

```env
DJANGO_SECRET_KEY=your-long-random-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com
```

Then run:

```bash
python manage.py collectstatic --noinput
gunicorn content_gen.wsgi:application
```

Configure HTTPS, a production database, static-file serving, backups and environment variables in your hosting platform. `DEBUG=False` is intentionally controlled through `.env` so local development remains convenient.

## Notes / troubleshooting

- If course generation reports a missing API key, check `.env` and restart the server.
- If Gemini reports quota, billing or model access errors, check your Google AI Studio project and account limits.
- The Gemini model is configurable with `GEMINI_MODEL`; the default is `gemini-2.5-flash`.
- Login is required to view courses, generate content, submit quizzes and export PDFs.
- The generated material is educational support. Review AI-generated content for accuracy before teaching or publishing it.
