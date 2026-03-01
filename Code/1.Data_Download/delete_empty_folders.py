import os

def delete_empty_folders(root_folder):
    # Walk bottom-up so subfolders are handled before parents
    for root, dirs, files in os.walk(root_folder, topdown=False):
        # If no files and no subdirectories remain → folder is empty
        if not dirs and not files:
            try:
                os.rmdir(root)
                print(f"Deleted empty folder: {root}")
            except OSError as e:
                print(f"Could not delete {root}: {e}")

# Path to your images folder
images_folder = "images"

delete_empty_folders(images_folder)
