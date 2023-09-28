# worker.py

from PIL import Image
import cv2
import os
import numpy as np
from celery import Celery
import pytesseract
from difflib import SequenceMatcher
from ftplib import FTP
import json
from redis import Redis
from rq import Queue, get_current_job
from db_connection import create_mongo_connection


THRESHOLD_VALUE = 125
ALLOWED_FIELDS = ["NIK", "Nama"]
LANG = "ind"

mongo_collection = create_mongo_connection()

app = Celery('worker', broker='pyamqp://guest@localhost//')

def similarity_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()

def extract_data(image_path):
    try:
        with open(image_path, "rb") as img_file:
            img = cv2.imdecode(np.frombuffer(img_file.read(), np.uint8), cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, threshed = cv2.threshold(gray, THRESHOLD_VALUE, 200, cv2.THRESH_BINARY)

        result = pytesseract.image_to_string(threshed, lang=LANG, config='--psm 6 --oem 3 --dpi 300 -c tessedit_char_blacklist=@#$?%^&*()- ')
        return result
    except Exception as e:
        return str(e)

def parse_extracted_data(extracted_text):
    data = {}
    lines = extracted_text.split("\n")
    nik = ""
    nama = ""

    for line in lines:
        for field in ALLOWED_FIELDS:
            if field in line:
                field_value = line.split(':', 1)
                if len(field_value) == 2:
                    field, value = field_value
                    data[field.strip()] = value.strip()
                else:
                    # Jika ":" tidak ada, ambil angka sebagai NIK
                    nik_parts = line.split()
                    for part in nik_parts:
                        if part.isdigit() and len(part) >= 10:
                            nik = part
                            data["NIK"] = nik
                            break
                    # Jika bukan angka, anggap sebagai Nama
                    if not nik:
                        nama = line.strip()
                        data["Nama"] = nama
    return data

def filter_data(data):
    return {field: data[field] for field in ALLOWED_FIELDS if field in data}

def process_image(image_filename):
    ftp_file_path = os.path.join('ktpFtpServer', image_filename)

    extracted_text = extract_data(ftp_file_path)
    extracted_data = parse_extracted_data(extracted_text)
    filtered_data = filter_data(extracted_data)
    return filtered_data



def resize_image(image_path, new_width, new_height):
    img = Image.open(image_path)
    img = img.resize((new_width, new_height), Image.BILINEAR)
    return img

def threshold_image(image_path, output_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, threshed = cv2.threshold(gray, THRESHOLD_VALUE, 200, cv2.THRESH_BINARY)
    cv2.imwrite(output_path, threshed, [int(cv2.IMWRITE_JPEG_QUALITY), 100])

def create_json_data(new_filename, filtered_data):
    ordered_data = {"nama_file": new_filename, **filtered_data}
    json_data = json.dumps(ordered_data, indent=3)
    return json_data

def insert_json_data(json_data):
    try:
        # Menambahkan JSON data ke MongoDB
        mongo_collection.insert_one(json.loads(json_data))
        return "Data inserted into MongoDB successfully."
    except Exception as e:
        return f"Failed to insert data into MongoDB: {str(e)}"
    
def upload_to_ftp(file_path, ftp_server, ftp_username, ftp_password):
    try:
        ftp = FTP(ftp_server)
        ftp.login(ftp_username, ftp_password)
        with open(file_path, 'rb') as file:
            ftp.storbinary('STOR ' + os.path.basename(file_path), file)
        ftp.quit()
        return True
    except Exception as e:
        return str(e)