import json
import os

# Load the existing progress.json content
progress_file_path = "progress.json"

try:
    with open(progress_file_path, 'r', encoding='utf-8') as f:
        progress_data = json.load(f)
except FileNotFoundError:
    progress_data = {}

# Directory path to read the CSV files
directory_path = "autohome_reviews_save"

# List all files in the directory
file_names = os.listdir(directory_path)

# Extract car names from file names
car_names = [os.path.splitext(name)[0].split('_')[0] for name in file_names]

# Update progress_data with the car names from the directory
for car_name in car_names:
    if car_name not in progress_data:
        progress_data[car_name] = {
            "status": "completed",
            "last_user_id": None,
            "review_progress": None
        }

# Save the updated progress_data back to progress.json
with open(progress_file_path, 'w', encoding='utf-8') as f:
    json.dump(progress_data, f, ensure_ascii=False, indent=4)

print("Progress data updated successfully.")
