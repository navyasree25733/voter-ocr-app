import cv2
import pytesseract
import numpy as np
from pdf2image import convert_from_path
from pdf2image import convert_from_bytes

def extract_voter_boxes(page_img):
    img = cv2.cvtColor(np.array(page_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 4)
    
    horizontal = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1)), iterations=2)
    vertical = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40)), iterations=2)
    
    grid = cv2.add(horizontal, vertical)
    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if 350 < w < 900 and 180 < h < 350:
            boxes.append((x, y, w, h))
    
    return sorted(boxes, key=lambda b: (b[1], b[0])), img

def split_voter_box(img, x, y, w, h):
    left_width = int(w * 0.72)
    return img[y:y+h, x:x+left_width], img[y:y+h, x+left_width:x+w]

def get_ocr_text(img_crop, config="--oem 3 --psm 6"):
    return pytesseract.image_to_string(img_crop, config=config, lang="eng")
