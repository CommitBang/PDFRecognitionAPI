import numpy as np
import cv2
from typing import List, Dict, Tuple
from config import Config
import os

try:
    from doclayout_yolo import YOLOv10
    DOCLAYOUT_AVAILABLE = True
    print("doclayout-yolo package loaded successfully")
except ImportError as e:
    print(f"doclayout-yolo not available: {e}")
    DOCLAYOUT_AVAILABLE = False
    YOLOv10 = None
except Exception as e:
    print(f"Error loading doclayout-yolo (likely version compatibility issue): {e}")
    print("Falling back to ultralytics YOLO")
    DOCLAYOUT_AVAILABLE = False
    YOLOv10 = None

from ultralytics import YOLO

class LayoutDetector:
    def __init__(self):
        self.model = None
        self.model_path = Config.YOLO_MODEL_PATH
        self.device = Config.DEVICE
        self.using_doclayout = False
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
        """Load YOLO-DocLayout model with fallback handling"""
        model_loaded = False
        
        # Only try DocLayout if the package is available
        if DOCLAYOUT_AVAILABLE:
            # Try using pre-trained DocLayout model from Hugging Face (recommended)
            try:
                print("Loading pre-trained DocLayout-YOLO model from Hugging Face...")
                self.model = YOLOv10.from_pretrained("juliozhao/DocLayout-YOLO-DocStructBench")
                model_loaded = True
                print("DocLayout YOLO model loaded successfully from Hugging Face")
                self.using_doclayout = True
                return
            except Exception as e:
                print(f"Error loading DocLayout model from Hugging Face: {e}")
                print("Trying local model file...")
            
            # Try using local doclayout-yolo package with local model file
            if os.path.exists(self.model_path):
                try:
                    print(f"Loading DocLayout model using doclayout-yolo package from {self.model_path}")
                    self.model = YOLOv10(self.model_path)
                    model_loaded = True
                    print("DocLayout YOLO model loaded successfully using doclayout-yolo package")
                    self.using_doclayout = True
                    return
                except Exception as e:
                    print(f"Error loading DocLayout model with doclayout-yolo package: {e}")
                    print("Falling back to ultralytics YOLO...")
        else:
            print("doclayout-yolo package not available, using ultralytics YOLO")
        
        # Try ultralytics YOLO if doclayout-yolo failed or not available
        if os.path.exists(self.model_path):
            try:
                print(f"Loading YOLO-DocLayout model using ultralytics from {self.model_path}")
                self.model = YOLO(self.model_path)
                model_loaded = True
                print("YOLO-DocLayout model loaded successfully using ultralytics")
                self.using_doclayout = False
                return
            except Exception as e:
                print(f"Error loading DocLayout model with ultralytics: {e}")
                print("This usually indicates a PyTorch version compatibility issue")
        
        # Try alternative models if DocLayout failed
        print("Trying standard YOLO models as fallback...")
        alternative_models = [
            ('yolov8n.pt', 'YOLOv8 Nano'),
            ('yolov8s.pt', 'YOLOv8 Small'),
            ('yolov8m.pt', 'YOLOv8 Medium')
        ]
        
        for model_name, description in alternative_models:
            try:
                print(f"Trying {description} model...")
                self.model = YOLO(model_name)  # Will auto-download if needed
                
                print(f"{description} model loaded successfully")
                print("Note: Using general object detection instead of document layout detection")
                model_loaded = True
                self.using_doclayout = False
                break
                
            except Exception as e:
                print(f"Error loading {description}: {e}")
                continue
        
        if not model_loaded:
            raise Exception("Could not load any YOLO model. Please check PyTorch installation and compatibility.")
    
    def detect_layout(self, image: np.ndarray) -> List[Dict]:
        """
        Detect layout elements in image
        Returns list of detected elements with bounding boxes and labels
        """
        try:
            if self.model is None:
                raise Exception("Model not loaded")
            
            # Ensure image is in correct format
            if len(image.shape) == 3 and image.shape[2] == 4:  # RGBA
                image = image[:, :, :3]  # Convert to RGB
            
            # Run inference based on model type
            try:
                if self.using_doclayout:
                    # Use DocLayout-YOLO specific parameters
                    results = self.model.predict(
                        image,
                        imgsz=1024,  # Recommended image size for DocLayout
                        conf=0.2,    # Recommended confidence threshold
                        device=self.device
                    )
                else:
                    # Use standard YOLO parameters
                    results = self.model(image, device=self.device, verbose=False)
                    
            except AttributeError as e:
                if "'Conv' object has no attribute 'bn'" in str(e):
                    raise Exception("PyTorch/YOLO version compatibility issue. Try: pip install doclayout-yolo==0.0.4")
                else:
                    raise Exception(f"Model inference error: {str(e)}")
            
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None and len(boxes) > 0:
                    for i in range(len(boxes)):
                        try:
                            # Get bounding box coordinates (xyxy format)
                            x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy()
                            confidence = boxes.conf[i].cpu().numpy()
                            class_id = int(boxes.cls[i].cpu().numpy())
                            
                            # Validate coordinates
                            if x2 <= x1 or y2 <= y1:
                                continue
                            
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
                                'class_name': self.class_names.get(class_id, f'Object_{class_id}'),
                                'type': self.class_names.get(class_id, f'Object_{class_id}')
                            }
                            
                            detections.append(detection)
                        except Exception as box_error:
                            print(f"Error processing detection {i}: {box_error}")
                            continue
            
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