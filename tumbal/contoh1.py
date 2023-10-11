#worker.py
import cv2
from ultralytics import YOLO
import pytesseract
import pika
import json
import os
from pymongo import MongoClient
from datetime import datetime
import numpy as np
from ftplib import FTP
from io import BytesIO


FTP_SERVER = 'ftp5.pptik.id'
FTP_PORT = 2121
FTP_USERNAME = 'magangitg'
FTP_PASSWORD = 'bWFnYW5naXRn'
FTP_UPLOAD_DIR = '/OCR-kWh'

def download_from_ftp(filename, direktori=FTP_UPLOAD_DIR):
    try:
        ftp = FTP()
        ftp.connect(FTP_SERVER, FTP_PORT)
        ftp.login(FTP_USERNAME, FTP_PASSWORD)
        ftp.cwd(direktori)  # Change directory to where the file was uploaded
        
        buffer = BytesIO()
        full_path_on_ftp = os.path.join(direktori, os.path.basename(filename))
        ftp.retrbinary('RETR ' + full_path_on_ftp, buffer.write)

        
        ftp.quit()
        buffer.seek(0)  # Reset buffer position to the start
        return buffer
    except Exception as e:
        print(f"FTP download error: {e}")
        return None

def process_image(filename, buffer):
    
    file_bytes = np.asarray(bytearray(buffer.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    # Initialize YOLO model
    model = YOLO(r'runs\detect\train2\weights\best.pt')
    results = model(img)

    custom_oem_psm_config = r'--oem 3 --psm 8 outputbase digits'
    bounding_boxes = []

    for result in results:
        boxes = result.boxes.numpy()
        for box in boxes:
            r = box.xyxy[0].astype(int)
            cropped = img[r[1]:r[3], r[0]:r[2]]

            grayscale = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(grayscale, (5, 5), 0)
            preprocessed = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
            detected_numbers = pytesseract.image_to_string(preprocessed, config=custom_oem_psm_config).strip()

            bounding_boxes.append({
                "box": [int(val) for val in r],
                "hasil": detected_numbers
            })

    output_data = {
        "namafile": os.path.basename(filename),
        "boundingBoxes": bounding_boxes,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # Initialize MongoDB client inside the function
    client = MongoClient('mongodb://magangitg:bWFnYW5naXRn@database2.pptik.id:27017/?authMechanism=DEFAULT&authSource=magangitg')
    db = client['magangitg']
    collection = db['OCR_kWh']

    # Insert the output_data into the MongoDB collection
    result = collection.insert_one(output_data)

    output_data['_id'] = str(result.inserted_id)

    json_output = json.dumps(output_data, indent=4, default=str)
    

    return json_output


def callback(ch, method, properties, body):
    message = json.loads(body.decode("utf-8"))
    filename = message["filename"]
    
    # Download the file from FTP server
    buffer = download_from_ftp(filename)
    
    if buffer:
        result = process_image(filename, buffer)
        print(f"processed: {result}")
    else:
        print(f"Failed to download: {buffer}")


if _name_ == "_main_":
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()
    queue_name = "image_queue"
    channel.queue_declare(queue=queue_name)

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    print("[*] Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()
    
    #server.py
from flask import Flask, request, jsonify, render_template
import os
from ftplib import FTP
import pika
import json
from datetime import datetime

app = Flask(_name_)
UPLOAD_FOLDER = 'uploads'  # Anda perlu mengatur ini ke jalur folder yang sesuai
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='image_queue')

# FTP Configuration
FTP_SERVER = 'ftp5.pptik.id'
FTP_PORT = 2121
FTP_USERNAME = 'magangitg'
FTP_PASSWORD = 'bWFnYW5naXRn'
FTP_UPLOAD_DIR = '/OCR-kWh'


def send_message_to_rabbitmq(filename):
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()

    # Mendeklarasikan nama queue yang akan digunakan
    queue_name = "image_queue"

    # Mengirim pesan ke RabbitMQ
    channel.queue_declare(queue=queue_name)
    message = {"filename": filename}
    channel.basic_publish(exchange="", routing_key=queue_name, body=json.dumps(message))

    connection.close()


def upload_to_ftp(file, ftp_path, direktori=FTP_UPLOAD_DIR):
    try:
        ftp = FTP()
        ftp.connect(FTP_SERVER, FTP_PORT)
        ftp.login(FTP_USERNAME, FTP_PASSWORD)
        ftp.cwd(direktori)

        with open(file, "rb") as f:
            ftp.storbinary(f"STOR {ftp_path}", f)
        ftp.quit()
        return True
    except Exception as e:
        print(f"FTP upload error: {e}")
        return False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    
    if "file" not in request.files:
        return jsonify({"error": "No file part"})

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"})
    if file:
        filename = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(filename)
        send_message_to_rabbitmq(filename)  # Mengirim pesan ke RabbitMQ

        print(f"Uploaded file name: {file.filename}")
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Current date: {current_date}")

        # Mengunggah file ke FTP server
        ftp_path = file.filename
        if upload_to_ftp(filename, ftp_path):
            print(f"File uploaded to FTP server at: {ftp_path}")
        else:
            print("Failed to upload file to FTP server")

        return jsonify("succesfully")


if _name_ == "_main_":
    app.run(debug=True)