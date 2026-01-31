from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lopf-demo-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///elearning.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    badge_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    passed = db.Column(db.Boolean, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='results')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Quiz Questions
QUIZ_QUESTIONS = {
    'support': [
        {
            'question': 'What is the best way to communicate with an older passenger who seems confused?',
            'options': ['Speak loudly and quickly', 'Speak clearly, face them, and give them time to respond', 'Ignore them and start driving', 'Ask them to hurry up'],
            'correct': 1
        },
        {
            'question': 'If a passenger with dementia becomes agitated, you should:',
            'options': ['Tell them to calm down', 'Remain calm, speak softly, and reassure them', 'Pull over and ask them to leave', 'Drive faster to end the journey quickly'],
            'correct': 1
        },
        {
            'question': 'A passenger seems lost and cannot remember their destination. What should you do?',
            'options': ['Drop them anywhere', 'Patiently help them, check for emergency contacts, or contact your operator', 'Refuse the fare', 'Drive to the police station immediately'],
            'correct': 1
        },
        {
            'question': 'Which behaviour might indicate early signs of dementia?',
            'options': ['Repeating questions or seeming disoriented', 'Being punctual', 'Having exact change ready', 'Knowing exactly where to go'],
            'correct': 0
        },
        {
            'question': 'Why is patience important when supporting older passengers?',
            'options': ['It is not important', 'They may need extra time to process information and move', 'So you can charge more', 'To fill awkward silence'],
            'correct': 1
        }
    ],
    'accessibility': [
        {
            'question': 'When assisting a passenger with a mobility aid, you should:',
            'options': ['Grab the aid and move it yourself', 'Ask how they would like to be assisted', 'Refuse the booking', 'Leave them to manage alone'],
            'correct': 1
        },
        {
            'question': 'A wheelchair user needs to travel. You should:',
            'options': ['Say your vehicle is not suitable', 'Ensure secure wheelchair fastening and seatbelt use', 'Ask them to sit in a regular seat', 'Charge extra without explanation'],
            'correct': 1
        },
        {
            'question': 'What is an important accessibility feature to check in your vehicle?',
            'options': ['Air freshener', 'Working door handles, ramps, and clear floor space', 'Loud music system', 'Tinted windows'],
            'correct': 1
        },
        {
            'question': 'Assistance dogs must be:',
            'options': ['Refused entry', 'Allowed without extra charge (except for damage)', 'Kept in the boot', 'Only allowed if muzzled'],
            'correct': 1
        },
        {
            'question': 'How can you make your vehicle more accessible for visually impaired passengers?',
            'options': ['Flash your lights', 'Verbally describe where handles and seats are', 'Expect them to find their own way', 'Honk when you arrive'],
            'correct': 1
        }
    ],
    'mobility': [
        {
            'question': 'Safe driving for older passengers means:',
            'options': ['Taking corners quickly to save time', 'Smooth acceleration, braking, and giving advance warning of stops', 'Loud music to keep them alert', 'Driving as fast as possible'],
            'correct': 1
        },
        {
            'question': 'When dropping off a passenger with mobility issues, you should:',
            'options': ['Stop wherever is convenient for you', 'Find a safe, level spot as close to their destination as possible', 'Drop them across the road', 'Leave immediately after they pay'],
            'correct': 1
        },
        {
            'question': 'Why might an older passenger need door-to-door service?',
            'options': ['They are being difficult', 'They may have difficulty walking distances or navigating streets', 'They want to waste your time', 'It costs more'],
            'correct': 1
        },
        {
            'question': 'What should you do if a passenger struggles to fasten their seatbelt?',
            'options': ['Tell them not to bother', 'Offer to help if they would like assistance', 'Drive off anyway', 'Cancel the trip'],
            'correct': 1
        },
        {
            'question': 'Regular bookings from the same older passenger help because:',
            'options': ['You can overcharge them', 'Building familiarity creates trust and better service', 'You can skip safety checks', 'It does not help at all'],
            'correct': 1
        }
    ]
}

MODULE_INFO = {
    'support': {
        'title': 'Support',
        'description': 'Understanding the needs of older passengers and those living with dementia',
        'video_id': 'ZY7onNGRiQ4',  # Placeholder - replace with actual video
        'icon': '🤝'
    },
    'accessibility': {
        'title': 'Accessibility', 
        'description': 'Making your service accessible for all passengers',
        'video_id': 'CT0ar2TiAEA',  # Placeholder - replace with actual video
        'icon': '♿'
    },
    'mobility': {
        'title': 'Mobility',
        'description': 'Safe and comfortable transport for passengers with mobility needs',
        'video_id': 'Hsn9txMNV9c',  # Placeholder - replace with actual video
        'icon': '🚗'
    }
}

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        badge_number = request.form.get('badge_number')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            badge_number=badge_number
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    results = {r.module: r for r in current_user.results}
    return render_template('dashboard.html', modules=MODULE_INFO, results=results)

