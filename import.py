import sqlite3
import csv

def insert_or_update_map(cursor, map_id, name, tier, type, mapper, youtube, steam, bonuses):
    try:
        cursor.execute("""
            INSERT INTO maps (map_id, name, tier, type, mapper, youtube, steam, bonuses)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                tier = COALESCE(EXCLUDED.tier, maps.tier),
                type = COALESCE(EXCLUDED.type, maps.type),
                mapper = COALESCE(EXCLUDED.mapper, maps.mapper),
                youtube = COALESCE(EXCLUDED.youtube, maps.youtube),
                steam = COALESCE(EXCLUDED.steam, maps.steam),
                bonuses = COALESCE(EXCLUDED.bonuses, maps.bonuses)
        """, (map_id, name, tier, type, mapper, youtube, steam, bonuses))
    except sqlite3.IntegrityError as e:
        print(f"Error inserting/updating map {name}: {e}")

# Connect to the SQLite database
conn = sqlite3.connect('surf.db')
cursor = conn.cursor()

# Open the CSV file
with open('importmaps2.csv', 'r') as file:
    csv_reader = csv.reader(file)
    
    # Skip the header row
    next(csv_reader)
    
    # Iterate over each row in the CSV file
    for row in csv_reader:
        map_id, name, tier, type, mapper, youtube, steam, bonuses = row
        
        # Convert map_id to integer, if necessary
        map_id = int(map_id) if map_id else None
        
        # Convert tier and bonuses to floats, if necessary
        tier = float(tier) if tier else None
        bonuses = int(bonuses) if bonuses else None
        
        # Insert or update the map
        insert_or_update_map(cursor, map_id, name, tier, type, mapper, youtube, steam, bonuses)

# Commit the changes
conn.commit()

# Close the connection
conn.close()

print("Maps data inserted or updated successfully.")