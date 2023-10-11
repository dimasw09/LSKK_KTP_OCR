# server.py
from flask import Flask, render_template, request, url_for, send_from_directory
from run import load_encoder, process_single_image
from pymongo import MongoClient
import os
import cv2
from datetime import datetime
import pytz
import dlib 
import pika
from ftplib import FTP, error_perm

app = Flask(_name_)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png'}
app.config['PROCESSED_FOLDER'] = 'static/processed_images'

def get_current_time():
    tz = pytz.timezone('Asia/Jakarta')
    now = datetime.now(tz)
    return now.strftime('%Y-%m-%d %H:%M:%S')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if not os.path.exists(app.config['PROCESSED_FOLDER']):
    os.makedirs(app.config['PROCESSED_FOLDER'])

client = MongoClient('mongodb://localhost:27017/')
db = client['reports_lskk']

try: 
    print("Successfully connected to MongoDB")
except:
    print("Could not connect to MongoDB")

def send_message_to_worker(filename):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='report_lskk')
    channel.basic_publish(exchange='', routing_key='report_lskk', body=filename)

    print(f"Pesan terkirim ke worker: {filename}")

    connection.close()

@app.route('/')
def index():
    current_time = get_current_time()
    return render_template('mongo.html', result=None, current_time=current_time)

def send_file(file):
    ftp = FTP()
    ftp.connect('localhost')
    ftp.login('shoya', '12345')
    with open(file, 'rb') as f:
        ftp.storbinary('STOR' + f)
    print(f"File {file} berhasil dikirim ke server FTP")
    ftp.quit() 

@app.route('/test', methods=['GET'])
def test():
    return "test ok"

@app.route('/process_image', methods=['POST'])
def process_image():
    print('process image')
    current_time = get_current_time()
    if 'data' not in request.files:
        return 'No image part'
    file = request.files['data']

    if file.filename == '':
        return 'No selected file'

    if file:
        # print('nama file : ',file.filename)
        path = './downloads/downloads/'
        file.save(path + file.filename)
        send_message_to_worker(file.filename)
        # print(file)
        return {'filename': file.filename}
        # filename = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_uploaded_image.jpg')

        # # Load encoder
        # encoder_filename = 'final_training.p'
        # encoder = load_encoder(encoder_filename)

        # # Load image and detect faces with dlib
        # img = cv2.imread(filename)
        # detector = dlib.cnn_face_detection_model_v1('mmod_human_face_detector.dat')
        # faces = detector(img, 1)

        # if len(faces) != 1:
        #     # Either no face or more than 1 face detected
        #     os.remove(filename)
        #     result = {
        #         'result': 'Upload an image with exactly 1 face.',
        #         'image_path': None,
        #         'detected_faces': [],
        #         'multiple_faces_detected': True
        #     }
        #     return render_template('mongo.html', result=result)
        
        # # Process single image
        # try:
        #     result = process_single_image(filename, encoder)
            
        #     # Save processed image
        #     processed_filename = os.path.join(app.config['PROCESSED_FOLDER'], file.filename)  
        #     cv2.imwrite(processed_filename, result['processed_image'])

        #     result['image_path'] = url_for('static', filename='processed_images/' + file.filename)
        #     result['multiple_faces_detected'] = False

        #     data = {
        #         'name': result['detected_faces'][0]['identity'],
        #         'probability': result['detected_faces'][0]['probability'],
        #         'upload_time': current_time,
        #         'image_path': 'static/processed_images/' + file.filename  # Gunakan nama file asli
        #     }

        #     db.lskk_face.insert_one(data)
        #     send_message_to_worker(file.filename)

        #     return render_template('mongo.html', result=result)

        # except Exception as e:
        #     result = {
        #         'result': 'Error processing image.',
        #         'image_path': None,
        #         'detected_faces': [],
        #         'multiple_faces_detected': True
        #     }
        #     return render_template('mongo.html', result=result, current_time=current_time)
    
    # return 'Error processing image.'

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(app.config['UPLOAD_FOLDER'], filename)


if _name_ == '_main_':
    app.run(debug=True, port=8080)