from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
from werkzeug.security import check_password_hash, generate_password_hash
from pymongo import MongoClient
import os
from werkzeug.utils import secure_filename
import pandas as pd
import json
import csv
import io
from bson import ObjectId
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# MongoDB configuration
client = MongoClient('mongodb://localhost:27017/')
db = client['gta_application']
users_collection = db['users']
gta_collection = db['gta_data']
assignment_collection = db['gta_assignments']
catalog_collection = db['catalog_course']
final_collection = db['final_approval_data']
columns_collection = db['columns']  # Collection to store added column names

# File upload configuration
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'xlsx', 'csv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_config(file_path='gta_rules.json'):
    with open(file_path, 'r') as f:
        return json.load(f)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_course_number(course_str):
    """Extracts the numeric part of the course string (e.g., from 'IT 1324/01' returns '1324')."""
    if not course_str:
        return ''
    course_str = str(course_str)
    parts = course_str.replace('/', ' ').split()
    for part in parts:
        numbers = ''.join(filter(str.isdigit, part))
        if numbers:
            return numbers
    return ''

def is_cross_listed(row, data):
    """
    Checks if a section is cross-listed.
    Returns tuple of (delta, online_section) for hybrid sections.
    For online sections that are cross-listed, returns None and updates their GTA Assignment.
    """
    course_num_sec = row.get("Course Num/Sec", "")
    course_number = extract_course_number(course_num_sec)
    max_seats = int(float(row.get("Max", 0)))
    avail_seats = int(float(row.get("Avail", 0)))
    delta_hybrid = max_seats - avail_seats

    # Determine if this is a hybrid section (no "W" in the section part)
    if "W" not in course_num_sec.split('/')[-1]:
        if int(course_number) < 5000:  # Undergraduate criteria
            if max_seats > 30:
                return None
            online_cap = 40
        elif int(course_number) >= 6000:  # Graduate criteria
            if max_seats > 20:
                return None
            online_cap = 30
        else:
            return None

        # Search for a corresponding online section in data
        for other_row in data:
            other_course_num_sec = other_row.get("Course Num/Sec", "")
            other_course_number = extract_course_number(other_course_num_sec)
            other_max_seats = int(float(other_row.get("Max", 0)))
            other_avail_seats = int(float(other_row.get("Avail", 0)))
            delta_online = other_max_seats - other_avail_seats

            # Match course numbers and check if online section has "W"
            if (course_number == other_course_number and
                "W" in other_course_num_sec.split('/')[-1] and
                ((int(course_number) < 5000 and other_max_seats < online_cap) or
                 (int(course_number) >= 6000 and other_max_seats < online_cap))):
                
                # Mark online section as cross-listed with hybrid section
                other_row["GTA Assignment"] = f"Cross-listed with {course_num_sec}"
                print(f"Cross-listed pair found: {course_num_sec} (hybrid) and {other_course_num_sec} (online)")
                
                # Return combined delta for hybrid section
                return delta_hybrid + delta_online

    return None




def determine_gta_assignment(row, data, config):
    """
    Determines the appropriate GTA assignment based on course type, number, and cross-listing conditions.
    """
    try:
        course_num_sec = row.get("Course Num/Sec", "")
        course_number = extract_course_number(course_num_sec)
        max_seats = int(float(row.get("Max", 0)))
        avail_seats = int(float(row.get("Avail", 0)))
        delta = max_seats - avail_seats

        # Handle cross-listing for hybrid sections
        cross_listed_delta = is_cross_listed(row, data)
        if cross_listed_delta is not None:
            delta = cross_listed_delta  # Use combined delta for cross-listed hybrid section

        # Determine GTA assignment based on course rules
        if int(course_number) >= 6000:
            rules = config["rules"]["6000_plus_series"]["any_course_type"]
        elif int(course_number) < 5000:
            course_subtype = "RP_intensive" if "intensive" in row.get("Course Type", "").lower() else "typical_lecture"
            rules = config["rules"]["below_5000"][course_subtype]
        else:
            rules = config["rules"]["5000_series"]["any_course_type"]

        # Check delta against the rules for assignment
        for tier, limits in rules.items():
            if limits["min"] <= delta <= limits["max"]:
                print(f"Assignment for {course_num_sec}: {tier.replace('_', ' ').capitalize()}")
                return tier.replace("_", " ").capitalize()

        return "No applicable GTA"

    except Exception as e:
        print(f"Error processing assignment for row: {row}")
        print(f"Error details: {str(e)}")
        return "Error in GTA Assignment"


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user'] = email
            flash('Login Successful', 'success')
            return redirect(url_for('welcome'))
        else:
            flash('Invalid Credentials', 'error')
    return render_template('login.html')

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')

        if users_collection.find_one({'email': email}):
            flash('Email already exists. Please log in.', 'error')
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password)
        users_collection.insert_one({
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password': hashed_password
        })

        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))

    return render_template('create_account.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = users_collection.find_one({'email': email})
        
        if user:
            # Logic to send recovery email
            flash('An email has been sent to recover your password.', 'success')
        else:
            flash('Invalid email. Please try again.', 'error')
    
    return render_template('forgot_password.html')

def reset_password(user_id):
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Check if passwords match
        if new_password != confirm_password:
            flash('Passwords do not match. Please try again.', 'error')
            return redirect(url_for('reset_password', user_id=user_id))

        # Add more password validation checks (e.g., length, complexity) if needed
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('reset_password', user_id=user_id))

        # Hash the new password
        hashed_password = generate_password_hash(new_password)

        # Update user's password in the database
        users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'password': hashed_password}})
        
        flash('Your password has been updated successfully.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', user_id=user_id)

