# server.py
from flask import Flask, render_template, request, flash, redirect, url_for
import os
import secrets
from datetime import datetime
import uuid
from worker import process_image, upload_to_ftp
from redist_conn import redis_queue

app = Flask(__name__)

# Constants
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
UPLOAD_FOLDER = 'uploads'

FTP_SERVER = 'localhost:2121'
FTP_USERNAME = 'dimassk7'
FTP_PASSWORD = '140289'
FTP_UPLOAD_DIRECTORY = 'ktpFtpServer'

secret_key = secrets.token_hex(16)
app.secret_key = secret_key
print(secret_key)

def allowed_file(filename): 
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if 'image' not in request.files:
            flash("No image part", 'error')
            return redirect(request.url)
        
        image_file = request.files["image"]

        if image_file.filename == "":
            flash("No selected image", 'error')
            return redirect(request.url)

# Inside the index route
        if image_file and allowed_file(image_file.filename):
            try:
                # Generate a unique UUID for the image file
                file_uuid = str(uuid.uuid4())
                file_extension = os.path.splitext(image_file.filename)[-1].lower()
                new_filename = f"{file_uuid}{file_extension}"

                # Save the image to a temporary location with the UUID filename
                image_temp_path = os.path.join(UPLOAD_FOLDER, new_filename)
                image_file.save(image_temp_path)

                # Upload the image to FTP server with the specified directory
                upload_result = upload_to_ftp(image_temp_path, new_filename, FTP_SERVER, FTP_USERNAME, FTP_PASSWORD, FTP_UPLOAD_DIRECTORY)
                if upload_result:
                    # If upload is successful, enqueue the image for processing
                    redis_queue.enqueue(process_image, new_filename)

                    current_time = datetime.now()
                    formatted_timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")

                    flash(f"Image {new_filename} uploaded successfully!", 'success')
                    return redirect(url_for("index"))
                else:
                    flash("Failed to upload image to FTP server", 'error')

            except Exception as e:
                error_message = str(e)
                flash(error_message, 'error')


    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)  # Run the Flask app with debug mode enabled
