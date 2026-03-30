import os
from flask import Flask, send_file, send_from_directory

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.route('/')
def index():
    return send_file(os.path.join(BASE_DIR, 'main.html'))


@app.route('/src/products/<path:filename>')
def product_images(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'src', 'products'), filename)


@app.route('/<path:filename>')
def static_files(filename):
    return send_file(os.path.join(BASE_DIR, filename))


# -----------------------------
# Run App
# -----------------------------
# if __name__ == '__main__':
#     app.run(debug=True, port=5000)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)