import os


directory = 'data/router_data/train'
deleted_count = 0

print("Scanning for hidden Mac files...")


for root, dirs, files in os.walk(directory):
    for file in files:

        if file.startswith('._'):
            file_path = os.path.join(root, file)
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                print(f"Couldn't delete {file_path}: {e}")

print(f"🧹 Cleanup complete! Deleted {deleted_count} hidden ghost files.")