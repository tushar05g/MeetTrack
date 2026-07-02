import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.worker import process_meeting

if __name__ == "__main__":
    process_meeting(3)