@app.route('/welcome', methods=['GET'])
def welcome():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))
    return render_template('welcome.html')

@app.route('/import_course_data', methods=['GET', 'POST'])
def import_course_data():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(url_for('import_course_data'))

        file = request.files['file']
        if file and allowed_file(file.filename):
            try:
                df = pd.read_excel(file)
                records = df.to_dict(orient='records')
                
                gta_collection.delete_many({})
                gta_collection.insert_many(records)
                
                flash(f'Uploaded {len(records)} records successfully.', 'success')
                return redirect(url_for('display_uploaded_data'))
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Invalid file type. Please upload an Excel (.xlsx) file.', 'error')

    return render_template('import_course_data.html')

@app.route('/display_uploaded_data', methods=['GET'])
def display_uploaded_data():
    records = list(gta_collection.find({}, {'_id': 0}))  # Exclude _id from display
    if records:
        headers = records[0].keys()
        return render_template('display_uploaded_data.html', records=records, headers=headers)
    else:
        flash("No data available to display.", "warning")
        return redirect(url_for('import_course_data'))

@app.route('/upload_approval_sheet', methods=['GET', 'POST'])
def upload_approval_sheet():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(url_for('upload_approval_sheet'))

        file = request.files['file']
        if file and allowed_file(file.filename):
            try:
                # Handling Excel and CSV files
                if file.filename.endswith('.xlsx'):
                    df = pd.read_excel(file)
                elif file.filename.endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    flash('Invalid file type. Please upload an Excel (.xlsx) or CSV (.csv) file.', 'error')
                    return redirect(url_for('upload_approval_sheet'))
                
                records = df.to_dict(orient='records')
                headers = df.columns.tolist()  # Get the column names for table headers

                # Save records to your database (optional, if you want to store them)
                final_collection.delete_many({})
                final_collection.insert_many(records)

                # Flash message and pass records to the template
                flash(f'Uploaded {len(records)} records successfully.', 'success')

                # Redirect to the page to show the uploaded data
                return render_template('preview_approval_sheet.html', records=records, headers=headers)

            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Invalid file type. Please upload an Excel (.xlsx) or CSV (.csv) file.', 'error')

    return render_template('upload_approval_sheet.html')


@app.route('/preview_approval_sheet', methods=['GET'])
def preview_approval_sheet():
    records = list(final_collection.find({}, {'_id': 0}))  # Exclude _id from display
    if records:
        headers = records[0].keys()
        return render_template('preview_approval_sheet.html', records=records, headers=headers)
    else:
        flash("No data available to display.", "warning")
        return redirect(url_for('upload_approval_sheet'))

