import cv2
import numpy as np
import pickle
from deepface import DeepFace
from sklearn.metrics.pairwise import cosine_similarity

# Load trained model
with open('faces_trained.pkl', 'rb') as f:
    data = pickle.load(f)

known_encodings = data['embeddings']
known_names = data['names']
model_name = data.get('model', 'Facenet')  # Default to Facenet if not specified

# Recognition settings
SIMILARITY_THRESHOLD = 0.65  # Adjust this based on your needs (higher = more strict)
DETECTOR_BACKEND = 'opencv'  # Options: 'opencv', 'ssd', 'dlib', 'mtcnn', 'retinaface'
SHOW_CONFIDENCE = True  # Display confidence score

# Initialize webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open camera")
    exit()

# Create window with adjustable size
cv2.namedWindow('Face Recognition', cv2.WINDOW_NORMAL)

def recognize_face(face_img):
    """Recognize a single face image"""
    try:
        # Get embedding for the current face
        result = DeepFace.represent(
            img_path=face_img,
            model_name=model_name,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=False
        )
        
        if not result:
            return None, 0
        
        current_embedding = np.array(result[0]['embedding'], dtype=np.float32)
        
        # Compare with known faces
        best_match = "Unknown"
        best_score = 0
        
        for known_embedding, name in zip(known_encodings, known_names):
            similarity = cosine_similarity(
                [current_embedding],
                [known_embedding]
            )[0][0]
            
            if similarity > best_score:
                best_score = similarity
                best_match = name
        
        return best_match, best_score
    
    except Exception as e:
        print(f"Recognition error: {e}")
        return None, 0

# Main recognition loop
while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Couldn't read frame")
        break
    
    try:
        # Detect faces in the frame (without mirroring)
        detections = DeepFace.extract_faces(
            img_path=frame,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=False
        )
        
        for detection in detections:
            if not detection.get('facial_area'):
                continue
                
            # Extract face location
            x = detection['facial_area']['x']
            y = detection['facial_area']['y']
            w = detection['facial_area']['w']
            h = detection['facial_area']['h']
            
            # Get face ROI
            face_roi = frame[y:y+h, x:x+w]
            
            # Recognize face
            name, confidence = recognize_face(face_roi)
            
            # Draw results
            if name and confidence > SIMILARITY_THRESHOLD:
                color = (0, 255, 0)  # Green for recognized
                label = f"{name} ({confidence:.2f})" if SHOW_CONFIDENCE else name
            else:
                color = (0, 0, 255)  # Red for unknown
                label = "Unknown"
            
            # Draw rectangle and label
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, label, (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    except Exception as e:
        print(f"Detection error: {e}")
        continue
    
    # Display frame (without mirroring)
    cv2.imshow('Face Recognition', frame)
    
    # Exit on 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()