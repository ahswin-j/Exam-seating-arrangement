from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import csv, os

app = Flask(__name__)
app.secret_key = 'secretkey'
app.config['UPLOAD_FOLDER'] = 'uploads'

students = []
classrooms = []
assigned_seats = []
subject_choices = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == 'examseating@gmail.com' and password == 'examcell@rit':
            session['admin'] = True
            return redirect(url_for('upload'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'admin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        student_file = request.files.get('students')
        classroom_file = request.files.get('classrooms')

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        student_path = os.path.join(app.config['UPLOAD_FOLDER'], 'students.csv')
        classroom_path = os.path.join(app.config['UPLOAD_FOLDER'], 'classrooms.csv')

        student_file.save(student_path)
        classroom_file.save(classroom_path)

        with open(student_path, newline='') as f:
            reader = csv.DictReader(f)
            global students
            students = [row for row in reader]

        with open(classroom_path, newline='') as f:
            reader = csv.DictReader(f)
            global classrooms
            classrooms = [row['classroom_name'] for row in reader]

        # Load subject options from CSV for 4 departments
        subject_data = {'AIDS': [], 'CCE': [], 'CSE': [], 'ECE': []}
        with open('subject_data.csv', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dept = row['dept']
                if dept in subject_data:
                    subject_data[dept].append({
                        'code': row['subject_code'],
                        'name': row['subject_name']
                    })

        return render_template('upload.html', subject_data=subject_data)

    return render_template('upload.html')

@app.route('/assign', methods=['POST'])
def assign():
    global assigned_seats, subject_choices
    assigned_seats = []

    # Get selected subjects from form
    subject_choices = {
        'AIDS': request.form.get('aids_subject'),
        'CCE': request.form.get('cce_subject'),
        'CSE': request.form.get('cse_subject'),
        'ECE': request.form.get('ece_subject')
    }

    # Group students by subject code
    subject_groups = {}
    for student in students:
        dept = student['dept']
        sub_code = subject_choices.get(dept)
        if sub_code:
            subject_groups.setdefault(sub_code, []).append(student)

    # Create ordered subject list: [AIDS, CCE, CSE, ECE]
    subject_order = [subject_choices[dept] for dept in ['AIDS', 'CCE', 'CSE', 'ECE']]
    subject_order = [s for s in subject_order if s in subject_groups and subject_groups[s]]

    seat_no = 1
    room_index = 0
    previous_subject = None

    while any(subject_groups.values()):
        # Pick next subject that is not same as previous_subject
        available_subjects = [s for s in subject_order if subject_groups.get(s)]
        next_subject = None
        for s in available_subjects:
            if s != previous_subject:
                next_subject = s
                break
        if not next_subject:
            # If all remaining students are from the same subject
            next_subject = available_subjects[0]

        student = subject_groups[next_subject].pop(0)
        previous_subject = next_subject

        if room_index >= len(classrooms):
            return "Not enough classrooms."

        assigned_seats.append({
            **student,
            'room': classrooms[room_index],
            'seat_no': seat_no
        })

        seat_no += 1
        if seat_no > 30:
            seat_no = 1
            room_index += 1

    # Save the assigned seats as a CSV file
    assigned_seats_path = os.path.join(app.config['UPLOAD_FOLDER'], 'assigned_seats.csv')
    with open(assigned_seats_path, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=assigned_seats[0].keys())
        writer.writeheader()
        writer.writerows(assigned_seats)

    # Pass the filename to the template for download link
    return redirect(url_for('index', filename='assigned_seats.csv'))

@app.route('/seating')
def seating():
    roll_no = request.args.get('roll_no')
    for s in assigned_seats:
        if s['roll_no'] == roll_no:
            return render_template('seating.html', student=s)
    return render_template('seating.html', student=None, not_found=True)

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
