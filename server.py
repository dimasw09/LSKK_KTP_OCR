# server.py
from flask import Flask, render_template, request
# from worker import unique_filename
import uuid
import pika
import os
from ftplib import FTP

FTP_SERVER = 'ftp5.pptik.id'
FTP_PORT = 2121
FTP_USERNAME = 'magangitg'
FTP_PASSWORD = 'bWFnYW5naXRn'
FTP_UPLOAD_DIR = '/ktp_ocr'

unique_filename = str(uuid.uuid4()) + '.png'

app = Flask(__name__)

# RabbitMQ configurations
RABBITMQ_HOST = 'localhost'
RABBITMQ_QUEUE = 'image_queue'


def send_to_queue(file_path):
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE)
    channel.basic_publish(exchange='', routing_key=RABBITMQ_QUEUE, body=file_path)
    connection.close()

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

@app.route("/", methods=["POST"])
def index():
    if request.method == "POST":
        image_file = request.files["image"]
        if image_file:
            try:
                # Generate a unique filename
                file_uuid = str(uuid.uuid4())
                file_extension = os.path.splitext(image_file.filename)[-1].lower()
                new_filename = f"{file_uuid}{file_extension}"

                # Save the image temporarily
                temp_path = os.path.join("uploads", new_filename)
                image_file.save(temp_path)

                # Send the file path to the message queue
                send_to_queue(temp_path)

                # Upload the file to FTP server
                upload_to_ftp(temp_path, new_filename)  # Ensure you pass both arguments

                return "File uploaded successfully."
            except Exception as e:
                error_message = str(e)
                return error_message
        else:
            error_message = "No image uploaded."
            return error_message

if __name__ == "__main__":
    app.run(debug=True)