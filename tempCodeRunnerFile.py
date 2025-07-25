from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = 'Aykjz9J4mYVUx9w2Vj6rWqLm7bn95mP6'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Moulik3637'
app.config['MYSQL_DB'] = 'college_club_manager'

mysql = MySQL(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id_, username, role):
        self.id = id_
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, role FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    if user:
        return User(user[0], user[1], user[2])
    return None

@app.route('/')
def index():
    return render_template('index.html', current_year=datetime.now().year)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # This is now just the role selection page
    if request.method == 'POST':
        role = request.form['role']
        if role == 'student':
            return redirect(url_for('register_student'))
        elif role == 'club_rep':
            return redirect(url_for('register_club'))
        else:
            flash('Invalid role selected')
            return redirect(url_for('register'))
    
    return render_template('register_role.html')

@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        department = request.form['department']
        roll_number = request.form['roll_number']

        cur = mysql.connection.cursor()
        try:
            # Check if username or email already exists
            cur.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
            if cur.fetchone():
                flash('Username or email already exists')
                return redirect(url_for('register_student'))

            password_hash = generate_password_hash(password)
            cur.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, 'student')",
                (username, email, password_hash)
            )
            user_id = cur.lastrowid
            
            cur.execute(
                "INSERT INTO students (user_id, department, roll_number) VALUES (%s, %s, %s)",
                (user_id, department, roll_number)
            )
            
            mysql.connection.commit()
            flash('Student registration successful! Please log in.')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Registration failed: {str(e)}')
        finally:
            cur.close()
    
    return render_template('register_student.html')

