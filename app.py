from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///ecotrack.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=False)

# Google Maps API Key (set as environment variable)
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255))
    city = db.Column(db.String(100), default='Kathmandu')
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    waste_entries = db.relationship('WasteEntry', backref='user', lazy=True)
    chat_messages = db.relationship('ChatMessage', backref='user', lazy=True)
    waste_goals = db.relationship('WasteGoal', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    achievements = db.relationship('Achievement', backref='user', lazy=True)

class WasteEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    waste_type = db.Column(db.String(50), nullable=False)  # organic, recyclable, hazardous, other
    weight_kg = db.Column(db.Float)
    description = db.Column(db.Text)
    disposal_date = db.Column(db.DateTime, default=datetime.utcnow)
    recycled = db.Column(db.Boolean, default=False)
    recycling_center_id = db.Column(db.Integer, db.ForeignKey('recycling_center.id'))

class RecyclingCenter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), default='Kathmandu')
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(255))
    accepts_types = db.Column(db.String(255))  # comma-separated waste types
    hours = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    waste_entries = db.relationship('WasteEntry', backref='recycling_center', lazy=True)
    pickup_schedules = db.relationship('PickupSchedule', backref='recycling_center', lazy=True)

class PickupSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recycling_center_id = db.Column(db.Integer, db.ForeignKey('recycling_center.id'), nullable=False)
    area = db.Column(db.String(200), nullable=False)
    pickup_day = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, etc.
    pickup_time = db.Column(db.String(20))  # e.g., "09:00 AM"
    waste_types = db.Column(db.String(255))
    frequency = db.Column(db.String(50), default='weekly')
    is_active = db.Column(db.Boolean, default=True)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class WasteGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    goal_type = db.Column(db.String(50), nullable=False)  # reduce, recycle, track
    target_value = db.Column(db.Float, nullable=False)
    current_value = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default='kg')
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='info')  # info, reminder, achievement
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    link = db.Column(db.String(255))  # Optional link to related page

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_type = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        address = request.form.get('address', '')
        city = request.form.get('city', 'Kathmandu')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Geocode address if provided
        lat, lng = None, None
        if address and GOOGLE_MAPS_API_KEY:
            lat, lng = geocode_address(f"{address}, {city}, Nepal")
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            address=address,
            city=city,
            latitude=lat,
            longitude=lng
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            session['user_id'] = user.id
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's recent waste entries
    recent_entries = WasteEntry.query.filter_by(user_id=current_user.id)\
        .order_by(WasteEntry.disposal_date.desc()).limit(5).all()
    
    # Get statistics
    total_entries = WasteEntry.query.filter_by(user_id=current_user.id).count()
    recycled_count = WasteEntry.query.filter_by(user_id=current_user.id, recycled=True).count()
    
    # Get nearby recycling centers
    if current_user.latitude is not None and current_user.longitude is not None:
        nearby_centers = get_nearby_recycling_centers(current_user.latitude, current_user.longitude, limit=5)
    else:
        nearby_centers = []  # empty list if no coordinates
    
    # Get user achievements
    achievements = Achievement.query.filter_by(user_id=current_user.id)\
        .order_by(Achievement.unlocked_at.desc()).limit(5).all()
    
    # Get active goals
    active_goals = WasteGoal.query.filter_by(user_id=current_user.id, is_completed=False).limit(3).all()
    
    # Get unread notifications count
    unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return render_template('dashboard.html', 
                         recent_entries=recent_entries,
                         total_entries=total_entries,
                         recycled_count=recycled_count,
                         nearby_centers=nearby_centers,
                         achievements=achievements,
                         active_goals=active_goals,
                         unread_notifications=unread_notifications,
                         google_maps_api_key=GOOGLE_MAPS_API_KEY)

