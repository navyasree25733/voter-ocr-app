# import PIL.Image
# from pdf2image import convert_from_path
# from ocr.voter_ocr import get_ocr_text # Reuse your existing OCR function
# from parsers.voteridP import parse_single_voter_text

# def process_single_voter_card(file_path):
#     # Convert input to images
#     if file_path.lower().endswith(".pdf"):
#         images = convert_from_path(file_path, dpi=300)
#     else:
#         images = [PIL.Image.open(file_path)]
    
#     combined_text = ""
#     for img in images:
#         combined_text += " " + get_ocr_text(img)
    
#     # Send all text to the specialized parser
#     data = parse_single_voter_text(combined_text)
#     return [data] # Return as list for DataFrame compatibility

import cv2
import pytesseract
import numpy as np


class OCRProcessor:
    def __init__(self, lang='eng+hin'):
        self.config = r'--oem 3 --psm 11'
        self.lang = lang

    def preprocess_voter(self, img):
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Resize for better OCR
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        # Light denoising
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        return gray

    def get_text(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return ""
        processed = self.preprocess_voter(img)
        text = pytesseract.image_to_string(processed, config=self.config, lang=self.lang)
        return text