@app.route('/module/<module_id>')
@login_required
def module(module_id):
    if module_id not in MODULE_INFO:
        flash('Module not found', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('module.html', 
                         module_id=module_id,
                         module=MODULE_INFO[module_id])

@app.route('/quiz/<module_id>', methods=['GET', 'POST'])
@login_required
def quiz(module_id):
    if module_id not in QUIZ_QUESTIONS:
        flash('Quiz not found', 'error')
        return redirect(url_for('dashboard'))
    
    questions = QUIZ_QUESTIONS[module_id]
    
    if request.method == 'POST':
        score = 0
        for i, q in enumerate(questions):
            answer = request.form.get(f'q{i}')
            if answer and int(answer) == q['correct']:
                score += 1
        
        passed = score >= 4  # 80% pass mark
        
        # Save result
        existing = QuizResult.query.filter_by(user_id=current_user.id, module=module_id).first()
        if existing:
            existing.score = score
            existing.total = len(questions)
            existing.passed = passed
            existing.completed_at = datetime.utcnow()
        else:
            result = QuizResult(
                user_id=current_user.id,
                module=module_id,
                score=score,
                total=len(questions),
                passed=passed
            )
            db.session.add(result)
        db.session.commit()
        
        return render_template('quiz_result.html',
                             module=MODULE_INFO[module_id],
                             module_id=module_id,
                             score=score,
                             total=len(questions),
                             passed=passed)
    
    return render_template('quiz.html',
                         module_id=module_id,
                         module=MODULE_INFO[module_id],
                         questions=questions)

@app.route('/certificate')
@login_required
def certificate():
    results = QuizResult.query.filter_by(user_id=current_user.id).all()
    all_passed = len(results) == 3 and all(r.passed for r in results)
    
    if not all_passed:
        flash('Complete all modules to receive your certificate', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('certificate.html', user=current_user)

@app.route('/certificate/download')
@login_required
def download_certificate():
    results = QuizResult.query.filter_by(user_id=current_user.id).all()
    all_passed = len(results) == 3 and all(r.passed for r in results)
    
    if not all_passed:
        flash('Complete all modules to download certificate', 'error')
        return redirect(url_for('dashboard'))
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=28, spaceAfter=30, textColor=colors.HexColor('#1a365d'))
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=16, spaceAfter=20, alignment=1)
    name_style = ParagraphStyle('Name', parent=styles['Title'], fontSize=24, spaceAfter=30, textColor=colors.HexColor('#2c5282'))
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=14, spaceAfter=15, alignment=1)
    
    elements = []
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("CERTIFICATE OF COMPLETION", title_style))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("Age and Dementia Awareness Training", subtitle_style))
    elements.append(Paragraph("for Taxi and Private Hire Drivers", subtitle_style))
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("This is to certify that", body_style))
    elements.append(Paragraph(f"<b>{current_user.full_name}</b>", name_style))
    if current_user.badge_number:
        elements.append(Paragraph(f"Badge Number: {current_user.badge_number}", body_style))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("has successfully completed all three modules of the", body_style))
    elements.append(Paragraph("<b>SAM Training Programme</b>", body_style))
    elements.append(Paragraph("(Support, Accessibility, Mobility)", body_style))
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%d %B %Y')}", body_style))
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("Leeds Older People's Forum", body_style))
    elements.append(Paragraph("in partnership with Motability Foundation", body_style))
    
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'SAM_Certificate_{current_user.full_name.replace(" ", "_")}.pdf',
        mimetype='application/pdf'
    )

@app.route('/admin')
@login_required
def admin():
    # Simple admin - in production would have proper role-based access
    users = User.query.all()
    results = QuizResult.query.all()
    
    stats = {
        'total_users': len(users),
        'completed_support': sum(1 for r in results if r.module == 'support' and r.passed),
        'completed_accessibility': sum(1 for r in results if r.module == 'accessibility' and r.passed),
        'completed_mobility': sum(1 for r in results if r.module == 'mobility' and r.passed),
        'fully_certified': len([u for u in users if len([r for r in u.results if r.passed]) == 3])
    }
    
    return render_template('admin.html', users=users, stats=stats)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=8080)