@app.route('/track-waste', methods=['GET', 'POST'])
@login_required
def track_waste():
    if request.method == 'POST':
        waste_type = request.form.get('waste_type')
        weight_kg = request.form.get('weight_kg', type=float)
        description = request.form.get('description', '')
        recycled = bool(request.form.get('recycled'))
        
        # Auto-mark recyclable waste as recycled if not explicitly set
        if waste_type == 'recyclable' and not recycled:
            recycled = True
        
        entry = WasteEntry(
            user_id=current_user.id,
            waste_type=waste_type,
            weight_kg=weight_kg,
            description=description,
            recycled=recycled
        )
        db.session.add(entry)
        db.session.commit()
        
        # Check for achievements
        check_and_create_achievements(current_user.id)
        
        # Update goals progress
        update_goals_progress(current_user.id)
        
        flash('Waste entry added successfully!', 'success')
        return redirect(url_for('track_waste'))
    
    entries = WasteEntry.query.filter_by(user_id=current_user.id)\
        .order_by(WasteEntry.disposal_date.desc()).all()
    
    return render_template('track_waste.html', entries=entries)

@app.route('/toggle-recycled/<int:entry_id>', methods=['POST'])
@login_required
def toggle_recycled(entry_id):
    """Toggle recycled status of a waste entry"""
    entry = WasteEntry.query.get_or_404(entry_id)
    
    # Ensure user owns this entry
    if entry.user_id != current_user.id:
        flash('Unauthorized action', 'error')
        return redirect(url_for('track_waste'))
    
    entry.recycled = not entry.recycled
    db.session.commit()
    
    # Update goals and achievements
    check_and_create_achievements(current_user.id)
    update_goals_progress(current_user.id)
    
    flash(f'Entry marked as {"recycled" if entry.recycled else "not recycled"}', 'success')
    return redirect(url_for('track_waste'))

@app.route('/recycling-centers')
@login_required
def recycling_centers():
    centers = RecyclingCenter.query.filter_by(is_active=True).all()
    
    # If user has location, sort by distance
    if current_user.latitude and current_user.longitude:
        centers = sorted(centers, key=lambda c: calculate_distance(
            current_user.latitude, current_user.longitude,
            c.latitude, c.longitude
        ))
    
    return render_template('recycling_centers.html', 
                         centers=centers,
                         user_lat=current_user.latitude,
                         user_lng=current_user.longitude,
                         google_maps_api_key=GOOGLE_MAPS_API_KEY)

@app.route('/pickup-schedules')
@login_required
def pickup_schedules():
    schedules = PickupSchedule.query.filter_by(is_active=True).all()
    
    # Filter by user's city if available
    if current_user.city:
        schedules = [s for s in schedules if current_user.city.lower() in s.area.lower()]
    
    return render_template('pickup_schedules.html', schedules=schedules)

@app.route('/waste-tips')
def waste_tips():
    tips = {
        'organic': [
            'Compost food scraps and yard waste',
            'Use biodegradable bags for organic waste',
            'Avoid mixing organic waste with recyclables',
            'Create a home compost bin if possible'
        ],
        'recyclable': [
            'Clean containers before recycling',
            'Remove labels and caps when possible',
            'Separate different types of recyclables',
            'Check local recycling guidelines',
            'Flatten cardboard boxes to save space'
        ],
        'hazardous': [
            'Never mix hazardous waste with regular trash',
            'Take batteries to designated collection points',
            'Dispose of electronics at certified e-waste centers',
            'Keep hazardous materials in original containers',
            'Contact local authorities for proper disposal'
        ],
        'other': [
            'Reduce waste by buying in bulk',
            'Reuse items when possible',
            'Donate items in good condition',
            'Choose products with minimal packaging'
        ]
    }
    return render_template('waste_tips.html', tips=tips)

