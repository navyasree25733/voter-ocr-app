import os
import uuid
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Request, BackgroundTasks, Form,  Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from pdf2image import convert_from_path
import base64
# --- Custom OCR & Parser Modules ---
from ocr.voter_ocr import extract_voter_boxes, split_voter_box, get_ocr_text
from parsers.voterP import parse_voter_text, extract_epic
from ocr.voterid_ocr import OCRProcessor
from parsers.voteridP import VoterParser
from datetime import datetime
# --- DB & Security Modules ---
from security import hash_password, verify_password
from db import get_db  # Using your db.py with get_db()
# from workshop import secure_filename

app = FastAPI()

# Session Middleware is crucial for the login system to remember users
# app.add_middleware(SessionMiddleware, secret_key="super-secret-key-change-this")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))
templates = Jinja2Templates(directory="templates")
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Shared in-memory dictionary to track job progress
db_status = {}

# ============================
# BACKGROUND OCR TASK
# ============================

def process_pdf_task(file_id: str, file_path: str, doc_type: str):
    try:
        records = []
        if doc_type == "voter_list":
            pages = convert_from_path(file_path, dpi=200)
            for pg_no, page in enumerate(pages, start=1):
                boxes, img = extract_voter_boxes(page)
                for x, y, w, h in boxes:
                    left_img, right_img = split_voter_box(img, x, y, w, h)
                    data = parse_voter_text(get_ocr_text(left_img))
                    epic = extract_epic(get_ocr_text(right_img))
                    data.update({"EPIC No": epic, "Page No": pg_no})
                    records.append(data)
        
        elif doc_type == "voter_id_card":
            ocr_engine = OCRProcessor()
            voter_parser = VoterParser()
            raw_text = ocr_engine.get_text(file_path)
            data = voter_parser.parse_all(raw_text)
            records.append(data)
        
        # Save results to Excel
        df = pd.DataFrame(records)
        output_path = os.path.join(UPLOAD_DIR, f"{file_id}.xlsx")
        df.to_excel(output_path, index=False)
        
        # Update status to Completed for the UI to pick up
        db_status[file_id].update({
            "status": "Completed", 
            "file": output_path, 
            "count": len(records),
            "doc_type": doc_type,
            "timestamp": datetime.now()
        })
    except Exception as e:
        db_status[file_id].update({"status": f"Error: {str(e)}", "file": None, "count": 0, "timestamp": datetime.now()})

# ============================
# AUTHENTICATION ROUTES
# ============================

@app.get("/")
def home(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_user(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user or not verify_password(password, user['password_hash']):
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Invalid email or password"
        })

    request.session["user"] = user['email']
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/signup")
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
def signup_user(request: Request, full_name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already exists"})

    hashed = hash_password(password)
    cursor.execute("INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)", (full_name, email, hashed))
    conn.commit()
    cursor.close()
    conn.close()

    request.session["user"] = email
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

# ============================
# OCR & DASHBOARD ROUTES
# ============================
@app.get("/dashboard")
async def dashboard(request: Request):
    user_email = request.session.get("user")
    if not user_email:
        return RedirectResponse("/login")

    # 1. NEW: Fetch current user data from the database
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT full_name, avatar_url FROM users WHERE email = %s", 
        (user_email,)
    )
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()

    # 2. Your existing logic for recent jobs
    sorted_jobs = sorted(
        db_status.items(), 
        key=lambda x: x[1].get('timestamp', datetime.min), 
        reverse=True
    )[:5]
    recent_jobs = dict(sorted_jobs)

    # 3. PASS THE 'user' OBJECT TO THE HTML
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "jobs": recent_jobs,
        "user": user_data  # <--- This allows {{ user.full_name }} to work
    })

# ============================
# upload
# ============================

@app.get("/upload")
async def upload_page(request: Request):
    user_email = request.session.get("user")
    if not user_email:
        return RedirectResponse("/login")

    # 1. Fetch user data so the Profile Chip in the top bar works
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT full_name, avatar_url FROM users WHERE email = %s", (user_email,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()

    # 2. Pass the 'user' variable to the template
    return templates.TemplateResponse("upload.html", {
        "request": request, 
        "user": user_data
    })

