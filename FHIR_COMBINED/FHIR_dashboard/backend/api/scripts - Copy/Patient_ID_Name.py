import os
import json

# Set the path to your folder containing all JSON files
existing_folder_path = "C:/Users/kasar/CoCM_Platform/backend/data/all_converted_files/All Converted Files"

# List all JSON files from the existing folder
all_json_files = []
for root, _, files in os.walk(existing_folder_path):
    for file in files:
        if file.endswith('.json'):
            all_json_files.append(os.path.join(root, file))

# Extract real patient names (ignoring FN### LN###)
def extract_patient_names(files):
    patient_records = {}

    for path in files:
        try:
            with open(path, 'r') as f:
                data = json.load(f)

            for entry in data.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Patient":
                    patient_id = resource.get("id")
                    name_data = resource.get("name", [{}])[0]
                    given = name_data.get("given", [""])[0]
                    family = name_data.get("family", "")
                    full_name = f"{given} {family}".strip()

                    # Skip fake names like FN### LN###
                    if full_name.startswith("FN") and "LN" in full_name:
                        continue

                    if patient_id and full_name:
                        patient_records[patient_id] = full_name
        except Exception:
            continue

    return patient_records

# Run the logic
patient_name_map = extract_patient_names(all_json_files)

# Preview the result
list(patient_name_map.items())[:10]
