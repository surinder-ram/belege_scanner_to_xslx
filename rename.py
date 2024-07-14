



import os

def rename_files(directory, start_number=300):
    files = os.listdir(directory)
    files.sort()  # Sort files to ensure consistent numbering

    for index, filename in enumerate(files):
        new_number = start_number + index
        new_filename = f"{new_number}_{filename}"
        old_file = os.path.join(directory, filename)
        new_file = os.path.join(directory, new_filename)

        os.rename(old_file, new_file)
        print(f"Renamed '{filename}' to '{new_filename}'")

# Verzeichnis angeben
directory_path = "C:\\Users\\surin\\Meine Ablage\\Firma\\Belege\\2023\\Versicherung Bank"

# Dateien umbenennen
rename_files(directory_path)