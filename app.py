from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from werkzeug.utils import secure_filename
import tensorflow as tf
import librosa
import numpy as np
from skimage.transform import resize
import logging
from logging.handlers import RotatingFileHandler
from gevent.pywsgi import WSGIServer

# Initialize Flask app
app = Flask(__name__, static_url_path='', static_folder='.')
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Configure logging
if not os.path.exists('logs'):
    os.makedirs('logs')
    
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Application startup')

# Add rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Configurations
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config.update(
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
)

# Load model with error handling and caching
model = None
classes = ['blues', 'classical', 'country', 'disco', 'hiphop', 'jazz', 'metal', 'pop', 'reggae', 'rock']

def load_model():
    global model
    try:
        if model is None:
            model = tf.keras.models.load_model("MGC.keras", compile=False)
            model.compile(optimizer='adam',
                        loss='categorical_crossentropy',
                        metrics=['accuracy'])
        return model
    except Exception as e:
        app.logger.error(f"Error loading model: {e}")
        raise

# Routes
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_and_preprocess_data(file_path, target_shape=(150, 150)):
    try:
        data = []
        audio_data, sample_rate = librosa.load(file_path, sr=None)
        
        if len(audio_data) == 0:
            raise ValueError("Audio file is empty or could not be read")
        
        min_samples = 4 * sample_rate  
        if len(audio_data) < min_samples:
            audio_data = np.pad(audio_data, (0, min_samples - len(audio_data)))
        
        chunk_duration = 4
        overlap_duration = 2
        
        chunk_samples = chunk_duration * sample_rate
        overlap_samples = overlap_duration * sample_rate
        
        num_chunks = int(np.ceil((len(audio_data) - chunk_samples) / (chunk_samples - overlap_samples))) + 1
        
        for i in range(num_chunks):
            start = i * (chunk_samples - overlap_samples)
            end = start + chunk_samples
            
            if end > len(audio_data):
                chunk = np.pad(audio_data[start:], (0, end - len(audio_data)))
            else:
                chunk = audio_data[start:end]
            
            mel_spectrogram = librosa.feature.melspectrogram(y=chunk, sr=sample_rate)
            mel_spectrogram = resize(np.expand_dims(mel_spectrogram, axis=-1), target_shape)
            data.append(mel_spectrogram)
        
        return np.array(data)
    except Exception as e:
        app.logger.error(f"Error processing audio: {str(e)}")
        raise Exception(f"Error processing audio: {str(e)}")

