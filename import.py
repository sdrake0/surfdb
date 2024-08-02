import csv
import sqlite3  # Replace with your database connector if using another DB

# Define the path to your CSV file and database
csv_file = 'allmaps.csv'
database_file = 'surf.db'  # Replace with your database file if using SQLite

# Connect to the database
conn = sqlite3.connect(database_file)
cursor = conn.cursor()

# Clear existing data in the 'maps' table
cursor.execute("DELETE FROM maps")
conn.commit()

# Read the CSV file and insert data into the 'maps' table
with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
    csv_reader = csv.reader(file)
    
    # Extract header and prepare the INSERT statement
    headers = next(csv_reader)  # Assumes first row is header
    placeholders = ', '.join(['?'] * len(headers))  # Create placeholders for each column
    insert_query = f"INSERT INTO maps ({', '.join(headers)}) VALUES ({placeholders})"
    
    # Insert rows
    for row in csv_reader:
        cursor.execute(insert_query, row)

# Commit changes and close the connection
conn.commit()
conn.close()

print("Data has been successfully replaced.")