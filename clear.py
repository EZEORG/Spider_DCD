import os
import shutil

def clear_directory(directory):
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    else:
        print(f'Directory {directory} does not exist.')

def main():
    directories_to_clear = ['autohome_reviews', 'dcd_data']
    for directory in directories_to_clear:
        clear_directory(directory)
        print(f'Directory {directory} has been cleared.')

if __name__ == "__main__":
    main()
