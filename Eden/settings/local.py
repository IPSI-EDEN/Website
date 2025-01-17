from .base import *
from dotenv import load_dotenv

DEBUG = True

LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL = '/login/'

STATIC_URL = '/static/'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / '/mediafiles'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

load_dotenv()
AES_SECRET_KEY = bytes.fromhex(os.getenv('AES_SECRET_KEY'))
