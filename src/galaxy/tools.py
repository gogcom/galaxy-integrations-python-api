import io
import os
import zipfile
from glob import glob


def zip_folder(folder):
    files = glob(os.path.join(folder, "**"), recursive=True)
    files = [file.replace(folder + os.sep, "") for file in files]
    files = [file for file in files if file]

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            zipf.write(os.path.join(folder, file), arcname=file)
    return zip_buffer


def zip_folder_to_file(folder, filename):
    zip_content = zip_folder(folder).getbuffer()
    with open(filename, "wb") as archive:
        archive.write(zip_content)
