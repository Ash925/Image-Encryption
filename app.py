from flask import Flask, render_template, request, send_file
import numpy as np
from cryptography.fernet import Fernet
import cv2
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
KEY_FILE = "secret.key"

def save_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)

def load_key():
    return open(KEY_FILE, "rb").read()

save_key()  # Ensure key is saved once
KEY = load_key()
cipher_suite = Fernet(KEY)

def encrypt_image(image_path, message, password):
    img = cv2.imread(image_path)
    img_shape = img.shape  # Save image dimensions
    img_bytes = img.tobytes()
    
    shape_str = f"{img.shape[0]}x{img.shape[1]}x{img.shape[2]}"
    shape_str = shape_str.ljust(20)  # Fixed size for consistency
    
    message = message.ljust(100)  # Ensure fixed message length
    encrypted_data = cipher_suite.encrypt((shape_str + message).encode() + img_bytes)
    
    encrypted_path = os.path.join(UPLOAD_FOLDER, 'encrypted.bin')
    with open(encrypted_path, 'wb') as f:
        f.write(encrypted_data)
    
    return encrypted_path

def decrypt_image(encrypted_path, password):
    with open(encrypted_path, 'rb') as f:
        encrypted_data = f.read()
    
    decrypted_data = cipher_suite.decrypt(encrypted_data)
    
    shape_str = decrypted_data[:20].decode(errors='ignore').strip()
    height, width, channels = map(int, shape_str.split('x'))
    
    img_size = height * width * channels
    actual_img_data = decrypted_data[120:]  # Skipping metadata and message
    
    if len(actual_img_data) != img_size:
        raise ValueError(f"Decrypted image data size {len(actual_img_data)} does not match expected {img_size}")
    
    img_array = np.frombuffer(actual_img_data, dtype=np.uint8).reshape((height, width, channels))
    message = decrypted_data[20:120].decode(errors='ignore').strip()  # Extract message
    
    decrypted_img_path = os.path.join(UPLOAD_FOLDER, 'decrypted.jpg')
    cv2.imwrite(decrypted_img_path, img_array)
    
    return decrypted_img_path, message

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/encrypt', methods=['POST'])
def encrypt():
    image = request.files['image']
    message = request.form['message']
    password = request.form['password']
    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    image.save(image_path)
    encrypted_path = encrypt_image(image_path, message, password)
    return send_file(encrypted_path, as_attachment=True, download_name='encrypted.bin')

@app.route('/decrypt', methods=['POST'])
def decrypt():
    encrypted_file = request.files['encrypted_image']
    password = request.form['password']
    encrypted_path = os.path.join(UPLOAD_FOLDER, encrypted_file.filename)
    encrypted_file.save(encrypted_path)
    decrypted_img_path, message = decrypt_image(encrypted_path, password)
    return render_template('result.html', message=message, image_path=decrypted_img_path)

if __name__ == '__main__':
    app.run(debug=True)