@app.route('/statistics')
@login_required
def statistics():
    """Detailed statistics page with charts"""
    # Get all user's waste entries
    entries = WasteEntry.query.filter_by(user_id=current_user.id).all()
    
    # Calculate statistics
    total_entries = len(entries)
    total_weight = sum(e.weight_kg or 0 for e in entries)
    recycled_count = sum(1 for e in entries if e.recycled)
    recycled_weight = sum(e.weight_kg or 0 for e in entries if e.recycled)
    
    # Group by waste type
    waste_by_type = {}
    for entry in entries:
        waste_type = entry.waste_type
        if waste_type not in waste_by_type:
            waste_by_type[waste_type] = {'count': 0, 'weight': 0}
        waste_by_type[waste_type]['count'] += 1
        waste_by_type[waste_type]['weight'] += entry.weight_kg or 0
    
    # Monthly statistics
    monthly_stats = {}
    for entry in entries:
        month_key = entry.disposal_date.strftime('%Y-%m')
        if month_key not in monthly_stats:
            monthly_stats[month_key] = {'count': 0, 'weight': 0}
        monthly_stats[month_key]['count'] += 1
        monthly_stats[month_key]['weight'] += entry.weight_kg or 0
    
    # Environmental impact (rough estimates)
    # Calculate CO2 saved based on waste type
    co2_saved = 0
    trees_saved = 0
    
    for entry in entries:
        if entry.recycled and entry.weight_kg:
            weight = entry.weight_kg
            # Different waste types have different CO2 savings
            if entry.waste_type == 'recyclable':
                # Recyclable: 1 kg ≈ 0.6 kg CO2 saved
                co2_saved += weight * 0.6
                # Paper/plastic recycling saves trees
                trees_saved += (weight / 1000) * 17
            elif entry.waste_type == 'organic':
                # Organic waste composting: 1 kg ≈ 0.3 kg CO2 saved
                co2_saved += weight * 0.3
            elif entry.waste_type == 'hazardous':
                # Proper hazardous waste disposal: 1 kg ≈ 0.8 kg CO2 saved
                co2_saved += weight * 0.8
            else:
                # Other waste: 1 kg ≈ 0.4 kg CO2 saved
                co2_saved += weight * 0.4
    
    # Also calculate potential savings from recyclable waste (even if not marked recycled)
    # This gives users an idea of what they could save
    recyclable_entries = [e for e in entries if e.waste_type == 'recyclable' and not e.recycled and e.weight_kg]
    potential_co2 = sum(e.weight_kg * 0.6 for e in recyclable_entries)
    potential_trees = sum((e.weight_kg / 1000) * 17 for e in recyclable_entries)
    
    # Calculate recycling rate
    recycling_rate = (recycled_count / total_entries * 100) if total_entries > 0 else 0
    
    return render_template('statistics.html',
                         total_entries=total_entries,
                         total_weight=round(total_weight, 2),
                         recycled_count=recycled_count,
                         recycled_weight=round(recycled_weight, 2),
                         waste_by_type=waste_by_type,
                         monthly_stats=monthly_stats,
                         co2_saved=round(co2_saved, 2),
                         trees_saved=round(trees_saved, 2),
                         recycling_rate=round(recycling_rate, 1),
                         potential_co2=round(potential_co2, 2),
                         potential_trees=round(potential_trees, 2))

@app.route('/goals')
@login_required
def goals():
    """Waste reduction goals page"""
    # Update all goals progress before displaying
    update_goals_progress(current_user.id)
    
    user_goals = WasteGoal.query.filter_by(user_id=current_user.id).order_by(WasteGoal.created_at.desc()).all()
    return render_template('goals.html', goals=user_goals)

@app.route('/goals/create', methods=['POST'])
@login_required
def create_goal():
    """Create a new waste reduction goal"""
    goal_type = request.form.get('goal_type')
    target_value = float(request.form.get('target_value', 0))
    unit = request.form.get('unit', 'kg')
    end_date_str = request.form.get('end_date')
    
    end_date = None
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except:
            pass
    
    # Don't set start_date by default - this allows goals to count all entries
    # Users can set a start date if they want to track from a specific date
    goal = WasteGoal(
        user_id=current_user.id,
        goal_type=goal_type,
        target_value=target_value,
        unit=unit,
        end_date=end_date,
        start_date=None  # Count all entries by default, not just from creation date
    )
    db.session.add(goal)
    db.session.commit()
    
    flash('Goal created successfully!', 'success')
    return redirect(url_for('goals'))

