import os

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
SHORT_TERM_DIR = os.path.join(DATA_DIR, "short_term")
LONG_TERM_DIR = os.path.join(DATA_DIR, "long_term")
SESSIONS_DIR = os.path.join(LONG_TERM_DIR, "sessions")
MEMORY_FILE = os.path.join(SHORT_TERM_DIR, "nova_memory.json")
