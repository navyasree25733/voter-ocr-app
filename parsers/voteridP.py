# import re

# def parse_single_voter_text(text):
#     data = {
#         "EPIC No": "Not Found",
#         "Name": "Not Found",
#         "Relation Name": "Not Found",
#         "Gender": "Not Found",
#         "DOB/Age": "Not Found"
#     }

#     # EPIC Number: usually 3 letters followed by 7 digits
#     epic_pattern = r'[A-Z]{3}\d{7}'
#     epic_match = re.search(epic_pattern, text)
#     if epic_match:
#         data["EPIC No"] = epic_match.group(0)

#     # Name Extraction (Look for "Name" or "Elector's Name")
#     name_match = re.search(r"(?:Name|Elector's Name)[:\s]+([A-Z\s]+)", text, re.I)
#     if name_match:
#         data["Name"] = name_match.group(1).strip().split('\n')[0]

#     # Relation Name (Father/Husband)
#     rel_match = re.search(r"(?:Father's|Husband's|Relation) Name[:\s]+([A-Z\s]+)", text, re.I)
#     if rel_match:
#         data["Relation Name"] = rel_match.group(1).strip().split('\n')[0]

#     return data

import re
from datetime import date, datetime

class VoterParser:
    STATES = [
        "ANDHRA PRADESH","TELANGANA","KARNATAKA","TAMIL NADU",
        "KERALA","MAHARASHTRA","DELHI","UTTAR PRADESH",
        "WEST BENGAL","ODISHA","GUJARAT","RAJASTHAN",
        "MADHYA PRADESH","BIHAR","ASSAM","PUNJAB",
        "HARYANA","JHARKHAND","CHHATTISGARH"
    ]

    def normalize_text_safe(self, text):
        text = text.replace("’", "'")
        text = text.replace("|", " ")
        text = re.sub(r"[^\x00-\x7F\n]+", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def extract_field(self, label_patterns, text, stop_words):
        label = "(?:" + "|".join(label_patterns) + ")"
        stop  = "(?:" + "|".join(stop_words) + ")"
        pattern = rf"{label}\s*[:.\-]?\s*(.*?)\s*(?={stop}|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if not match:
            return "Not Stated"
        value = match.group(1).replace("\n", " ")
        return re.sub(r"\s+", " ", value).strip() or "Not Stated"

    def clean_person_name(self, value):
        if value in ("", None, "Not Stated"):
            return "Not Stated"
        value = re.sub(r"\d+", "", value)
        value = re.sub(r"[><\"/\\|_=,:;]+", " ", value)
        value = re.sub(r"[^A-Za-z.\s]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        value = re.sub(r"\b[a-zA-Z]{1}\b$", "", value).strip()
        words = value.split()
        if len(words) > 5:
            value = " ".join(words[:4])
        return value if len(value) >= 2 else "Not Stated"

    def extract_address(self, text):
        stop_words = [
            r"Electoral Registration Officer", r"Issue Date", r"This card",
            r"Note", r"www", r"http", r"Date of Birth", r"Name", r"Father"
        ]
        stop = "|".join(stop_words)
        pattern = rf"Address\s*[:.\-]?\s*(.*?)(?=\n(?:{stop})|\Z)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if not match:
            return "Not Available on Voter ID"
        address = match.group(1).replace("\n", " ")
        address = re.sub(r"\s+", " ", address).strip()
        return address if len(address) > 10 else "Not Available on Voter ID"

    def calculate_age(self, dob):
        if dob in ("", None, "Not Stated"):
            return "Not Stated"
        for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
            try:
                d = datetime.strptime(dob, fmt).date()
                today = date.today()
                return today.year - d.year - ((today.month, today.day) < (d.month, d.day))
            except:
                continue
        return "Not Stated"

    def extract_gender(self, raw_text):
        t = raw_text.lower()
        if "पुरुष" in t: return "Male"
        if "महिला" in t or "स्त्री" in t: return "Female"
        m = re.search(r"\b(male|female|other)\b", t)
        return m.group(1).capitalize() if m else "Not Stated"

    def extract_pincode(self, text):
        m = re.search(r"\b[5-7]\d{5}\b", text)
        return m.group() if m else "Not Stated"

    def extract_state(self, text):
        text_upper = text.upper()
        for s in self.STATES:
            s_words = s.split()
            if all(re.search(r'\b' + word + r'\b', text_upper) for word in s_words):
                return s.title()
        return "Not Stated"

    def parse_all(self, ocr_text):
        """
        Main entry point that mimics your script logic
        """
        clean_text = self.normalize_text_safe(ocr_text)

        epic_match = re.search(r"\b[A-Z]{3}\d{7}\b", clean_text)
        epic = epic_match.group() if epic_match else "Not Stated"

        raw_name = self.extract_field(["Name"], clean_text, ["Father'?s Name", "Gender", "Date of Birth", "DOB", "Address", "Electoral"])
        name = self.clean_person_name(raw_name)

        raw_father = self.extract_field(["Father'?s Name"], clean_text, ["Name", "Gender", "Date of Birth", "DOB", "Address", "Electoral"])
        father = self.clean_person_name(raw_father)

        dob_match = re.search(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", clean_text)
        dob = dob_match.group() if dob_match else "Not Stated"

        return {
            "Name": name,
            "Father Name": father,
            "DOB": dob,
            "Age": self.calculate_age(dob),
            "EPIC NUMBER": epic,
            "Gender": self.extract_gender(ocr_text),
            "Address": self.extract_address(clean_text),
            "Pincode": self.extract_pincode(clean_text),
            "State": self.extract_state(clean_text)
        }