# from flask import Flask, render_template, request, send_from_directory
# import os
# import cv2
# from PIL import Image
# import pytesseract
# import json
# import numpy as np
# from difflib import SequenceMatcher
# from datetime import datetime
# from db_connection import create_mongo_connection  
# import uuid


# app = Flask(__name__)

# # Constants
# THRESHOLD_VALUE = 125
# LANG = "ind"
# ALLOWED_FIELDS = ["NIK", "Nama"]

# mongo_collection = create_mongo_connection()

# def similarity_ratio(a, b):
#     return SequenceMatcher(None, a, b).ratio()

# def calculate_accuracy(ground_truth, extracted_text):
#     return similarity_ratio(ground_truth, extracted_text) * 100

# def extract_data(image_path):
#     try:
#         with open(image_path, "rb") as img_file:
#             img = cv2.imdecode(np.frombuffer(img_file.read(), np.uint8), cv2.IMREAD_COLOR)
        
#         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#         _, threshed = cv2.threshold(gray, THRESHOLD_VALUE, 200, cv2.THRESH_BINARY)

#         result = pytesseract.image_to_string(threshed, lang=LANG, config='--psm 6 --oem 3 --dpi 300 -c tessedit_char_blacklist=@#$?%^&*()- ')
#         return result
#     except Exception as e:
#         return str(e)

# def parse_extracted_data(extracted_text):
#     data = {}
#     lines = extracted_text.split("\n")
#     nik = ""
#     nama = ""

#     for line in lines:
#         for field in ALLOWED_FIELDS:
#             if field in line:
#                 field_value = line.split(':', 1)
#                 if len(field_value) == 2:
#                     field, value = field_value
#                     data[field.strip()] = value.strip()
#                 else:
#                     # Jika ":" tidak ada, ambil angka sebagai NIK
#                     nik_parts = line.split()
#                     for part in nik_parts:
#                         if part.isdigit() and len(part) >= 10:
#                             nik = part
#                             data["NIK"] = nik
#                             break
#                     # Jika bukan angka, anggap sebagai Nama
#                     if not nik:
#                         nama = line.strip()
#                         data["Nama"] = nama
#     return data

# def filter_data(data):
#     return {field: data[field] for field in ALLOWED_FIELDS if field in data}

# def create_json_data(new_filename, filtered_data):
#     ordered_data = {"nama_file": new_filename, **filtered_data}
#     json_data = json.dumps(ordered_data, indent=3)
#     return json_data

# def insert_json_data(json_data):
#     try:
#         # Menambahkan JSON data ke MongoDB
#         mongo_collection.insert_one(json.loads(json_data))
#         return "Data inserted into MongoDB successfully."
#     except Exception as e:
#         return f"Failed to insert data into MongoDB: {str(e)}"

# @app.route('/uploads/<filename>')
# def uploaded_image(filename):
#     return send_from_directory("uploads", filename)

# @app.route("/", methods=["GET", "POST"])
# def index():
#     if request.method == "POST":
#         image_file = request.files["image"]
#         if image_file:
#             try:
#                 # Membuat UUID unik untuk file gambar
#                 file_uuid = str(uuid.uuid4())

#                 file_extension = os.path.splitext(image_file.filename)[-1].lower()

#                 new_filename = f"{file_uuid}{file_extension}"

#                 # Menyimpan gambar di lokasi sementara dengan nama file yang diubah menjadi UUID
#                 image_temp_path = os.path.join("uploads", new_filename)
#                 image_file.save(image_temp_path)
                
#                 permanent_image_path = os.path.join("F:\KerjaPraktik\KTP-SCAN1\ktpFtpServer", new_filename)
#                 image_file.save(permanent_image_path)

#                 extracted_text = extract_data(image_temp_path)

#                 extracted_data = parse_extracted_data(extracted_text)
#                 filtered_data = filter_data(extracted_data)
#                 current_time = datetime.now()
#                 formatted_timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
#                 filtered_data["create_at"] = formatted_timestamp

#                 img = Image.open(image_temp_path)
#                 new_width = 1040
#                 new_height = 780                
#                 img = img.resize((new_width, new_height), Image.BILINEAR)
#                 print('height : ', img.height)
#                 print('width : ', img.width)
                
#                 img_np = np.fromfile(image_temp_path, np.uint8)
#                 img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

#                 gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#                 _, threshed = cv2.threshold(gray, THRESHOLD_VALUE, 200, cv2.THRESH_BINARY)

#                 # Simpan hasil thresholding (threshed) sebagai gambar
#                 result_image_path = os.path.join("F:\KerjaPraktik\KTP-SCAN1\hasil threshold", "T." + new_filename)
#                 cv2.imwrite(result_image_path, threshed, [int(cv2.IMWRITE_JPEG_QUALITY), 100])

#                 json_data = create_json_data(new_filename, filtered_data)  # Menggunakan new_filename di sini

#                 insert_result = insert_json_data(json_data)

#                 return render_template("index.html", json_data=json_data, result=extracted_text, image_filename=new_filename, insert_result=insert_result)
#             except Exception as e:
#                 error_message = str(e)
#                 return render_template("index.html", error_message=error_message)
#         else:
#             error_message = "No image uploaded."
#             return render_template("index.html", error_message=error_message)

#     return render_template("index.html")

# if __name__ == "__main__":
#     app.run(debug=True)