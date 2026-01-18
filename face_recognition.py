import cv2
import numpy as np
from deepface import DeepFace
import requests
import os
import pickle
import time
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class FaceLock:
    def __init__(self):
        self.running = False
        self.current_frame = None
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Load trained faces
        try:
            with open('faces_trained.pkl', 'rb') as f:
                data = pickle.load(f)
                self.known_encodings = data['embeddings']
                self.known_names = data['names']
                self.model_name = data.get('model', 'Facenet')
                logger.info(f"Loaded {len(self.known_names)} trained faces")
        except Exception as e:
            logger.error(f"Failed to load trained faces: {str(e)}")
            self.known_encodings = []
            self.known_names = []
            self.model_name = 'Facenet'

    def match_face(self, face_img):
        """Match detected face with trained data"""
        try:
            # Get embedding for detected face
            embedding = DeepFace.represent(
                img_path=face_img,
                model_name=self.model_name,
                detector_backend='opencv',
                enforce_detection=True,
                align=True
            )

            if not embedding:
                return None, 0.0

            # Convert to numpy array for comparison
            current_embedding = np.array(embedding[0]['embedding'])
            
            # Calculate similarities with known faces
            similarities = cosine_similarity(
                current_embedding.reshape(1, -1),
                self.known_encodings
            )[0]

            # Find best match
            best_match_idx = np.argmax(similarities)
            confidence = similarities[best_match_idx]

            # Only return match if confidence is high enough
            if confidence >= 0.8:  # 80% confidence threshold
                return self.known_names[best_match_idx], confidence
            
            return None, confidence

        except Exception as e:
            logger.error(f"Face matching error: {str(e)}")
            return None, 0.0

    def run(self):
        """Main face recognition loop"""
        self.running = True
        cap = cv2.VideoCapture(0)
        last_recognition_time = 0
        recognition_cooldown = 2.0  # Seconds between recognition attempts

        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue

            self.current_frame = frame.copy()
            current_time = time.time()

            # Only attempt recognition after cooldown
            if current_time - last_recognition_time >= recognition_cooldown:
                try:
                    # Detect faces
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

                    for (x, y, w, h) in faces:
                        # Extract and preprocess face
                        face_img = frame[y:y+h, x:x+w]
                        name, confidence = self.match_face(face_img)

                        if name:
                            # Draw green box for recognized face
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            text = f"{name} ({confidence:.2%})"
                            cv2.putText(frame, text, (x, y-10),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                            # Trigger door control
                            self.handle_recognition(name, confidence)
                            last_recognition_time = current_time
                        else:
                            # Draw red box for unknown face
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                            cv2.putText(frame, "Unknown", (x, y-10),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                except Exception as e:
                    logger.error(f"Recognition error: {str(e)}")

            self.current_frame = frame

        cap.release()

    def handle_recognition(self, name, confidence):
        """Handle successful face recognition"""
        try:
            # Log recognition
            logger.info(f"Recognized {name} with {confidence:.2%} confidence")

            # Send recognition event to server
            response = requests.post(
                'http://localhost:5000/face_recognized',
                json={
                    'name': name,
                    'confidence': float(confidence),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            )

            if response.status_code == 200:
                logger.info("Recognition event processed successfully")
            else:
                logger.error(f"Recognition event processing failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Recognition handling error: {str(e)}")

    def stop(self):
        self.running = False