@app.route('/notifications')
@login_required
def notifications_page():
    """User notifications page"""
    user_notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).limit(50).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('notifications.html', notifications=user_notifications, unread_count=unread_count)

@app.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/export-data')
@login_required
def export_data():
    """Export user data as CSV"""
    import csv
    from io import StringIO
    
    entries = WasteEntry.query.filter_by(user_id=current_user.id).all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Waste Type', 'Weight (kg)', 'Description', 'Recycled'])
    
    for entry in entries:
        writer.writerow([
            entry.disposal_date.strftime('%Y-%m-%d'),
            entry.waste_type,
            entry.weight_kg or '',
            entry.description or '',
            'Yes' if entry.recycled else 'No'
        ])
    
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=ecotrack_data_{current_user.username}_{datetime.now().strftime("%Y%m%d")}.csv'}
    )

@app.route('/calculator')
@login_required
def calculator():
    """Waste reduction calculator"""
    return render_template('calculator.html')

# API Routes
@app.route('/api/waste-entries', methods=['GET', 'POST'])
@login_required
def api_waste_entries():
    if request.method == 'GET':
        entries = WasteEntry.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': e.id,
            'waste_type': e.waste_type,
            'weight_kg': e.weight_kg,
            'description': e.description,
            'disposal_date': e.disposal_date.isoformat(),
            'recycled': e.recycled
        } for e in entries])
    
    elif request.method == 'POST':
        data = request.json
        entry = WasteEntry(
            user_id=current_user.id,
            waste_type=data.get('waste_type'),
            weight_kg=data.get('weight_kg'),
            description=data.get('description', '')
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({'id': entry.id, 'message': 'Entry created successfully'}), 201

@app.route('/api/recycling-centers', methods=['GET'])
@login_required
def api_recycling_centers():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    
    if lat and lng:
        centers = get_nearby_recycling_centers(lat, lng)
    else:
        centers = RecyclingCenter.query.filter_by(is_active=True).all()
    
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'address': c.address,
        'latitude': c.latitude,
        'longitude': c.longitude,
        'phone': c.phone,
        'email': c.email,
        'accepts_types': c.accepts_types,
        'hours': c.hours
    } for c in centers])

@app.route('/api/pickup-schedules', methods=['GET'])
@login_required
def api_pickup_schedules():
    area = request.args.get('area')
    schedules = PickupSchedule.query.filter_by(is_active=True)
    
    if area:
        schedules = schedules.filter(PickupSchedule.area.ilike(f'%{area}%'))
    
    return jsonify([{
        'id': s.id,
        'area': s.area,
        'pickup_day': s.pickup_day,
        'pickup_time': s.pickup_time,
        'waste_types': s.waste_types,
        'frequency': s.frequency,
        'center_name': s.recycling_center.name if s.recycling_center else None
    } for s in schedules.all()])

@app.route('/api/statistics', methods=['GET'])
@login_required
def api_statistics():
    """API endpoint for statistics data"""
    entries = WasteEntry.query.filter_by(user_id=current_user.id).all()
    
    total_entries = len(entries)
    total_weight = sum(e.weight_kg or 0 for e in entries)
    recycled_count = sum(1 for e in entries if e.recycled)
    recycled_weight = sum(e.weight_kg or 0 for e in entries if e.recycled)
    
    waste_by_type = {}
    for entry in entries:
        waste_type = entry.waste_type
        if waste_type not in waste_by_type:
            waste_by_type[waste_type] = {'count': 0, 'weight': 0}
        waste_by_type[waste_type]['count'] += 1
        waste_by_type[waste_type]['weight'] += entry.weight_kg or 0
    
    return jsonify({
        'total_entries': total_entries,
        'total_weight': round(total_weight, 2),
        'recycled_count': recycled_count,
        'recycled_weight': round(recycled_weight, 2),
        'waste_by_type': waste_by_type
    })

