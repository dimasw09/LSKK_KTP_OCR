# app_worker.py
import os
import cv2
from PIL import Image
import pytesseract
from io import BytesIO
import json
from ftplib import FTP
import numpy as np
from datetime import datetime
from difflib import SequenceMatcher
from db_connection import create_mongo_connection  
import uuid
import pika
THRESHOLD_VALUE = 125
LANG = "ind"
ALLOWED_FIELDS = ["NIK", "Nama"]
# FTP Configuration
FTP_SERVER = 'ftp5.pptik.id'
FTP_PORT = 2121
FTP_USERNAME = 'magangitg'
FTP_PASSWORD = 'bWFnYW5naXRn'
FTP_UPLOAD_DIR = '/OCR-kWh'
unique_filename = str(uuid.uuid4()) + '.png'

mongo_collection = create_mongo_connection()

dirUP = '/ktp_ocr'

def upload_to_ftp(filename, dir=dirUP,unique_filename=unique_filename):
    try:
        file_path = f'ktpFtpServer/KTP_Server/{filename}'

        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return

        print("Connecting to FTP server...")
        ftp = FTP()
        ftp.connect(FTP_SERVER, FTP_PORT)
        ftp.login(FTP_USERNAME, FTP_PASSWORD)
        print("Connected to FTP server.")

        ftp.cwd(dir)

        print(f"Uploading {filename} from {file_path} to FTP server.")
        with open(file_path, 'rb') as file:
            ftp.storbinary(f"STOR {unique_filename}", file)        
            print(f"Upload completed.")
        print(f"Uploaded {filename} to FTP server.")

        ftp.quit()
    except Exception as e:
        print(f"FTP upload failed: {str(e)}")



def download_from_ftp(filename,unique_filename=unique_filename):
    try:
        ftp = FTP()
        ftp.connect('ftp5.pptik.id', port=2121)
        ftp.login('magangitg', 'bWFnYW5naXRn')
        ftp.cwd('./ktp_ocr/')

        local_path = os.path.join("./ktp_ocr/", unique_filename)  # Use unique_filename here

        with open(local_path, 'wb') as file:
            ftp.retrbinary(f"RETR {filename}", file.write)

        print(f"Downloaded {filename} from FTP server.")

        ftp.quit()
        return local_path
    except Exception as e:
        print(f"FTP download failed: {str(e)}")
        return None

def similarity_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()

def send_image_to_queue(filename, rabbitmq_url='localhost'):
    try:
        with pika.BlockingConnection(pika.ConnectionParameters(rabbitmq_url)) as connection:
            channel = connection.channel()
            channel.queue_declare(queue='abc', durable=True)

            # Generate a unique filename using UUID
            # unique_filename = str(uuid.uuid4()) + '.png'
        if filename:
            unique_filename = unique_filename  # Assuming unique_filename is a function that generates a unique filename
            save_path = os.path.abspath(f'ktpFtpServer/KTP_Server/{unique_filename}')
            filename.save(save_path)
            upload_to_ftp(unique_filename)
            send_image_to_queue(unique_filename)

            image_info = {
                "filename": filename,
                "data": filename  # Sending the original filename to the queue
            }

            channel.basic_publish(exchange='',
                                  routing_key='abc',
                                  body=json.dumps(image_info),
                                  properties=pika.BasicProperties(
                                      delivery_mode=2,  # Make the message persistent
                                  ))

            print(f"Sent {filename} to the queue.")
            return filename, "Image sent to the queue successfully.", None
    except Exception as e:
        print(f"Failed to send image to the queue: {str(e)}")
        return None, None, f"Failed to send image to the queue: {str(e)}"

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


def process_image(filename, data):
    try:
        file_uuid = str(uuid.uuid4())
        file_extension = os.path.splitext(filename)[-1].lower()
        new_filename = f"{file_uuid}{file_extension}"

        image_temp_path = os.path.join("uploads", new_filename)

        # Save the data to a file
        with open(image_temp_path, 'wb') as file:
            file.write(data.encode('utf-8')) 
        upload_to_ftp(image_temp_path, new_filename)

        try:
            # Remove the line below
            Image.open(image_temp_path)
        except Exception as e:
            raise ValueError(f"The file {new_filename} is not a valid image.")
        extracted_text = extract_data(image_temp_path)
        extracted_data = parse_extracted_data(extracted_text)
        filtered_data = filter_data(extracted_data)

        current_time = datetime.now()
        formatted_timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
        filtered_data["create_at"] = formatted_timestamp

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


def start_worker(rabbitmq_url='localhost'):
    try:
        with pika.BlockingConnection(pika.ConnectionParameters(rabbitmq_url)) as connection:
            channel = connection.channel()
            channel.queue_declare(queue='abc', durable=True)
            channel.basic_consume(queue='abc', on_message_callback=callback, auto_ack=True)

            print(' [*] Waiting for messages. To exit press CTRL+C')
            channel.start_consuming()
    except Exception as e:
        print(f"Error starting worker: {str(e)}")

def callback(ch, method, properties, body):
    try:
        image_info = json.loads(body)
        filename = image_info["filename"]
        data = image_info["data"]

        print(f"Received image {filename} from the queue for processing.")
        path1 = upload_to_ftp(filename)
        if path1:
            print(f"Terupload")
        local_path = download_from_ftp(filename, image_info["unique_filename"])
        if local_path:
            new_filename, extracted_text, insert_result = process_image(local_path, data)

            print(f"Processed {new_filename} , {extracted_text}, {insert_result}")
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        
if __name__ == '__main__':
    start_worker()