# ============================
# Process
# ============================
@app.post("/process")
async def process_pdf(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...), doc_type: str = Form(...)):
    if not request.session.get("user"):
        return RedirectResponse("/login")
        
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    ext = file.filename.split('.')[-1]
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.{ext}")
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    db_status[file_id] = {"status": "Processing", "file": None, "count": 0,"filename": original_filename}
    background_tasks.add_task(process_pdf_task, file_id, file_path, doc_type)
    
    return templates.TemplateResponse("view.html", {"request": request, "file_id": file_id})

@app.get("/status/{file_id}")
async def get_status(file_id: str):
    """Used by JS in view.html to poll status"""
    job = db_status.get(file_id, {"status": "Not Found"})
    return {"status": job["status"]}


@app.get("/processed/{file_id}")
async def processed_page(request: Request, file_id: str):
    """Final landing page once OCR is done. Replaces the old 'Processed' logic."""

    job = db_status.get(file_id)
    if not job:
        return RedirectResponse(url="/dashboard")
    
    # Logic to read the Excel file and display records in a table
    if job["status"] == "Completed" and job["file"]:
        try:
            df = pd.read_excel(job["file"])
            # Fill NaN values to avoid template errors and convert to list of dicts
            job["records"] = df.fillna("").to_dict(orient="records")
        except Exception as e:
            job["records"] = []
            print(f"Error loading Excel: {e}")
    else:
        job["records"] = []

    return templates.TemplateResponse("processed.html", {
        "request": request, 
        "file_id": file_id, 
        "job": job
    })

# ============================
# Download
# ============================
@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """Simple download route for the generated Excel file."""
    job = db_status.get(file_id)
    if job and job.get("file"):
        return FileResponse(
            job["file"], 
            filename=f"voter_data_{file_id[:8]}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    return {"error": "File not ready or not found"}

def require_login(request: Request):
    return "user_id" in request.session

# ============================
# extracted
# ============================
@app.get("/extracted", response_class=HTMLResponse)
async def get_extracted_list(request: Request):
    """Route to view the list of all processed files"""
    if not request.session.get("user"):
        return RedirectResponse("/login")
    
    # We pass 'db_status' as 'jobs' to match your template loop
    return templates.TemplateResponse("extracted.html", {
        "request": request, 
        "jobs": db_status
    })

# ============================
# Profile
# ============================

@app.get("/profile")
async def get_profile(request: Request):
    email = request.session.get("user")
    if not email: return RedirectResponse("/login")
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT full_name, email, phone, avatar_url FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

@app.post("/update-profile")
async def update_profile(request: Request, fullName: str = Form(...), phone: str = Form(None)):
    email = request.session.get("user")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET full_name = %s, phone = %s WHERE email = %s", (fullName, phone, email))
    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "success"}

@app.post("/update-avatar")
async def update_avatar(request: Request, file: UploadFile = File(...)):
    email = request.session.get("user")
    contents = await file.read()
    encoded = base64.b64encode(contents).decode()
    avatar_data = f"data:{file.content_type};base64,{encoded}"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET avatar_url = %s WHERE email = %s", (avatar_data, email))
    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "success"}

@app.post("/remove-avatar")
async def remove_avatar(request: Request):
    email = request.session.get("user")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET avatar_url = NULL WHERE email = %s", (email,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "success"}

# ============================
# settings
# ============================
@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user_email = request.session.get("user")
    if not user_email:
        return RedirectResponse("/login")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT full_name, phone FROM users WHERE email = %s", (user_email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user_name": user['full_name'],
        "phone": user['phone'] or ""
    })

@app.post("/update-password")
async def update_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    user_email = request.session.get("user")
    if new_password != confirm_password:
        return RedirectResponse("/settings?msg=Passwords+do+not+match&type=error", status_code=303)

    # Logic: Verify current_password against DB, then update to new_password
    # cursor.execute("UPDATE users SET password = %s WHERE email = %s", (new_password, user_email))
    
    return RedirectResponse("/settings?msg=Password+updated+successfully&type=success", status_code=303)

@app.post("/update-preferences")
async def update_preferences(
    request: Request,
    phone: str = Form(...),
    theme: str = Form(...)
):
    user_email = request.session.get("user")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET phone = %s WHERE email = %s", (phone, user_email))
    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse("/settings?msg=Preferences+saved&type=success", status_code=303)