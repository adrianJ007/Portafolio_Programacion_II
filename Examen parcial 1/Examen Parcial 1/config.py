import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
