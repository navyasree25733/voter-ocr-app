# import re

# def normalize_text(text):
#     text = text.upper()
#     text = text.replace("¢", "C").replace("|", "I").replace("!", "I")
#     text = re.sub(r"[;=+?]", ":", text)
#     return re.sub(r"\s+", " ", text).strip()

# def extract_epic(text):
#     if not text: return "Not Stated"
#     t = re.sub(r"[^A-Z0-9]", "", text.upper().replace("¢", "0"))
#     m = re.search(r"([A-Z]{3,4})(\d{6,8})", t)
#     return m.group(1)[:3] + m.group(2)[:7] if m else "Not Stated"

# def extract_between(text, start_patterns, stop_patterns):
#     start = r"(?:%s)\s*:?\s*" % "|".join(start_patterns)
#     stop = r"(?=%s)" % "|".join(stop_patterns)
#     m = re.search(start + r"(.*?)" + stop, text)
#     return m.group(1).strip() if m else "Not Stated"

# def parse_voter_text(text):
#     text = normalize_text(text)
#     return {
#         "Name": extract_between(text, ["NAME"], ["FATHERS", "HUSBANDS", "HOUSE", "AGE"]),
#         "Father/Husband": extract_between(text, ["FATHERS NAME", "HUSBANDS NAME"], ["HOUSE", "AGE"]),
#         "Age": (re.search(r"AGE\s*:?\s*(\d+)", text) or re.S).group(1) if re.search(r"AGE\s*:?\s*(\d+)", text) else "Not Stated",
#         "Gender": "Male" if "MALE" in text else "Female" if "FEMALE" in text else "Not Stated"
#     }

# import re

# def normalize_text(text):
#     text = text.upper()
#     text = text.replace("¢", "C").replace("|", "I").replace("!", "I")
#     text = re.sub(r"[;=+?]", ":", text)
#     text = re.sub(r"\bPHOTO\b|\bAVAILABLE\b", " ", text)
#     return re.sub(r"\s+", " ", text).strip()

# def extract_epic(text):
#     if not text: return "Not Stated"
#     # Replace common OCR errors in EPIC numbers
#     t = text.upper().replace("¢", "0")
#     t = re.sub(r"[^A-Z0-9]", "", t)
#     # Find EPIC-like sequence (3-4 letters + 7-8 digits)
#     m = re.search(r"([A-Z]{3,4})(\d{6,8})", t)
#     return m.group(1)[:3] + m.group(2)[:7] if m else "Not Stated"

# def extract_between(text, start_patterns, stop_patterns):
#     start = r"(?:%s)\s*:?\s*" % "|".join(start_patterns)
#     stop = r"(?=%s)" % "|".join(stop_patterns)
#     m = re.search(start + r"(.*?)" + stop, text)
#     return m.group(1).strip() if m else "Not Stated"

# def extract_house_no(text):
#     """Specific logic to pull House No while avoiding junk OCR noise."""
#     patterns = [
#         r"HOUSE\s*NO\.?\s*[:\-]?\s*(.+)",
#         r"HOUSE\s*NUMBER\s*[:\-]?\s*(.+)",
#         r"H\.?\s*NO\.?\s*[:\-]?\s*(.+)",
#     ]
#     for p in patterns:
#         m = re.search(p, text)
#         if m:
#             value = m.group(1).strip()
#             # Stop the string if it hits the next field labels
#             value = re.split(r"\b(AGE|GENDER|PHOTO|AVAILABLE|NAME|FATHER|HUSBAND)\b", value)[0].strip()
#             # Clean up trailing punctuation often found in OCR
#             value = re.sub(r"^[.,\-\/ ]+|[.,\-\/ ]+$", "", value)
#             return value if value else "Not Stated"
#     return "Not Stated"

# def parse_voter_text(text):
#     text = normalize_text(text)
    
#     # We use extract_between for name and guardian
#     name = extract_between(text, ["NAME"], ["FATHERS", "HUSBANDS", "HOUSE", "AGE"])
#     guardian = extract_between(text, ["FATHERS NAME", "HUSBANDS NAME"], ["HOUSE", "AGE"])
    
#     # House No, Age, and Gender use specific extraction logic
#     house = extract_house_no(text)
    
#     age_match = re.search(r"AGE\s*:?\s*(\d{1,3})", text)
#     age = age_match.group(1) if age_match else "Not Stated"
    
#     gender = "Not Stated"
#     if re.search(r"\b(MALE|MAIA|MATE)\b", text):
#         gender = "Male"
#     elif re.search(r"\b(FEMALE|FERNALE|FEMAIE|FAMATE)\b", text):
#         gender = "Female"

#     return {
#         "Name": name,
#         "Father/Husband": guardian,
#         "House No": house,
#         "Age": age,
#         "Gender": gender
#     }



import re

# --- CONFIGURATION & TAGS ---
GUARDIAN_TAGS = {
    "FATHER": ["FATHER NAME", "FATHERS NAME", "FATHER"],
    "HUSBAND": ["HUSBAND NAME", "HUSBANDS NAME", "HUSBAND"],
    "MOTHER": ["MOTHER NAME", "MOTHERS NAME", "MOTHER", "MOTHERS"],
    "OTHER": ["OTHER NAME", "OTHERS NAME", "OTHER", "OTHERS"],
}

