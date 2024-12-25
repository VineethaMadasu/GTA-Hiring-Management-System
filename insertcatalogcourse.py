import pandas as pd
from pymongo import MongoClient

# Step 1: Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["gta_application"]  # Use your database name
collection = db["catalog_course"]  # Use your collection name

# Step 2: Read the Excel file using pandas
excel_file = r"C:\Users\Raghu\Downloads\Milestone_3_finalcode\catalog_course.xlsx"
df = pd.read_excel(excel_file)

# Step 3: Convert the DataFrame to a dictionary
data_dict = df.to_dict(orient='records')

# Step 4: Insert data into MongoDB
if data_dict:
    collection.insert_many(data_dict)  # Inserting all records at once
    print("Data inserted successfully!")
else:
    print("No data found in the Excel file.")
