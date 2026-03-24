import json
import os
import pymysql
from glob import glob

# DB config (use dotenv or hardcode for now)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'youruser',
    'password': 'yourpass',
    'database': 'yourdb',
    'cursorclass': pymysql.cursors.DictCursor
}

# Step 1: Parse FHIR JSON and extract location info
def extract_location_info(fhir_file):
    with open(fhir_file, 'r') as f:
        data = json.load(f)

    city = state = postal_code = patient_id = None

    for entry in data.get('entry', []):
        resource = entry.get('resource', {})
        if resource.get('resourceType') == 'Patient':
            patient_id = resource.get('id')
            address = resource.get('address', [{}])[0]
            city = address.get('city')
            state = address.get('state')
            postal_code = address.get('postalCode')

    return patient_id, city, state, postal_code


# Step 2: Upsert into hospital_locations and update patients
def backfill_locations(fhir_folder):
    conn = pymysql.connect(**DB_CONFIG)
    with conn:
        cursor = conn.cursor()

        for file_path in glob(os.path.join(fhir_folder, '*.json')):
            patient_id, city, state, postal_code = extract_location_info(file_path)
            if not (patient_id and city and state and postal_code):
                print(f"Skipping incomplete: {file_path}")
                continue

            # Insert or get location ID
            cursor.execute("""
                SELECT id FROM hospital_locations
                WHERE city=%s AND state=%s AND postal_code=%s
            """, (city, state, postal_code))
            result = cursor.fetchone()

            if result:
                location_id = result['id']
            else:
                cursor.execute("""
                    INSERT INTO hospital_locations (city, state, postal_code, hospital_name, latitude, longitude)
                    VALUES (%s, %s, %s, %s, 0, 0)
                """, (city, state, postal_code, f"{city} General Hospital"))
                location_id = cursor.lastrowid

            # Update patients table with foreign key
            cursor.execute("""
                UPDATE patients SET location_id=%s WHERE id=%s
            """, (location_id, patient_id))

            conn.commit()
            print(f"Updated patient {patient_id} with location_id {location_id}")