STOP_KEYS = ["HOUSE", "AGE", "GENDER", "EPIC", "PHOTO"]

# --- HELPER FUNCTIONS ---

def normalize_text(text):
    """Standardizes text and removes common OCR symbols."""
    if not text: return ""
    text = text.upper()
    # Correct common character misinterpretations
    text = text.replace("¢", "C").replace("|", "I").replace("!", "I")
    text = re.sub(r"[;=+?]", ":", text)
    text = re.sub(r"\bPHOTO\b|\bAVAILABLE\b", " ", text)
    # Collapse multiple spaces into one
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_between(text, start_keys, stop_keys):
    """Extracts text between specific keys and cleans leading/trailing noise."""
    start = r"(?:%s)\s*[:\-]?\s*" % "|".join(start_keys)
    # Use positive lookahead for stop keys
    stop = r"(?=\b(?:%s)\b)" % "|".join(stop_keys)

    m = re.search(start + r"(.*?)" + stop, text, re.IGNORECASE)
    if not m:
        return "Not Stated"

    value = m.group(1)
    
    # Clean leading OCR garbage (like / or > from box borders)
    value = re.sub(r"^[^\w\s]+", "", value)
    value = value.strip(" :-")

    # Remove secondary noise if field labels leaked in
    value = re.sub(r"\b(NAME|FATHER|HUSBAND)\b.*$", "", value)

    return value.strip() if value else "Not Stated"

def extract_name_and_guardian(text):
    """Tag-aware parser for Name, Guardian Name, and Guardian Type."""
    # 1. Extract Name (always occurs before any guardian or house tag)
    name = extract_between(
        text,
        start_keys=["NAME"],
        stop_keys=list(GUARDIAN_TAGS["FATHER"] + GUARDIAN_TAGS["HUSBAND"] + 
                       GUARDIAN_TAGS["MOTHER"] + GUARDIAN_TAGS["OTHER"] + STOP_KEYS)
    )

    # 2. Identify Guardian Type and Extract corresponding name
    guardian = "Not Stated"
    guardian_type = "Not Stated"

    for g_type, patterns in GUARDIAN_TAGS.items():
        pattern_regex = r"\b(?:%s)\b" % "|".join(patterns)
        if re.search(pattern_regex, text):
            guardian = extract_between(text, start_keys=patterns, stop_keys=STOP_KEYS)
            guardian_type = g_type
            break

    return name, guardian, guardian_type

def extract_epic(text):
    """Cleans and extracts EPIC numbers (usually 3 letters + 7 digits)."""
    if not text: return "Not Stated"
    t = text.upper().replace("¢", "0")
    t = re.sub(r"[^A-Z0-9]", "", t)

    # Match 3-4 letters followed by 6-8 digits
    m = re.search(r"([A-Z]{3,4})(\d{6,8})", t)
    if m:
        letters, digits = m.groups()
        return f"{letters[:3]}{digits[:7]}"
    return "Not Stated"

# def extract_age(text):
#     """Finds numeric age values."""
#     m = re.search(r"AGE\s*:?\s*(\d{1,3})", text)
#     return m.group(1) if m else "Not Stated"
def extract_age(text):
    # This looks for any number after the word 'Age' or 'Aqe' (common OCR error)
    match = re.search(r'(?:Age|Aqe|Agc)\s*[:\-\s]*(\d+)', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return "Not Stated"
def extract_gender(text):
    """Maps varied OCR outputs to standardized Gender labels."""
    if re.search(r"\b(MALE|MAIA|MATE)\b", text):
        return "Male"
    if re.search(r"\b(FEMALE|FERNALE|FEMAIE|FAMATE)\b", text):
        return "Female"
    return "Not Stated"

def extract_house_no(text):
    """Specific logic for House Numbers to avoid field leakage."""
    if not text: return "Not Stated"
    
    patterns = [
        r"HOUSE\s*NO\.?\s*[:\-]?\s*(.+)",
        r"HOUSE\s*NUMBER\s*[:\-]?\s*(.+)",
        r"H\.?\s*NO\.?\s*[:\-]?\s*(.+)",
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            value = m.group(1).strip()
            # Split if subsequent fields are merged into the same string
            value = re.split(r"\b(AGE|GENDER|PHOTO|AVAILABLE|NAME|FATHER|HUSBAND)\b", 
                             value, flags=re.IGNORECASE)[0].strip()
            
            # Remove leading/trailing non-alphanumeric junk
            value = re.sub(r"^[^\w]+|[^\w]+$", "", value)
            return value if value else "Not Stated"
            
    return "Not Stated"

# --- MAIN PARSER ---

def parse_voter_text(text):
    """Unified function used by the background task in main.py."""
    text = normalize_text(text)
    
    name, guardian, g_type = extract_name_and_guardian(text)

    return {
        "Name": name,
        "Father/Husband": guardian, # Mapping 'Guardian' to your existing column name
        "Guardian Type": g_type,
        "House No": extract_house_no(text),
        "Age": extract_age(text),
        "Gender": extract_gender(text),
        "EPIC No": "Not Stated" # Populated via extract_epic in the main loop
    }