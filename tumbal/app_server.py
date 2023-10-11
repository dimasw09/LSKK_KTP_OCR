#server.py
from flask import Flask, request, jsonify
from app_worker import send_image_to_queue, unique_filename, upload_to_ftp


app = Flask(__name__)

@app.route("/", methods=["POST"])
def index():
    # Check if the request has a file attached
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded."}), 400

    image_file = request.files["image"]
    
    # Check if the file is empty
    if image_file.filename == '':
        return jsonify({"error": "No selected image."}), 400

    try:

        if image_file:
            image_file.save('ktpFtpServer/KTP_Server/'+ unique_filename)
            upload_to_ftp(image_file.filename)
            send_image_to_queue(image_file.filename)
            
        return image_file.filename
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
