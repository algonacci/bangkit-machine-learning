import os
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
import numpy as np
from PIL import Image
import sys
import tensorflow_hub as hub
from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as viz_utils
sys.path.append("..")

app = Flask(__name__)

app.config['ALLOWED_EXTENSIONS'] = set(['png', 'jpg', 'jpeg'])
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['DOWNLOAD_FOLDER'] = 'downloads/'

LABEL_FILENAME = 'labels/label_map.pbtxt'
category_index = label_map_util.create_category_index_from_labelmap(LABEL_FILENAME, use_display_name=True)

print('------ Loading model ------')
model = 'model/'
hub_model = hub.load(model)
print('------ Model Loaded ------')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

def load_image_into_numpy_array(image):
  (image_width, image_height) = image.size
  return np.array(image.getdata()).reshape((1, image_height, image_width, 3)).astype(np.uint8)

@app.route('/')
def index():
    hello_json = {
        'status_code': 200,
        'message': 'Success testing the API!',
        'data': [],
    }
    return jsonify(hello_json)

@app.route('/post', methods=['POST'])
def post():
    data = request.get_json()
    return jsonify(data)

@app.route('/predict', methods=['POST'])
def predict():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_path = Image.open(file)
        image_path = image_path.convert('RGB')
        image_np = load_image_into_numpy_array(image_path)
        flip_image_horizontally = False 
        convert_image_to_grayscale = False
        if(flip_image_horizontally):
            image_np[0] = np.fliplr(image_np[0]).copy()
        if(convert_image_to_grayscale):
            image_np[0] = np.tile(
            np.mean(image_np[0], 2, keepdims=True), (1, 1, 3)).astype(np.uint8)
        results = hub_model(image_np)
        result = {key:value.numpy() for key,value in results.items()}
        label_id_offset = 0
        image_np_with_detections = load_image_into_numpy_array(image_path)
        viz_utils.visualize_boxes_and_labels_on_image_array(
            image_np_with_detections[0],
            result['detection_boxes'][0],
            (result['detection_classes'][0] + label_id_offset).astype(int),
            result['detection_scores'][0],
            category_index,
            use_normalized_coordinates=True,
            max_boxes_to_draw=200,
            min_score_thresh=.30,
            agnostic_mode=False
        )
        predicted_image = Image.fromarray(image_np_with_detections.squeeze())
        predicted_image.save('downloads/'+filename)
        label = viz_utils.visualize_boxes_and_labels_on_image_array.class_name
        json = {
            "label": label,
            "image_url": 'http://127.0.0.1:5000/downloads/'+filename
        }
        return jsonify(json)

@app.route('/downloads/<name>')
def download_file(name):
    return send_from_directory(app.config["DOWNLOAD_FOLDER"], name)

@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Endpoint not found', 'status_code': 404})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')