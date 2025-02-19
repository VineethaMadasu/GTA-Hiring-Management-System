# GTA-Hiring-Management-System
A Flask web-based application built with Python Flask and MongoDB to automate and streamline the hiring process for Graduate Teaching Assistants. Features include GTA request automation, cross-listing detection, real-time data updates, and validation logic. Led project planning, task delegation, and development to ensure seamless delivery.
Features
1.User Management:
   User registration, login, logout, and password reset.
   Secure password hashing with werkzeug.security.
2.Data Import and Processing:
   Upload course data in .xlsx or .csv formats.
   Save, display, and edit imported course data.
   Generate GTA assignments dynamically based on predefined rules.
3.Dynamic GTA Assignment:
   Automatically determine assignments based on course type, enrollment, and cross-listing.
   Configurable rules using a JSON file (gta_rules.json).
4.Approval Management:
   Upload approval data files.
   Edit approval sheet data with dynamically added columns.
   Export data in .csv format.
5.Cross-listing Detection:
   Identify and handle hybrid and online course cross-listing scenarios.
6.Interactive Features:
   Add or remove custom columns in approval sheets.
   Preview and modify student assignments directly from the web interface.
________________________________________
Requirements
Python Dependencies
•Flask
•pymongo
•pandas
•werkzeug
•bson
Additional Requirements
•MongoDB (Running on localhost:27017)
•Excel files (.xlsx) or CSV files for data uploads.
________________________________________
#Installation
1.Clone the Repository:
    bash
    Copy code
     git clone https://github.com/vineetha346/GTA-Hiring-Management-System
    cd Milestone_3_finalcode
2. Set Up Virtual Environment:
     python3 -m venv venv
    source venv/bin/activate # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
3.Database Setup:
    Ensure MongoDB is running locally on port 27017.
    the following collections will be created automatically:
	users, gta_data, gta_assignments, catalog_course, final_approval_data, columns.
4. **Run the insertcatalogcourse.py Script: 
Before starting the application, you must run the insertcatalogcourse.py script to insert catalog course data into the database. This step is only required once, at the beginning of application usage: **
bash
 python insertcatalogcourse.py
5.Run the Application:
    python app.py
6.Access the Application: Open http://127.0.0.1:5000 in your browser.
________________________________________
File Structure
php
Copy code
gta-management/
├── app.py                # Main application file
├── templates/            # HTML templates
├── static/               # Static files (CSS, JS)
├── uploads/              # Uploaded files directory
├── insertcatalogcourse.py # Script to populate catalog course data
├── requirements.txt      # Python dependencies
└── README.md             # Documentation
________________________________________
Configuration
1.	Secret Key: Modify the app.secret_key in app.py for better security.
2.	File Uploads: Supported file types are .xlsx and .csv. Files are saved in the upload’s directory.
3.	Rules Configuration: Customize GTA assignment rules in the gta_rules.json file.
________________________________________
Usage Instructions
1.Run Catalog Script: Ensure you run insertcatalogcourse.py before starting the application.
2.User Management:
    Register an account or log in with existing credentials.
    Reset password if needed.
3.Course Data Import:
    Navigate to "Import Course Data" and upload your file.
    View and verify uploaded data in the "Uploaded Data" section.
4.Generate GTA Assignments:
   Generate assignments using predefined rules.
   Review assignments in the "View Requests" section.
5.Approval Management:
   Upload approval data for review.
   Edit data dynamically and export as needed.
6.Export Data:
   Download assignments or approval data in .csv format for external use.
________________________________________
API Endpoints
Public Endpoints
•/ - Login page
•/create_account - User registration
•/forgot_password - Password recovery
Secured Endpoints
•/import_course_data - Upload course data
•/generate_gta_requests - Generate assignments
•/export_requests - Export assignments as .csv
•/upload_approval_sheet - Upload approval sheet
•/editable_approval_sheet - Edit approval data dynamically
________________________________________
Troubleshooting
1.MongoDB Connection:
   Ensure MongoDB is running on localhost:27017.
   Check for collection names matching the app's requirements.
2.File Upload Errors:
   Ensure uploaded files are in .xlsx or .csv format.
   Verify the file structure matches the expected columns.
3.Debugging: Run the app in debug mode for detailed error logs:
4. If GTA requests are not generated, ensure the gta_rules.json file is correctly formatted and it is in correct folder.