def get_feel_factor(predictions):
    # Get top 3 genres and their percentages
    sorted_genres = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
    top_genres = sorted_genres[:3]
    
    # Create base descriptors for each genre
    genre_descriptors = {
        'blues': {
            'adjectives': ['soulful', 'raw', 'emotional', 'melancholic', 'passionate'],
            'nouns': ['heartache', 'soul', 'feeling', 'spirit', 'depth'],
            'verbs': ['flows', 'resonates', 'pulses', 'breathes', 'moves']
        },
        'classical': {
            'adjectives': ['elegant', 'sophisticated', 'orchestral', 'refined', 'majestic'],
            'nouns': ['composition', 'harmony', 'arrangement', 'symphony', 'opus'],
            'verbs': ['soars', 'flows', 'builds', 'unfolds', 'swells']
        },
        'country': {
            'adjectives': ['rustic', 'heartfelt', 'authentic', 'pastoral', 'folksy'],
            'nouns': ['story', 'roots', 'heart', 'tradition', 'earth'],
            'verbs': ['tells', 'flows', 'rides', 'speaks', 'moves']
        },
        'disco': {
            'adjectives': ['groovy', 'energetic', 'vibrant', 'dynamic', 'rhythmic'],
            'nouns': ['rhythm', 'beat', 'pulse', 'movement', 'energy'],
            'verbs': ['moves', 'pulses', 'drives', 'grooves', 'flows']
        },
        'hiphop': {
            'adjectives': ['urban', 'rhythmic', 'bold', 'expressive', 'street'],
            'nouns': ['flow', 'rhythm', 'beat', 'groove', 'pulse'],
            'verbs': ['flows', 'moves', 'rides', 'speaks', 'pulses']
        },
        'jazz': {
            'adjectives': ['improvisational', 'smooth', 'sophisticated', 'fluid', 'expressive'],
            'nouns': ['harmony', 'rhythm', 'soul', 'groove', 'spirit'],
            'verbs': ['flows', 'swings', 'moves', 'breathes', 'plays']
        },
        'metal': {
            'adjectives': ['intense', 'powerful', 'aggressive', 'fierce', 'heavy'],
            'nouns': ['power', 'intensity', 'energy', 'force', 'strength'],
            'verbs': ['drives', 'crushes', 'pounds', 'surges', 'roars']
        },
        'pop': {
            'adjectives': ['catchy', 'melodic', 'polished', 'vibrant', 'fresh'],
            'nouns': ['melody', 'hook', 'rhythm', 'energy', 'vibe'],
            'verbs': ['moves', 'flows', 'pulses', 'shines', 'grooves']
        },
        'reggae': {
            'adjectives': ['laid-back', 'mellow', 'groovy', 'rhythmic', 'tropical'],
            'nouns': ['groove', 'vibe', 'rhythm', 'pulse', 'spirit'],
            'verbs': ['flows', 'moves', 'rides', 'pulses', 'sways']
        },
        'rock': {
            'adjectives': ['energetic', 'powerful', 'dynamic', 'bold', 'electric'],
            'nouns': ['energy', 'power', 'drive', 'force', 'spirit'],
            'verbs': ['drives', 'rocks', 'moves', 'pulses', 'surges']
        }
    }

    import random

    def generate_phrase(genres_with_weights):
        # Select descriptors based on the top genres and their weights
        selected_words = []
        total_weight = sum(weight for _, weight in genres_with_weights)
        
        # Get words from top 2 genres
        for genre, weight in genres_with_weights[:2]:
            descriptors = genre_descriptors[genre]
            selected_words.extend([
                random.choice(descriptors['adjectives']),
                random.choice(descriptors['nouns']),
                random.choice(descriptors['verbs'])
            ])
        
        # Ensure we have enough words
        while len(selected_words) < 6:
            first_genre = genres_with_weights[0][0]
            descriptors = genre_descriptors[first_genre]
            selected_words.extend([
                random.choice(descriptors['adjectives']),
                random.choice(descriptors['nouns']),
                random.choice(descriptors['verbs'])
            ])
        
        # More refined and coherent phrase templates
        phrases = [
            f"A {selected_words[0]} melody {selected_words[2]} through layers of {selected_words[3]} harmony.",
            f"Waves of {selected_words[0]} {selected_words[1]} cascade into {selected_words[3]} rhythms.",
            f"The {selected_words[0]} spirit {selected_words[2]}, painting a canvas of {selected_words[3]} sound.",
            f"{selected_words[0].capitalize()} textures blend with {selected_words[3]} movements, creating pure {selected_words[1]}.",
            f"In this piece, {selected_words[0]} elements {selected_words[2]} beneath {selected_words[3]} undertones.",
            f"A journey where {selected_words[0]} {selected_words[1]} meets {selected_words[3]} expression.",
            f"Delicate {selected_words[0]} passages interweave with {selected_words[3]} moments of {selected_words[1]}."
        ]
        
        return random.choice(phrases)

    # Generate the artistic description
    description = generate_phrase(top_genres)
    
    # Add a mood indicator based on the dominant genres
    mood_phrases = {
        ('metal', 'rock'): "Intensity peaks and valleys paint the sonic landscape",
        ('jazz', 'blues'): "Smooth sophistication meets raw emotion",
        ('classical', 'jazz'): "Refined elegance dances with improvised spirit",
        ('hiphop', 'reggae'): "Urban rhythms float on island vibes",
        # Add more mood combinations as needed
    }
    
    # Get the mood phrase if it exists for the top two genres
    mood = mood_phrases.get((top_genres[0][0], top_genres[1][0]), "")
    
    return f"{description}\n{mood}" if mood else description

def analyze_music(file_path):
    try:
        X_test = load_and_preprocess_data(file_path)
        current_model = load_model()
        
        y_pred = current_model.predict(X_test)
        average_predictions = np.mean(y_pred, axis=0)
        percentages = average_predictions * 100
        
        genre_percentages = {classes[i]: float(percentages[i]) for i in range(len(classes))}
        sorted_predictions = dict(sorted(genre_percentages.items(), 
                                       key=lambda x: x[1], 
                                       reverse=True))
        
        return {
            "predictions": sorted_predictions,
            "artisticDescription": get_feel_factor(sorted_predictions),
            "topGenre": list(sorted_predictions.keys())[0],
            "topConfidence": float(list(sorted_predictions.values())[0])
        }
    except Exception as e:
        app.logger.error(f"Error in analyze_music: {str(e)}")
        raise

@app.route('/analyze', methods=['POST'])
@limiter.limit("1 per second")
def analyze():
    app.logger.info("Received analyze request")
    
    try:
        if 'file' not in request.files:
            app.logger.warning("No file in request")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            app.logger.warning("No filename provided")
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                app.logger.info(f"Saving file: {filename}")
                file.save(filepath)
                app.logger.info(f"File saved successfully at: {filepath}")
                
                app.logger.info("Starting music analysis")
                results = analyze_music(filepath)
                app.logger.info(f"Analysis complete: {results}")
                
                # Clean up
                if os.path.exists(filepath):
                    os.remove(filepath)
                    app.logger.info("Temporary file removed")
                
                return jsonify(results)
            except Exception as e:
                app.logger.error(f"Error processing request: {str(e)}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({'error': str(e)}), 500
        
        app.logger.warning("Invalid file type")
        return jsonify({'error': 'Invalid file type'}), 400
    
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 50MB'}), 413

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error. Please try again later.'}), 500

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    # Development
    if app.debug:
        app.run(debug=True)
    # Production
    else:
        http_server = WSGIServer(('0.0.0.0', 8000), app)
        app.logger.info('Starting production server on http://0.0.0.0:8000')
        http_server.serve_forever()

MODEL_PATH = "MGC.keras"
if not os.path.exists(MODEL_PATH):
    app.logger.error(f"Model file not found at: {MODEL_PATH}")