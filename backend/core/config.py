from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
<<<<<<< HEAD
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
=======
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
>>>>>>> 9c94f62 (fix: increase retry backoff and add root health check)
