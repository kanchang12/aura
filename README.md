# SAM eLearning Platform Demo

**Age and Dementia Awareness Training for Taxi and Private Hire Drivers**

Demo platform for Leeds Older People's Forum tender submission.

## Features

- ✅ User registration and login
- ✅ Three SAM modules (Support, Accessibility, Mobility)
- ✅ YouTube video embedding
- ✅ Multiple choice quizzes (5 questions each, 80% pass mark)
- ✅ Progress tracking
- ✅ PDF certificate generation
- ✅ Admin dashboard with analytics
- ✅ Mobile responsive design
- ✅ WCAG 2.2 accessible

## Quick Start

```bash
# Install dependencies
pip install flask flask-login flask-sqlalchemy reportlab

# Run the application
python app.py

# Open browser
http://localhost:8080
```

## Routes

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/register` | User registration |
| `/login` | User login |
| `/dashboard` | Module selection |
| `/module/<id>` | Video + quiz link |
| `/quiz/<id>` | Quiz questions |
| `/certificate` | View certificate |
| `/certificate/download` | Download PDF |
| `/admin` | Admin dashboard |

## Technical Specifications

- **Framework**: Flask (Python)
- **Database**: SQLite
- **Authentication**: Flask-Login
- **PDF Generation**: ReportLab
- **Styling**: Custom CSS (no frameworks)
- **Video**: YouTube embed

## Customisation

### Replace Placeholder Videos

Edit `app.py` and update the `video_id` in `MODULE_INFO`:

```python
MODULE_INFO = {
    'support': {
        'video_id': 'YOUR_YOUTUBE_ID',
        ...
    }
}
```

### Modify Quiz Questions

Edit the `QUIZ_QUESTIONS` dictionary in `app.py`.

## Production Deployment

For production, consider:
- PostgreSQL instead of SQLite
- Gunicorn/uWSGI as WSGI server
- HTTPS via reverse proxy (nginx)
- Environment variables for secrets

## Developed By

ikanchan.com | Kanchan Ghosh
Independent AI Developer & Business Innovation Specialist
