# worker.py
import pika
import os
import uuid
from PIL import Image
import cv2
import numpy as np
import pytesseract
import json
import logging
from ftplib import FTP
from io import BytesIO
import datetime
from pymongo import MongoClient

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Constants
THRESHOLD_VALUE = 125
LANG = "ind"
ALLOWED_FIELDS = ["NIK", "Nama"]
RABBITMQ_HOST = 'localhost'
RABBITMQ_QUEUE = 'image_queue'
FTP_SERVER = "ftp5.pptik.id"
FTP_USERNAME = "magangitg"
FTP_PASSWORD = "bWFnYW5naXRn"
FTP_PORT = 2121
FTP_UPLOAD_DIR = '/OCR-kWh'

DIRECTORY_NAME = "./download/"
if not os.path.exists(DIRECTORY_NAME):
    os.makedirs(DIRECTORY_NAME)



def download_from_ftp(filename, direktori=FTP_UPLOAD_DIR):
    try:
        ftp = FTP()
        ftp.set_debuglevel(2) 
        ftp.connect(FTP_SERVER, FTP_PORT)
        ftp.login(FTP_USERNAME, FTP_PASSWORD)
        ftp.set_pasv(True)  # Using passive mode
        ftp.cwd(direktori)

        buffer = BytesIO()

        filename_cleaned = os.path.basename(filename).rstrip('}"')
        full_path_on_ftp = f"{direktori}/{filename_cleaned}"
        logging.info(f"Executing FTP command: RETR {full_path_on_ftp}")
        logging.info(f"Trying to download file from FTP: {full_path_on_ftp}")

        ftp.retrbinary(f'RETR "{full_path_on_ftp}"', buffer.write)
        ftp.quit()
        buffer.seek(0)
        return buffer
    except Exception as e:
        logging.error(f"FTP download error: {e}")
        return None

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

# def insert_json_data(new_filename, filtered_data):
#     try:
#         ordered_data = {"nama_file": new_filename, **filtered_data}
#         json_data = json.dumps(ordered_data, indent=3)
#         client = MongoClient('mongodb://magangitg:bWFnYW5naXRn@database2.pptik.id:27017/?authMechanism=DEFAULT&authSource=magangitg')
#         db = client['magangitg']
#         collection = db['ktp_ocr']

#         # Insert the output_data into the MongoDB collection
#         result = collection.insert_one(json_data)

#         return result
#     except Exception as e:
#         return f"Failed to insert data into MongoDB: {str(e)}"



def process_image(file_path, filename, data):
    try:
        file_uuid = str(uuid.uuid4())
        file_extension = os.path.splitext(filename)[-1].lower()
        new_filename = f"{file_uuid}{file_extension}"

        image_temp_path = os.path.join("./download/", new_filename)

        # Write the data to image_temp_path instead of file_path
        with open(image_temp_path, 'wb') as file:  
            file.write(data)  

        # Open the image using image_temp_path
        try:
            Image.open(image_temp_path)
        except Exception as e:
            raise ValueError(f"The file {new_filename} is not a valid image.")
        
        extracted_text = extract_data(image_temp_path)  # Use image_temp_path here
        extracted_data = parse_extracted_data(extracted_text)
        filtered_data = filter_data(extracted_data)

        img = Image.open(image_temp_path)
        new_width = 1040
        new_height = 780
        img = img.resize((new_width, new_height), Image.BILINEAR)

        img_np = np.array(img)  # Convert the PIL image directly to numpy array
        img = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, threshed = cv2.threshold(gray, THRESHOLD_VALUE, 200, cv2.THRESH_BINARY)

        result_image_path = os.path.join("F:\KerjaPraktik\KTP-SCAN1\hasil threshold", "T." + new_filename)
        cv2.imwrite(result_image_path, threshed, [int(cv2.IMWRITE_JPEG_QUALITY), 100])

        json_data = create_json_data(new_filename, filtered_data)
        insert_result = insert_json_data(json_data, filtered_data)

        print(f"Processed Image: {new_filename}\nExtracted Text: {extracted_text}\nInsert Result: {insert_result}")

        return new_filename, extracted_text, insert_result
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        raise e

    


def callback(ch, method, properties, body):
    try:
        file_path = body.decode("utf-8")
        filename_cleaned = os.path.basename(file_path).rstrip('}"')

        buffer = download_from_ftp(file_path)
        if buffer:
            local_path = os.path.join(DIRECTORY_NAME, filename_cleaned)
            with open(local_path, 'wb') as file:
                file.write(buffer.getvalue())

            if os.path.exists(local_path):
                process_image(local_path, filename_cleaned, buffer.getvalue())
                # Delete the temporary file
                os.remove(local_path)
            else:
                logging.error(f"File not found: {local_path}")

    except Exception as e:
        logging.error(f"Error in callback: {str(e)}")

def start_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE)
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback, auto_ack=True)
    logging.info('Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()


if __name__ == "__main__":
    try:
        start_consumer()
    except Exception as e:
        logging.error(f"Failed to start the consumer: {str(e)}")



