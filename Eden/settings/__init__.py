import os

env = os.environ.get('DJANGO_ENV', 'local')

if env == 'production':
    from .production import *
elif env == 'test':
    from .test import *
else:
    from .local import *