@app.route('/generate_gta_requests', methods=['POST'])
def generate_gta_requests():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

    try:
        config = load_config()
        gta_data = list(gta_collection.find())
        catalog_data = list(catalog_collection.find())

        assignments = []
        processed_courses = set()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # First pass: Process all sections and identify cross-listed pairs
        cross_listed_pairs = {}
        for row in gta_data:
            course_full = row.get("Course Num/Sec", "")
            cross_listed_delta = is_cross_listed(row, gta_data)
            
            if cross_listed_delta is not None:
                # Save the cross-listed information for later
                cross_listed_pairs[course_full] = cross_listed_delta

        # Second pass: Generate assignments
        for row in gta_data:
            course_full = row.get("Course Num/Sec", "")

            # Skip if course is already processed
            if course_full in processed_courses:
                continue

            processed_courses.add(course_full)

            max_seats = int(float(row.get("Max", 0)))
            avail_seats = int(float(row.get("Avail", 0)))
            current_enrollment = max_seats - avail_seats

            crn = row.get("CRN", "N/A")
            course_num = extract_course_number(course_full)

            # Find catalog match
            catalog_match = next(
                (course for course in catalog_data 
                 if extract_course_number(course.get("Course#", "")) == course_num),
                None
            )

            # Determine course type
            course_type = catalog_match.get('Type of course', 'Typical lecture') if catalog_match else 'Typical lecture'
            row['Course Type'] = course_type

            # Check if this is a cross-listed section that was already processed
            existing_assignment = row.get("GTA Assignment")
            if existing_assignment and existing_assignment.startswith("Cross-listed with"):
                gta_assignment = existing_assignment
            else:
                # Get GTA assignment
                gta_assignment = determine_gta_assignment(row, gta_data, config)

            # Build assignment dictionary
            assignment = {
                "CRN": crn,
                "Course Num/Sec": course_full,
                "Instructor": row.get("Instructor", "N/A"),
                "Current Enrollment": current_enrollment,
                "Course Type": course_type,
                "GTA Assignment": gta_assignment,
                "Timestamp": timestamp,
            }
            assignments.append(assignment)

            print(f"Generated assignment for {course_full}: {gta_assignment}")

        # Sort assignments by course number/section
        assignments.sort(key=lambda x: x['Course Num/Sec'])

        # Save assignments to MongoDB
        assignment_collection.delete_many({})
        if assignments:
            assignment_collection.insert_many(assignments)
            flash(f'Successfully generated {len(assignments)} GTA/SI assignments.', 'success')
        else:
            flash('No assignments could be generated.', 'warning')

        return redirect(url_for('view_requests'))

    except Exception as e:
        flash(f'Error generating assignments: {str(e)}', 'error')
        print(f"Error generating assignments: {e}")
        return redirect(url_for('display_uploaded_data'))




@app.route('/api/view_requests', methods=['GET'])
def api_view_requests():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized access'}), 401
    try:
        assignments = list(assignment_collection.find({}, {'_id': 0}))
        return jsonify(assignments)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/view_requests', methods=['GET'])
def view_requests():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))
    return render_template('view_requests.html')

@app.route('/export_requests', methods=['GET'])
def export_requests():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))
    
    try:
        assignments = list(assignment_collection.find({}, {'_id': 0}))
        if not assignments:
            flash('No assignments to export.', 'warning')
            return redirect(url_for('view_requests'))

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=assignments[0].keys())
        writer.writeheader()
        writer.writerows(assignments)
        output.seek(0)

        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=gta_assignments.csv"}
        )
    except Exception as e:
        flash(f"Error exporting assignments: {str(e)}", 'error')
        return redirect(url_for('view_requests'))
    
@app.route('/editable_approval_sheet', methods=['GET', 'POST'])
def editable_approval_sheet():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            form_data = request.form.to_dict(flat=False)
            
            for i, doc_id in enumerate(form_data.get('_id[]', [])):
                # Get the base data
                update_data = {
                    'CRN': form_data.get('CRN[]', [])[i],
                    'Course Num/Sec': form_data.get('Course_Num_Sec[]', [])[i],
                    'Instructor': form_data.get('Instructor[]', [])[i],
                    'Current Enrollment': form_data.get('Current_Enrollment[]', [])[i],
                    'Course Type': form_data.get('Course_Type[]', [])[i],
                    'GTA Assignment': form_data.get('GTA_Assignment[]', [])[i],
                    'Timestamp': form_data.get('Timestamp[]', [])[i],
                }

                # Get student assignments for this row
                student_assignments = []
                student_key = f'student_assignments[{i}][]'
                if student_key in form_data:
                    student_data = form_data[student_key]
                    if isinstance(student_data, list):
                        for student_json in student_data:
                            try:
                                student = json.loads(student_json)
                                student_assignments.append({
                                    'name': student.get('name', ''),
                                    'ksuId': student.get('ksuId', ''),
                                    'email': student.get('email', ''),
                                    'contact': student.get('contact', '')
                                })
                            except (json.JSONDecodeError, AttributeError) as e:
                                app.logger.error(f"Error parsing student data: {e}")
                                continue

                # Update MongoDB document
                update_data['student_assignments'] = student_assignments
                
                # Add any additional columns
                for col in form_data:
                    if col.endswith('[]') and col not in ['CRN[]', 'Course_Num_Sec[]', 'Instructor[]', 
                                                         'Current_Enrollment[]', 'Course_Type[]', 
                                                         'GTA_Assignment[]', 'Timestamp[]', '_id[]']:
                        col_name = col[:-2]
                        if i < len(form_data[col]):
                            update_data[col_name] = form_data[col][i]

                try:
                    final_collection.update_one(
                        {'_id': ObjectId(doc_id)},
                        {'$set': update_data}
                    )
                except Exception as e:
                    app.logger.error(f"Error updating document {doc_id}: {str(e)}")
                    continue

            flash("Approval sheet saved successfully!", 'success')
            return redirect(url_for('editable_approval_sheet'))

        except Exception as e:
            app.logger.error(f"Error saving data: {str(e)}")
            flash(f"Error saving data: {str(e)}", 'error')
            return redirect(url_for('editable_approval_sheet'))

    # GET request handling
    try:
        records = list(final_collection.find())
        added_columns = [col['name'] for col in columns_collection.find()]
        
        # Convert ObjectId to string for each record
        for record in records:
            record['_id'] = str(record['_id'])
            # Ensure student_assignments exists
            if 'student_assignments' not in record:
                record['student_assignments'] = []

        return render_template('editable_approval_sheet.html', 
                             records=records,
                             added_columns=added_columns)
    except Exception as e:
        app.logger.error(f"Error fetching data: {str(e)}")
        flash(f"Error loading approval sheet: {str(e)}", 'error')
        return redirect(url_for('welcome'))

