from ultralytics import YOLO
import numpy as np
import cv2
from typing import List, Dict, Tuple
from config import Config
import os

class LayoutDetector:
    def __init__(self):
        self.model = None
        self.model_path = Config.YOLO_MODEL_PATH
        self.device = Config.DEVICE
        self.load_model()
        
        # DocLayout-YOLO class names based on the repository
        self.class_names = {
            0: 'Caption',
            1: 'Footnote', 
            2: 'Formula',
            3: 'List-item',
            4: 'Page-footer',
            5: 'Page-header',
            6: 'Picture',
            7: 'Section-header',
            8: 'Table',
            9: 'Text',
            10: 'Title'
        }
    
    def load_model(self):
        """Load YOLO-DocLayout model"""
        try:
            if os.path.exists(self.model_path):
                self.model = YOLO(self.model_path)
            else:
                # Download pre-trained model if not exists
                self.model = YOLO('yolov8n.pt')  # Fallback to base model
                print(f"Warning: YOLO-DocLayout model not found at {self.model_path}")
                print("Using base YOLOv8 model. Please download DocLayout-YOLO model.")
                
        except Exception as e:
            raise Exception(f"Error loading YOLO model: {str(e)}")
    
    def detect_layout(self, image: np.ndarray) -> List[Dict]:
        """
        Detect layout elements in image
        Returns list of detected elements with bounding boxes and labels
        """
        try:
            if self.model is None:
                raise Exception("Model not loaded")
            
            # Run inference
            results = self.model(image, device=self.device)
            
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for i in range(len(boxes)):
                        # Get bounding box coordinates (xyxy format)
                        x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy()
                        confidence = boxes.conf[i].cpu().numpy()
                        class_id = int(boxes.cls[i].cpu().numpy())
                        
                        # Convert to our format
                        detection = {
                            'bbox': {
                                'x': int(x1),
                                'y': int(y1),
                                'width': int(x2 - x1),
                                'height': int(y2 - y1)
                            },
                            'confidence': float(confidence),
                            'class_id': class_id,
                            'class_name': self.class_names.get(class_id, f'Unknown_{class_id}'),
                            'type': self.class_names.get(class_id, f'Unknown_{class_id}')
                        }
                        
                        detections.append(detection)
            
            return detections
            
        except Exception as e:
            raise Exception(f"Error in layout detection: {str(e)}")
    
    def filter_figure_elements(self, detections: List[Dict]) -> List[Dict]:
        """Filter detections to get figure-related elements"""
        figure_types = ['Picture', 'Formula', 'Table', 'Caption']
        return [det for det in detections if det['class_name'] in figure_types]
    
    def get_text_blocks(self, detections: List[Dict]) -> List[Dict]:
        """Filter detections to get text blocks"""
        text_types = ['Text', 'Caption', 'Title', 'Section-header']
        return [det for det in detections if det['class_name'] in text_types]