@app.route('/register/club', methods=['GET', 'POST'])
def register_club():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        club_name = request.form['club_name']

        cur = mysql.connection.cursor()
        try:
            # Check if username or email already exists
            cur.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
            if cur.fetchone():
                flash('Username or email already exists')
                return redirect(url_for('register_club'))

            password_hash = generate_password_hash(password)
            cur.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, 'club_rep')",
                (username, email, password_hash)
            )
            user_id = cur.lastrowid
            
            cur.execute(
                "INSERT INTO clubs (user_id, club_name) VALUES (%s, %s)",
                (user_id, club_name)
            )
            
            mysql.connection.commit()
            flash('Club registration successful! Please log in.')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Registration failed: {str(e)}')
        finally:
            cur.close()
    
    return render_template('register_club.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, password_hash, role FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[1], password):
            user_obj = User(user[0], username, user[2])
            login_user(user_obj)
            flash('Logged in successfully.')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    
    try:
        if current_user.role == 'student':
            # Student dashboard logic
            cur.execute("SELECT COUNT(*) FROM applications WHERE student_id = %s", (current_user.id,))
            applications_count = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(*) FROM opportunities 
                WHERE status='active' 
                AND deadline BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 3 DAY)
            """)
            approaching_deadlines = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM opportunities WHERE status='active'")
            active_opportunities = cur.fetchone()[0]
            
            cur.execute("""
                SELECT id, title, deadline 
                FROM opportunities 
                WHERE status='active' AND deadline > NOW()
                ORDER BY deadline ASC LIMIT 3
            """)
            nearest_deadlines = [{'id': row[0], 'title': row[1], 'deadline': row[2]} for row in cur.fetchall()]
            
            cur.execute("""
                SELECT o.title, a.status, a.applied_at 
                FROM applications a
                JOIN opportunities o ON a.opportunity_id = o.id
                WHERE a.student_id = %s
                ORDER BY a.applied_at DESC LIMIT 3
            """, (current_user.id,))
            recent_applications = [{'title': row[0], 'status': row[1], 'applied_at': row[2]} for row in cur.fetchall()]
            
            return render_template('dashboard_student.html',
                                student_name=current_user.username,
                                applications_count=applications_count,
                                approaching_deadlines=approaching_deadlines,
                                active_opportunities=active_opportunities,
                                nearest_deadlines=nearest_deadlines,
                                recent_applications=recent_applications)
        
        elif current_user.role == 'club_rep':
            # Club representative dashboard logic
            cur.execute("""
                SELECT id, title, type, description, deadline, status, 
                       google_form_link, google_responses_link
                FROM opportunities 
                WHERE creator_id=%s
                ORDER BY deadline ASC
            """, (current_user.id,))
            opportunities = [
                {
                    'id': row[0],
                    'title': row[1],
                    'type': row[2],
                    'description': row[3],
                    'deadline': row[4],
                    'status': row[5],
                    'google_form_link': row[6],
                    'google_responses_link': row[7]
                }
                for row in cur.fetchall()
            ]
            return render_template('dashboard_club.html', 
                                opportunities=opportunities,
                                club_name=current_user.username)
        
        else:
            flash('Invalid user role.', 'error')
            return redirect(url_for('logout'))
    
    except Exception as e:
        flash('An error occurred while loading the dashboard.', 'error')
        return redirect(url_for('index'))
    
    finally:
        cur.close()

@app.route('/profile')
@login_required
def profile():
    cur = mysql.connection.cursor()
    
    # Get basic user info
    cur.execute("SELECT username, email, role FROM users WHERE id = %s", (current_user.id,))
    user = cur.fetchone()
    
    # Get additional info based on role
    extra_info = None
    if current_user.role == 'student':
        cur.execute("""
            SELECT department, roll_number 
            FROM students 
            WHERE user_id = %s
        """, (current_user.id,))
        extra_info = cur.fetchone()
    elif current_user.role == 'club_rep':
        cur.execute("SELECT club_name FROM clubs WHERE user_id = %s", (current_user.id,))
        extra_info = cur.fetchone()
    
    cur.close()
    
    return render_template('profile.html', 
                         user={
                             'username': user[0],
                             'email': user[1],
                             'role': user[2]
                         },
                         extra_info=extra_info)

@app.route('/opportunities')
@login_required
def opportunities():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, title, type, description, deadline, status, google_form_link
        FROM opportunities 
        WHERE status='active'
        ORDER BY deadline ASC
    """)
    opportunities = [
        {
            'id': row[0],
            'title': row[1],
            'type': row[2],
            'description': row[3],
            'deadline': row[4],
            'status': row[5],
            'google_form_link': row[6]
        }
        for row in cur.fetchall()
    ]
    
    # Get application stats
    cur.execute("SELECT COUNT(*) FROM applications WHERE student_id = %s", (current_user.id,))
    applications_count = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(*) FROM opportunities 
        WHERE status='active' 
        AND deadline BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 3 DAY)
    """)
    approaching_deadlines = cur.fetchone()[0]
    
    cur.close()
    
    return render_template('opportunities.html',
                         opportunities=opportunities,
                         applications_count=applications_count,
                         approaching_deadlines=approaching_deadlines)

@app.route('/opportunity/<int:opp_id>')
@login_required
def opportunity_detail(opp_id):
    cur = mysql.connection.cursor()
    
    # Get opportunity details
    cur.execute("""
        SELECT id, title, type, description, requirements, deadline, 
               positions, status, google_form_link, creator_id
        FROM opportunities WHERE id=%s
    """, (opp_id,))
    opportunity = cur.fetchone()
    
    # Check if student has applied
    has_applied = False
    if current_user.role == 'student':
        cur.execute("""
            SELECT 1 FROM applications 
            WHERE opportunity_id=%s AND student_id=%s
            LIMIT 1
        """, (opp_id, current_user.id))
        has_applied = cur.fetchone() is not None
    
    cur.close()
    
    if not opportunity:
        flash('Opportunity not found.')
        return redirect(url_for('dashboard'))
    
    return render_template('opportunity_detail.html',
                         opportunity={
                             'id': opportunity[0],
                             'title': opportunity[1],
                             'type': opportunity[2],
                             'description': opportunity[3],
                             'requirements': opportunity[4],
                             'deadline': opportunity[5],
                             'positions': opportunity[6],
                             'status': opportunity[7],
                             'google_form_link': opportunity[8],
                             'creator_id': opportunity[9]
                         },
                         has_applied=has_applied,
                         current_user_role=current_user.role)

@app.route('/opportunity/<int:opp_id>/apply')
@login_required
def apply_opportunity_redirect(opp_id):
    if current_user.role != 'student':
        flash('Only students can apply.')
        return redirect(url_for('dashboard'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT google_form_link FROM opportunities WHERE id=%s", (opp_id,))
    row = cur.fetchone()

    # Record the application
    cur.execute("""
        INSERT INTO applications (opportunity_id, student_id, status)
        VALUES (%s, %s, 'pending')
    """, (opp_id, current_user.id))
    mysql.connection.commit()
    cur.close()
    
    if not row or not row[0]:
        flash('Application link not available for this opportunity.')
        return redirect(url_for('dashboard'))
    
    return redirect(row[0])

@app.route('/opportunity/create', methods=['GET', 'POST'])
@login_required
def create_opportunity():
    if current_user.role != 'club_rep':
        flash('Unauthorized access.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        type_ = request.form['type']
        description = request.form['description']
        requirements = request.form['requirements']
        deadline = request.form['deadline']
        positions = request.form['positions']
        google_form_link = request.form['google_form_link']
        google_responses_link = request.form['google_responses_link']

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO opportunities 
            (creator_id, type, title, description, requirements, deadline, 
             positions, google_form_link, google_responses_link) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            current_user.id, type_, title, description, requirements,
            deadline, positions, google_form_link, google_responses_link
        ))
        mysql.connection.commit()
        cur.close()
        flash('Opportunity created successfully.')
        return redirect(url_for('dashboard'))
    return render_template('create_opportunity.html')

if __name__ == '__main__':
    app.run(debug=True)