# Add this new route to get existing students
@app.route('/get_existing_students', methods=['GET'])
def get_existing_students():
    try:
        # Get all unique students from existing assignments
        all_students = set()
        records = final_collection.find({}, {'student_assignments': 1})
        
        for record in records:
            if 'student_assignments' in record:
                for student in record['student_assignments']:
                    # Create a tuple of student info to ensure uniqueness
                    student_tuple = (
                        student.get('name', ''),
                        student.get('ksuId', ''),
                        student.get('email', ''),
                        student.get('contact', '')
                    )
                    all_students.add(student_tuple)
        
        # Convert set back to list of dictionaries
        students_list = [
            {
                'name': student[0],
                'ksuId': student[1],
                'email': student[2],
                'contact': student[3]
            }
            for student in all_students
        ]
        
        return jsonify(students_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/add_column', methods=['POST'])
def add_column():
    if 'user' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    new_column = request.form.get('column_name')
    if not new_column:
        return jsonify({'status': 'error', 'message': 'No column name provided.'}), 400

    # Sanitize the column name (basic example)
    new_column = new_column.strip().replace(' ', '_')

    # Check if the column already exists
    if columns_collection.find_one({'name': new_column}):
        return jsonify({'status': 'error', 'message': 'Column already exists.'}), 400

    # Insert the new column name into the columns_collection
    columns_collection.insert_one({'name': new_column})

    return jsonify({'status': 'success', 'message': 'Column added successfully.', 'column_name': new_column})

@app.route('/delete_column', methods=['POST'])
def delete_column():
    if 'user' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    column_name = request.form.get('column_name')
    if not column_name:
        return jsonify({'status': 'error', 'message': 'No column name provided.'}), 400

    # Check if the column exists
    if not columns_collection.find_one({'name': column_name}):
        return jsonify({'status': 'error', 'message': 'Column does not exist.'}), 400

    # Remove the column from columns_collection
    columns_collection.delete_one({'name': column_name})

    # Remove the column from all documents in approvaldata_collection
    final_collection.update_many({}, {'$unset': {column_name: ""}})

    return jsonify({'status': 'success', 'message': 'Column deleted successfully.'})



@app.route('/view_approval_sheet_data', methods=['GET'])
def view_approval_sheet_data():
    # Fetch all records from approvaldata_collection
    records = list(final_collection.find())

    # Fetch all added column names from columns_collection
    added_columns = [col['name'] for col in columns_collection.find()]

    # Pass both records and added_columns to the template
    return render_template('view_approval_sheet_data.html', records=records, added_columns=added_columns)

@app.route('/export_approval_requests', methods=['GET'])
def export_approval_requests():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))
    
    try:
        assignments = list(assignment_collection.find({}, {'_id': 0}))
        if not assignments:
            flash('No assignments to export.', 'warning')
            return redirect(url_for('view_approval_sheet_data'))

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=assignments[0].keys())
        writer.writeheader()
        writer.writerows(assignments)
        output.seek(0)

        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=gta_assignments.csv"}
        )
    except Exception as e:
        flash(f"Error exporting assignments: {str(e)}", 'error')
        return redirect(url_for('view_approval_sheet_data'))



@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

