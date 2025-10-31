# 🎧 VibeSheet

It connects Spotify to a shared Google Sheets spreadsheet to show what each user is listening to in real time.

---

## 🚀 Setup

### 1. Creating the environment

```bash
python -m venv venv
source venv/bin/activate # (or venv\Scripts\activate on Windows)

```

### 2. Installing dependencies

```bash
pip install -r requirements.txt

```

### 3. Creating the `.env` file

Copy `.env.example` to `.env` and fill it with your credentials.

### 4. Run the app

```bash
uvicorn main:app --reload

```

Then visit:

```bash
http://localhost:8000/health
```

## 📦 Project Structure

```bash
vibesheet/
├── auth/       # Spotify OAuth
├── sheets/     # Google Sheets integration
├── services/   # Spotify polling
├── utils/  # Scheduler / background jobs
└── main.py     # FastAPI entrypoint
```
