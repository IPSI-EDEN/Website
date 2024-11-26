from .base import *
from dotenv import load_dotenv

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

load_dotenv()
AES_SECRET_KEY = bytes.fromhex(os.getenv('AES_SECRET_KEY'))
