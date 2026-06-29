import os
import sys


CLIENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if CLIENT_ROOT not in sys.path:
    sys.path.insert(0, CLIENT_ROOT)
