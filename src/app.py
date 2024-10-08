from flask import Flask, request, render_template, url_for
import pandas as pd
from pickle import load
from PIL import Image
import numpy as np
import joblib
import io
import os

app = Flask(__name__)

# Set up paths
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Load KMeans clustering model
kmeans_model = load(open("../models/kmodel.dat", "rb"))

# Directory where models are stored
model_directory = '../models/'

# Initialize a dictionary to store the models
model_dict = {}

# Loop through the model indices
for i in range(4):
    model_path = f'{model_directory}{i}Model95acc.joblib'
    try:
        model = joblib.load(model_path)
        model_dict[i] = model
        print(f"Model {i} loaded successfully.")
    except Exception as e:
        print(f"Error loading model {i}: {e}")

# Print out the keys of loaded models
print("Loaded models:", model_dict.keys())


# Dictionary to map class indices to class names and descriptions
class_dict = {
    0: {'name': 'Adipose', 'description': 'Adipose tissue, commonly known as body fat, is a connective tissue that stores energy in the form of fat.'},
    1: {'name': 'Background', 'description': 'Background refers to the non-specific or irrelevant areas in the image that do not correspond to any class of interest.'},
    2: {'name': 'Debris', 'description': 'Debris includes small fragments or remnants that are often considered as waste material in the histology slide.'},
    3: {'name': 'Lymphocytes', 'description': 'Lymphocytes are a type of white blood cell crucial for the immune system, involved in the body’s defense against pathogens.'},
    4: {'name': 'Mucus', 'description': 'Mucus is a viscous fluid secreted by mucous membranes that serves to protect and lubricate tissues.'},
    5: {'name': 'Smooth Muscle', 'description': 'Smooth muscle tissue is a type of involuntary muscle found in various organs and structures, responsible for involuntary movements.'},
    6: {'name': 'Normal Colon Mucosa', 'description': 'Normal colon mucosa refers to the healthy lining of the colon, which is important for proper digestive function.'},
    7: {'name': 'Cancer-Associated Stroma', 'description': 'Cancer-associated stroma is the supportive tissue surrounding cancer cells that can influence tumor growth and progression.'},
    8: {'name': 'Colorectal Adenocarcinoma Epithelium', 'description': 'Colorectal adenocarcinoma epithelium refers to the cancerous epithelial cells found in colorectal cancer.'}
}

# Function to preprocess the image
def preprocess_image(image):
    image = image.resize((28, 28))
    image_array = np.array(image) / 255.0  # Normalize pixel values to [0, 1]
    return image_array

# Function to extract RGB statistics from an image
def extract_rgb_statistics(image):
    img = np.array(image)
    red, green, blue = img[:, :, 0].flatten().tolist(), img[:, :, 1].flatten().tolist(), img[:, :,
                                                                                            2].flatten().tolist()
    colors = {'red': red, 'green': green, 'blue': blue}
    funcs = {'_avg': np.mean, '_std': np.std, '_max': np.max, '_min': np.min}
    results = {}
    for _name, func in funcs.items():
        for name, color in colors.items():
            results[name + _name] = func(color)
    return results

@app.route("/", methods=["GET", "POST"])
def index():
    class_prediction = None
    description = None
    rgb_features = None
    text_rgb = None
    alt_rgb_1 = None
    image_url = None
    error_message = None

    if request.method == "POST":
        try:
            image_file = request.files.get('fileInput')

            if image_file:
                # Save the uploaded image
                image_path = os.path.join(UPLOAD_FOLDER, 'uploaded_image.jpg')
                image = Image.open(io.BytesIO(image_file.read())).convert('RGB')
                image.save(image_path)
                image_url = url_for('static', filename=f'uploads/uploaded_image.jpg')

                # Preprocess and predict
                image_array = preprocess_image(image)
                image_array = image_array.reshape(1, 28, 28, 3)
                rgb_features = extract_rgb_statistics(image)
                cluster_label = kmeans_model.predict(pd.DataFrame(rgb_features, index=[0]))[0]
                text_rgb = [rgb_features[f'{i}_avg'] - (rgb_features[f'{i}_std'] * 2) if (rgb_features[f'{i}_avg'] - (rgb_features[f'{i}_std'] * 2)) >= 0 else 0 for i in ['red', 'green', 'blue']]
                alt_rgb_1 = [rgb_features[f'{i}_avg'] + (rgb_features[f'{i}_std'] * 2) if (rgb_features[f'{i}_avg'] + (rgb_features[f'{i}_std'] * 2)) <= 255 else 255 for i in ['red', 'green', 'blue']]
                rgb_features = [v for k, v in rgb_features.items() if '_avg' in k]
                model = model_dict.get(cluster_label)
                if model is None:
                    class_prediction = "Model not found for the predicted cluster."
                else:
                    class_probs = model.predict(image_array)
                    predicted_class_index = np.argmax(class_probs)
                    class_info = class_dict.get(predicted_class_index, {'name': 'Unknown', 'description': 'No description available'})
                    class_prediction = class_info['name']
                    description = class_info['description']
                    print(f"Class Probabilities: {class_probs}")
                    print(f"Predicted Class Index: {predicted_class_index}")
                    print(f"Class Prediction: {class_prediction}")

        except Exception as e:
            error_message = str(e)
            print(f"Error: {error_message}")

    return render_template("index.html", prediction=class_prediction, description=description, error=error_message, rgb_features=rgb_features, text_rgb = text_rgb, alt_rgb_1=alt_rgb_1, image=image_url)

if __name__ == "__main__":
    app.run(debug=True)
