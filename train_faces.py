import os
import cv2
import numpy as np
import pickle
from deepface import DeepFace
from pathlib import Path
from tqdm import tqdm
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FaceTrainer:
    def __init__(self):
        self.known_encodings = []
        self.known_names = []
        self.model_name = "Facenet"  # Can use "VGG-Face", "OpenFace", "ArcFace"
        self.detector_backend = "opencv"  # Alternatives: "mtcnn", "retinaface"
        self.min_confidence = 0.8  # Minimum detection confidence

    def process_image(self, image_path):
        """Extract face embeddings from an image"""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError("Could not read image")

            # Get face embeddings
            results = DeepFace.represent(
                img_path=image_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=True
            )

            # Handle single/multiple faces
            if isinstance(results, dict):
                results = [results]
            
            embeddings = []
            for result in results:
                if result['face_confidence'] >= self.min_confidence:
                    embedding = np.array(result['embedding'], dtype=np.float32)
                    embeddings.append(embedding)
            
            return embeddings

        except Exception as e:
            logger.warning(f"Could not process {image_path}: {str(e)}")
            return None

    def train_from_folder(self, dataset_path):
        """Train from SD card folder structure"""
        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"Dataset path not found: {dataset_path}")

        logger.info(f"Starting training from: {dataset_path}")
        
        # Process each person's folder
        person_folders = [f for f in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, f))]
        
        for person_name in tqdm(person_folders, desc="Processing people"):
            person_path = os.path.join(dataset_path, person_name)
            image_files = [f for f in os.listdir(person_path) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            for image_file in tqdm(image_files, desc=f"Processing {person_name}", leave=False):
                image_path = os.path.join(person_path, image_file)
                embeddings = self.process_image(image_path)
                
                if embeddings:
                    for embedding in embeddings:
                        self.known_encodings.append(embedding)
                        self.known_names.append(person_name)

    def save_model(self, output_file="face_encodings.pkl"):
        """Save trained model to file"""
        if not self.known_encodings:
            raise ValueError("No face encodings to save")

        data = {
            "embeddings": self.known_encodings,
            "names": self.known_names,
            "model": self.model_name,
            "detector": self.detector_backend,
            "timestamp": str(np.datetime64('now'))
        }

        with open(output_file, "wb") as f:
            pickle.dump(data, f)

        logger.info(f"Saved trained model to {output_file}")
        logger.info(f"Total encodings: {len(self.known_encodings)}")
        logger.info(f"Unique people: {len(set(self.known_names))}")

def main():
    # SD card path (modify as needed)
    sd_card_path = "/media/sd_card"  # Linux/Mac
    # sd_card_path = "D:\\"  # Windows
    
    # Alternative: Use fixed path you mentioned
    fixed_path = r"c:\Users\HP\Desktop\datas\SD_CARD"
    
    # Initialize trainer
    trainer = FaceTrainer()
    
    try:
        # Try to train from SD card first
        if os.path.exists(sd_card_path):
            trainer.train_from_folder(sd_card_path)
        else:
            # Fall back to fixed path
            trainer.train_from_folder(fixed_path)
        
        # Save the trained model
        trainer.save_model("faces_trained.pkl")
        
    except Exception as e:
        logger.error(f"Training failed: {str(e)}")
        return

if __name__ == "__main__":
    main()