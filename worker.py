# worker.py
import pika
import os
from flask import Flask
import uuid
from PIL import Image
from server import upload_to_ftp, FTP
import cv2
import numpy as np
import pytesseract
import json
from db_connection import create_mongo_connection
import datetime

app = Flask(__name__)

THRESHOLD_VALUE = 125
LANG = "ind"
ALLOWED_FIELDS = ["NIK", "Nama"]

# RabbitMQ configurations
RABBITMQ_HOST = 'localhost'
RABBITMQ_QUEUE = 'image_queue'
mongo_collection = create_mongo_connection()

unique_filename = str(uuid.uuid4()) + '.png'
# FTP configurations
FTP_SERVER = 'ftp5.pptik.id'
FTP_PORT = 2121
FTP_USERNAME = 'magangitg'
FTP_PASSWORD = 'bWFnYW5naXRn'
FTP_UPLOAD_DIR = '/ktp_ocr'

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
                    nik_parts = line.split()
                    for part in nik_parts:
                        if part.isdigit() and len(part) >= 10:
                            nik = part
                            data["NIK"] = nik
                            break
                    if not nik:
                        nama = line.strip()
                        data["Nama"] = nama
    return data

def filter_data(data):
    return {field: data[field] for field in ALLOWED_FIELDS if field in data}

def create_json_data(new_filename, filtered_data):
    ordered_data = {"nama_file": new_filename, **filtered_data}
    json_data = json.dumps(ordered_data, indent=3)
    return json_data

def insert_json_data(new_filename, filtered_data):
    try:
        ordered_data = {"nama_file": new_filename, **filtered_data}
        json_data = json.dumps(ordered_data, indent=3)
        mongo_collection.insert_one(json.loads(json_data))
        return "Data inserted into MongoDB successfully."
    except Exception as e:
        return f"Failed to insert data into MongoDB: {str(e)}"



def process_image(file_path, filename, data):
    try:
        file_uuid = str(uuid.uuid4())
        file_extension = os.path.splitext(filename)[-1].lower()
        new_filename = f"{file_uuid}{file_extension}"

        image_temp_path = os.path.join("./downloAD/", new_filename)

        with open(file_path, 'wb') as file:  # Open the file in binary mode
            file.write(data)  # Write binary data directly

        upload_to_ftp(file_path, new_filename)

        try:
            Image.open(file_path)
        except Exception as e:
            raise ValueError(f"The file {new_filename} is not a valid image.")
        extracted_text = extract_data(file_path)
        extracted_data = parse_extracted_data(extracted_text)
        filtered_data = filter_data(extracted_data)

        # # current_time = datetime.datetime.now()
        # formatted_timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
        # filtered_data["create_at"] = formatted_timestamp

        img = Image.open(image_temp_path)
        new_width = 1040
        new_height = 780
        img = img.resize((new_width, new_height), Image.BILINEAR)

        img_np = np.fromfile(image_temp_path, np.uint8)
        img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, threshed = cv2.threshold(gray, THRESHOLD_VALUE, 200, cv2.THRESH_BINARY)

        result_image_path = os.path.join("F:\KerjaPraktik\KTP-SCAN1\hasil threshold", "T." + new_filename)
        cv2.imwrite(result_image_path, threshed, [int(cv2.IMWRITE_JPEG_QUALITY), 100])

        json_data = create_json_data(new_filename, filtered_data)
        insert_result = insert_json_data(json_data, filtered_data)

        return new_filename, extracted_text, insert_result
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        raise e
    

def download_from_ftp(local_path, filename):
    try:
        ftp = FTP()
        ftp.connect('ftp5.pptik.id', port=2121)
        ftp.login('magangitg', 'bWFnYW5naXRn')
        ftp.set_pasv(True)  # Use passive mode
        ftp.cwd('/ktp_ocr/')  # Use the correct FTP directory

        local_path = os.path.join("./downloAD/", filename)  # Use the correct local directory

        print(f"Downloading {filename} from FTP server to {local_path}.")

        with open(local_path, 'wb') as file:
            ftp.retrbinary(f"RETR {filename}", file.write)

        print(f"Downloaded {filename} from FTP server.")

        ftp.quit()
        return local_path
    except Exception as e:
        print(f"FTP download failed: {str(e)}")
        return None



def callback(ch, method, properties, body):
    file_path = body.decode("utf-8")
    filename = os.path.basename(file_path)
    download_path = download_from_ftp(file_path, filename)
    
    if download_path:
        with open(download_path, 'rb') as file:  # Open the file in binary mode
            data = file.read()
        
        process_image(download_path, filename, data)
        os.remove(download_path)


def start_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE)
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback, auto_ack=True)
    print('Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

def upload_to_ftp(file_path, filename):
    try:
        ftp = FTP()
        ftp.connect(FTP_SERVER, FTP_PORT)
        ftp.login(FTP_USERNAME, FTP_PASSWORD)
        ftp.cwd(FTP_UPLOAD_DIR)

        print(f"Uploading {filename} to FTP server.")
        with open(file_path, 'rb') as file:
            ftp.storbinary(f"STOR {filename}", file)

        print(f"Upload completed for {filename}.")
        ftp.quit()
    except Exception as e:
        print(f"FTP upload failed: {str(e)}")

if __name__ == "__main__":
    start_consumer()