@app.route('/api/goals', methods=['GET', 'POST'])
@login_required
def api_goals():
    """API endpoint for goals"""
    if request.method == 'GET':
        goals = WasteGoal.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': g.id,
            'goal_type': g.goal_type,
            'target_value': g.target_value,
            'current_value': g.current_value,
            'unit': g.unit,
            'is_completed': g.is_completed,
            'end_date': g.end_date.isoformat() if g.end_date else None
        } for g in goals])
    
    elif request.method == 'POST':
        data = request.json
        goal = WasteGoal(
            user_id=current_user.id,
            goal_type=data.get('goal_type'),
            target_value=data.get('target_value'),
            unit=data.get('unit', 'kg'),
            end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None
        )
        db.session.add(goal)
        db.session.commit()
        return jsonify({'id': goal.id, 'message': 'Goal created'}), 201

@app.route('/api/notifications', methods=['GET'])
@login_required
def api_notifications():
    """API endpoint for notifications"""
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .order_by(Notification.created_at.desc()).limit(10).all()
    return jsonify([{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'type': n.notification_type,
        'created_at': n.created_at.isoformat(),
        'link': n.link
    } for n in notifications])

# Socket.IO Events
@socketio.on('connect')
def handle_connect(auth):
    """Handle client connection - check if user is authenticated"""
    from flask import request as flask_request
    # Get user from session cookie
    user_id = None
    try:
        with app.app_context():
            from flask_login import current_user
            if hasattr(flask_request, 'cookies'):
                # Try to get user from session
                session_id = flask_request.cookies.get('session')
                if session_id:
                    # Decode session to get user_id
                    from itsdangerous import URLSafeTimedSerializer
                    serializer = URLSafeTimedSerializer(app.secret_key)
                    try:
                        session_data = serializer.loads(session_id)
                        user_id = session_data.get('user_id') or session_data.get('_user_id')
                    except:
                        pass
    except Exception as e:
        print(f"Session error: {e}")
    
    if user_id:
        join_room(f'user_{user_id}')
        emit('connected', {'message': 'Connected to Ecotrack chat'})
    else:
        # Allow connection but require auth for messages
        emit('connected', {'message': 'Connected. Please ensure you are logged in.'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    pass

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle chat messages from client"""
    from flask import request as flask_request
    
    # Try to get user_id from session
    user_id = None
    try:
        # Flask-SocketIO should preserve the session
        # Try to get from request context
        with app.app_context():
            from flask_login import current_user
            # Access session through request
            if hasattr(flask_request, 'cookies'):
                # Try to decode session
                try:
                    from itsdangerous import URLSafeTimedSerializer
                    serializer = URLSafeTimedSerializer(app.secret_key)
                    session_cookie = flask_request.cookies.get('session')
                    if session_cookie:
                        session_data = serializer.loads(session_cookie)
                        user_id = session_data.get('_user_id') or session_data.get('user_id')
                except:
                    # Fallback: try to get from data
                    user_id = data.get('user_id')
    except Exception as e:
        print(f"Error getting user_id: {e}")
        user_id = data.get('user_id')
    
    if not user_id:
        emit('error', {'message': 'Please refresh the page and log in again.'})
        return
    
    message = data.get('message', '').strip()
    if not message:
        return
    
    # Enhanced chatbot responses
    response = generate_chatbot_response(message, user_id)
    
    # Save to database
    try:
        chat_msg = ChatMessage(
            user_id=user_id,
            message=message,
            response=response
        )
        db.session.add(chat_msg)
        db.session.commit()
    except Exception as e:
        print(f"Error saving chat message: {e}")
    
    emit('chat_response', {
        'message': message,
        'response': response,
        'timestamp': datetime.utcnow().isoformat()
    })

# Helper Functions
def geocode_address(address):
    """Geocode an address using Google Maps API"""
    if not GOOGLE_MAPS_API_KEY:
        return None, None
    
    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': address,
            'key': GOOGLE_MAPS_API_KEY
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
    except Exception as e:
        print(f"Geocoding error: {e}")
    
    return None, None

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two coordinates using Haversine formula"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth radius in km
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)
    
    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def get_nearby_recycling_centers(lat, lng, radius_km=10, limit=10):
    """Get recycling centers within radius"""
    centers = RecyclingCenter.query.filter_by(is_active=True).all()
    
    nearby = []
    for center in centers:
        distance = calculate_distance(lat, lng, center.latitude, center.longitude)
        if distance <= radius_km:
            nearby.append((distance, center))
    
    # Sort by distance and limit
    nearby.sort(key=lambda x: x[0])
    return [center for _, center in nearby[:limit]]

def check_and_create_achievements(user_id):
    """Check if user has unlocked any achievements"""
    entries = WasteEntry.query.filter_by(user_id=user_id).all()
    total_entries = len(entries)
    recycled_count = sum(1 for e in entries if e.recycled)
    total_weight = sum(e.weight_kg or 0 for e in entries if e.recycled)
    
    achievements_to_check = [
        (1, 'First Step', 'Tracked your first waste entry!', 'first_entry'),
        (5, 'Getting Started', 'Tracked 5 waste entries!', 'five_entries'),
        (10, 'Waste Warrior', 'Tracked 10 waste entries!', 'ten_entries'),
        (25, 'Eco Champion', 'Tracked 25 waste entries!', 'twenty_five_entries'),
        (1, 'Recycler', 'Recycled your first item!', 'first_recycle'),
        (10, 'Recycling Master', 'Recycled 10 items!', 'ten_recycles'),
        (50, 'Eco Hero', 'Recycled 50 kg of waste!', 'fifty_kg_recycled')
    ]
    
    for threshold, title, description, achievement_type in achievements_to_check:
        # Check if achievement already exists
        existing = Achievement.query.filter_by(
            user_id=user_id,
            achievement_type=achievement_type
        ).first()
        
        if existing:
            continue
        
        # Check conditions
        unlocked = False
        if achievement_type == 'first_entry' and total_entries >= 1:
            unlocked = True
        elif achievement_type == 'five_entries' and total_entries >= 5:
            unlocked = True
        elif achievement_type == 'ten_entries' and total_entries >= 10:
            unlocked = True
        elif achievement_type == 'twenty_five_entries' and total_entries >= 25:
            unlocked = True
        elif achievement_type == 'first_recycle' and recycled_count >= 1:
            unlocked = True
        elif achievement_type == 'ten_recycles' and recycled_count >= 10:
            unlocked = True
        elif achievement_type == 'fifty_kg_recycled' and total_weight >= 50:
            unlocked = True
        
        if unlocked:
            achievement = Achievement(
                user_id=user_id,
                achievement_type=achievement_type,
                title=title,
                description=description
            )
            db.session.add(achievement)
            
            # Create notification
            notification = Notification(
                user_id=user_id,
                title='🏆 Achievement Unlocked!',
                message=f'{title}: {description}',
                notification_type='achievement',
                link='/dashboard'
            )
            db.session.add(notification)
    
    db.session.commit()

def update_goals_progress(user_id):
    """Update progress for user's waste reduction goals"""
    # Update ALL goals (both completed and not completed) to show accurate progress
    goals = WasteGoal.query.filter_by(user_id=user_id).all()
    entries = WasteEntry.query.filter_by(user_id=user_id).all()
    
    for goal in goals:
        was_completed = goal.is_completed
        
        if goal.goal_type == 'reduce':
            # Calculate total waste in current period
            # If start_date is set, count from that date; otherwise count all entries
            if goal.start_date:
                period_entries = [e for e in entries if e.disposal_date >= goal.start_date]
            else:
                period_entries = entries
            
            if goal.end_date:
                period_entries = [e for e in period_entries if e.disposal_date <= goal.end_date]
            
            current_value = sum(e.weight_kg or 0 for e in period_entries)
            goal.current_value = current_value
            
            # Check if goal is completed (reduced waste)
            if current_value <= goal.target_value and not was_completed:
                goal.is_completed = True
                create_notification(user_id, 'Goal Achieved!', 
                                 f'You achieved your goal to reduce waste to {goal.target_value} {goal.unit}!',
                                 'achievement', '/goals')
            elif current_value > goal.target_value and was_completed:
                # Goal was completed but now exceeded - mark as not completed
                goal.is_completed = False
        
        elif goal.goal_type == 'recycle':
            # Count recycled items
            # If start_date is set, count from that date; otherwise count all entries
            recycled_entries = [e for e in entries if e.recycled]
            
            if goal.start_date:
                recycled_entries = [e for e in recycled_entries if e.disposal_date >= goal.start_date]
            
            if goal.end_date:
                recycled_entries = [e for e in recycled_entries if e.disposal_date <= goal.end_date]
            
            if goal.unit == 'count':
                current_value = len(recycled_entries)
            else:
                current_value = sum(e.weight_kg or 0 for e in recycled_entries)
            
            goal.current_value = current_value
            
            if current_value >= goal.target_value and not was_completed:
                goal.is_completed = True
                create_notification(user_id, 'Goal Achieved!',
                                 f'You achieved your recycling goal of {goal.target_value} {goal.unit}!',
                                 'achievement', '/goals')
        
        elif goal.goal_type == 'track':
            # Count total entries
            # If start_date is set, count from that date; otherwise count all entries
            if goal.start_date:
                period_entries = [e for e in entries if e.disposal_date >= goal.start_date]
            else:
                period_entries = entries
            
            if goal.end_date:
                period_entries = [e for e in period_entries if e.disposal_date <= goal.end_date]
            
            current_value = len(period_entries)
            goal.current_value = current_value
            
            if current_value >= goal.target_value and not was_completed:
                goal.is_completed = True
                create_notification(user_id, 'Goal Achieved!',
                                 f'You tracked {goal.target_value} waste entries!',
                                 'achievement', '/goals')
    
    db.session.commit()

def create_notification(user_id, title, message, notification_type='info', link=None):
    """Helper function to create notifications"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def generate_chatbot_response(message, user_id=None):
    """Generate enhanced chatbot response based on user message"""
    message_lower = message.lower()
    
    # Get user stats if user_id provided
    user_stats = {}
    if user_id:
        try:
            user = User.query.get(user_id)
            if user:
                total_entries = WasteEntry.query.filter_by(user_id=user_id).count()
                recycled_count = WasteEntry.query.filter_by(user_id=user_id, recycled=True).count()
                total_weight = db.session.query(db.func.sum(WasteEntry.weight_kg)).filter_by(user_id=user_id).scalar() or 0
                user_stats = {
                    'total_entries': total_entries,
                    'recycled_count': recycled_count,
                    'total_weight': round(total_weight, 2)
                }
        except:
            pass
    
    if any(word in message_lower for word in ['recycle', 'recycling', 'center']):
        response = "I can help you find recycling centers! Check the 'Recycling Centers' page or tell me your location."
        if user_stats.get('recycled_count', 0) > 0:
            response += f" You've recycled {user_stats['recycled_count']} items so far! 🌱"
        return response
    
    elif any(word in message_lower for word in ['pickup', 'schedule', 'collection']):
        return "You can view pickup schedules on the 'Pickup Schedules' page. What area are you in? I can also remind you about upcoming pickups!"
    
    elif any(word in message_lower for word in ['waste', 'dispose', 'trash', 'garbage']):
        response = "You can track your waste disposal on the 'Track Waste' page. What type of waste do you need to dispose of?"
        if user_stats.get('total_entries', 0) > 0:
            response += f" You've tracked {user_stats['total_entries']} waste entries."
        return response
    
    elif any(word in message_lower for word in ['stat', 'statistic', 'progress', 'how much']):
        if user_stats:
            return f"Here's your progress: {user_stats['total_entries']} waste entries tracked, {user_stats['recycled_count']} items recycled, {user_stats['total_weight']} kg total. Great job! 🎉"
        return "Check your dashboard for detailed statistics and progress!"
    
    elif any(word in message_lower for word in ['tip', 'tips', 'segregation', 'separate']):
        return "Check out the 'Waste Tips' page for helpful information on waste segregation and disposal! I can also give you specific tips - just ask!"
    
    elif any(word in message_lower for word in ['goal', 'target', 'challenge']):
        return "You can set waste reduction goals on your dashboard! Try setting a goal to reduce waste or increase recycling. Would you like help setting one up?"
    
    elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'greeting']):
        return "Hello! I'm Ecotrack assistant. How can I help you with waste management today? I can help with tracking, finding centers, schedules, and tips!"
    
    elif any(word in message_lower for word in ['help', 'support', 'what can you']):
        return "I can help you with: finding recycling centers, checking pickup schedules, tracking waste, setting goals, viewing statistics, and providing waste management tips. What do you need?"
    
    elif any(word in message_lower for word in ['thank', 'thanks']):
        return "You're welcome! Keep up the great work with waste management! 🌍"
    
    elif any(word in message_lower for word in ['environment', 'impact', 'carbon']):
        return "Great question! Proper waste management significantly reduces environmental impact. Recycling helps reduce carbon emissions and saves resources. Track your waste to see your positive impact!"
    
    else:
        return "I'm here to help with waste management! You can ask me about recycling centers, pickup schedules, waste tracking, statistics, goals, or tips for proper waste disposal. What would you like to know?"

# Initialize database with sample data
def init_db():
    """Initialize database with sample data"""
    db.create_all()
    try:
        db.engine.execute('ALTER TABLE recycling_center ADD COLUMN email TEXT;')
    except Exception:
        # If column already exists, ignore the error
        pass
    # Add sample recycling centers for Nepal (Kathmandu area)
    if RecyclingCenter.query.count() == 0:
        sample_centers = [
            RecyclingCenter(
                name='Kathmandu Metropolitan City Waste Management',
                address='Teku, Kathmandu',
                city='Kathmandu',
                latitude=27.7000,
                longitude=85.3000,
                phone='+977-1-4256909',
                accepts_types='organic, recyclable, hazardous',
                hours='Mon-Sat: 8:00 AM - 5:00 PM'
            ),
            RecyclingCenter(
                name='Green Waste Nepal',
                address='Lalitpur, Kathmandu Valley',
                city='Lalitpur',
                latitude=27.6667,
                longitude=85.3167,
                phone='+977-1-5521234',
                accepts_types='recyclable, electronic',
                hours='Mon-Fri: 9:00 AM - 4:00 PM'
            ),
            RecyclingCenter(
                name='Nepal Recycling Center',
                address='Baneshwor, Kathmandu',
                city='Kathmandu',
                latitude=27.6833,
                longitude=85.3500,
                phone='+977-1-4785234',
                accepts_types='recyclable, plastic, paper',
                hours='Mon-Sat: 8:00 AM - 6:00 PM'
            )
        ]
        
        for center in sample_centers:
            db.session.add(center)
        
        # Add sample pickup schedules
        sample_schedules = [
            PickupSchedule(
                recycling_center_id=1,
                area='Kathmandu - Central',
                pickup_day='Monday',
                pickup_time='09:00 AM',
                waste_types='organic, recyclable',
                frequency='weekly'
            ),
            PickupSchedule(
                recycling_center_id=1,
                area='Kathmandu - North',
                pickup_day='Wednesday',
                pickup_time='09:00 AM',
                waste_types='organic, recyclable',
                frequency='weekly'
            ),
            PickupSchedule(
                recycling_center_id=2,
                area='Lalitpur',
                pickup_day='Friday',
                pickup_time='10:00 AM',
                waste_types='recyclable, electronic',
                frequency='bi-weekly'
            )
        ]
        
        for schedule in sample_schedules:
            db.session.add(schedule)
        
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

