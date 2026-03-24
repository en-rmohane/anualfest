# 🎭 Annual Fest 2025 – Performance Registration App

## Folders Structure
```
annual_fest/
├── app.py              ← Main Flask application
├── requirements.txt    ← Dependencies
├── submissions.json    ← Auto-generated (data store)
├── static/
│   └── uploads/        ← Uploaded music files
└── templates/
    ├── submit.html     ← Student registration form
    ├── admin_login.html← Admin login page
    └── dashboard.html  ← Admin dashboard
```

## Setup & Run (Step by Step)

### 1. Install Python (if not already installed)
Download from: https://python.org

### 2. Install Flask
```bash
pip install -r requirements.txt
```

### 3. Run the App
```bash
python app.py
```

### 4. URLs
- **Student Form:** http://localhost:5000/
- **Admin Login:** http://localhost:5000/admin
- **Admin Password:** `admin123`

### 5. To share link with students
Find your computer's IP:
- Windows: `ipconfig` → IPv4 address
- Mac/Linux: `ifconfig` → inet address

Then send the link: `http://YOUR_IP:5000/`
Students must be on the same WiFi network.

---

## Features
✅ Student registration form (Solo/Group)
✅ Dance/Song/Skit category selection  
✅ Music file upload (MP3, WAV, OGG, M4A)
✅ Admin dashboard with all submissions
✅ Audio playback in dashboard
✅ Approve / Reject / Pending status
✅ Search & filter submissions
✅ Delete entries
✅ Live stats (Total, Solo, Group, Pending, Approved)

## Change Admin Password
`app.py` file at line 13:
```python
ADMIN_PASSWORD = "admin123"  ← Enter your password here
```

## Vercel Deployment Notes
This application is configured for Vercel deployment (`vercel.json` included). However, please be aware:
- **Ephemeral Storage:** Because Vercel has a read-only filesystem, all uploads and submissions are routed to the `/tmp` directory. Vercel automatically wipes `/tmp` during inactive periods or cold starts. So your data **will not persist permanently**. 
- To use this system for a real production event permanently, you should convert the `submissions.json` to a Database (like Firebase or MongoDB) and file uploads to Cloud Storage (like AWS S3 or Cloudinary).
