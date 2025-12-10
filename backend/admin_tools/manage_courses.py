import argparse
import os
import sys
import logging
from google.cloud import firestore

# Add backend root to sys.path to allow imports if run from anywhere
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from constants import AVAILABLE_STYLES

def _get_db():
    db_name = os.environ.get("FIRESTORE_DATABASE", "langbridge").strip()
    if db_name:
        return firestore.Client(database=db_name)
    return firestore.Client(database="langbridge")

def create_or_update_course(course_id, title, languages, voice_configs, styles=None):
    db = _get_db()
    doc_ref = db.collection('courses').document(course_id)
    
    data = {
        "course_id": course_id,
        "title": title,
        "languages": languages,
        "voice_configs": voice_configs,
        "updated_at": firestore.SERVER_TIMESTAMP
    }
    
    # Add multiple styles if provided
    if styles:
        data["available_styles"] = styles
        data["default_style"] = styles[0] if styles else "professional"
    
    doc_ref.set(data, merge=True)
    logger.info(f"Successfully updated course: {course_id}")
    logger.info(f"Data: {data}")

def list_courses():
    db = _get_db()
    courses = db.collection('courses').stream()
    print(f"{'ID':<20} {'Title':<30} {'Styles':<30} {'Languages':<30}")
    print("-" * 110)
    for c in courses:
        d = c.to_dict()
        langs = ",".join(d.get('languages', []))
        styles = d.get('available_styles', [d.get('style', 'default')])
        styles_str = ",".join(styles) if isinstance(styles, list) else str(styles)
        print(f"{c.id:<20} {d.get('title', 'N/A'):<30} {styles_str:<30} {langs:<30}")

def list_styles():
    """List all available presentation styles"""
    print("Available presentation styles:")
    for style in AVAILABLE_STYLES:
        print(f"  - {style}")

def main():
    parser = argparse.ArgumentParser(description="Manage LangBridge Courses")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # ADD/UPDATE Command
    parser_add = subparsers.add_parser('update', help='Create or update a course')
    parser_add.add_argument('--id', required=True, help='Course ID (e.g., course_101)')
    parser_add.add_argument('--title', required=True, help='Course Title')
    parser_add.add_argument('--langs', required=True, help='Comma-separated languages (e.g., en-US,zh-CN,yue-HK)')
    parser_add.add_argument('--styles', help='Comma-separated list of available styles for this course')
    
    # LIST Command
    subparsers.add_parser('list', help='List all courses')
    
    # LIST STYLES Command
    subparsers.add_parser('styles', help='List all available presentation styles')

    args = parser.parse_args()

    if args.command == 'update':
        langs = [l.strip() for l in args.langs.split(',')]
        
        # Default voice configs for now (can be expanded to be arguments later)
        voice_configs = {
            "en-US": {"name": "en-US-Neural2-F", "gender": "FEMALE"},
            "zh-CN": {"name": "cmn-CN-Chirp3-HD-Achernar", "gender": "FEMALE"},
            "yue-HK": {"name": "yue-HK-Standard-A", "gender": "FEMALE"},
            "zh-TW": {"name": "zh-TW-Standard-A", "gender": "FEMALE"}
        }
        
        styles_list = None
        if args.styles:
            styles_list = [s.strip() for s in args.styles.split(',')]
        
        create_or_update_course(args.id, args.title, langs, voice_configs, styles_list)
        
    elif args.command == 'list':
        list_courses()
    elif args.command == 'styles':
        list_styles()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
