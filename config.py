import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_UPLOADS_DIR = os.path.join(BASE_DIR, 'user_uploads')

LIBRARY_DIR = os.path.join(BASE_DIR, 'library')
VERILOGS_DIR = os.path.join(LIBRARY_DIR, 'verilogs')
CONSTRAINTS_DIR = os.path.join(LIBRARY_DIR, 'constraints')

TEMP_OUTPUTS_DIR = os.path.join(BASE_DIR, 'temp_out')
