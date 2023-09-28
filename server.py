# server.py
from flask import Flask, render_template, request
import os
from datetime import datetime
import uuid
from worker import process_image
from redist_conn import redis_queue

app = Flask(__name__)

# Constants
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
UPLOAD_FOLDER = 'uploads'


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        image_file = request.files["image"]
        if image_file:
            try:
                # Generate a unique UUID for the image file
                file_uuid = str(uuid.uuid4())
                file_extension = os.path.splitext(image_file.filename)[-1].lower()
                new_filename = f"{file_uuid}{file_extension}"

                # Save the image to a temporary location with the UUID filename
                image_temp_path = os.path.join(UPLOAD_FOLDER, new_filename)
                image_file.save(image_temp_path)

                redis_queue.enqueue(process_image, image_temp_path)

                current_time = datetime.now()
                formatted_timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")

                return render_template("index.html", image_filename=new_filename, timestamp=formatted_timestamp)
            except Exception as e:
                error_message = str(e)
                return render_template("index.html", error_message=error_message)
        else:
            error_message = "No image uploaded."
            return render_template("index.html", error_message=error_message)

    return render_template("index.html")

if __name__ == "__main__":
    while True:
        job = redis_queue.dequeue()  # Mengambil pekerjaan dari antrian Redis Queue
        if job:
            image_path = job.decode("utf-8")  # Mendekode pekerjaan sebagai path gambar
            filtered_data = process_image(image_path)
            # Lakukan apa pun yang perlu Anda lakukan dengan data ini, seperti menyimpan ke MongoDB atau mengunggah ke FTP
            print(filtered_data)