import argparse
import os
import sys
import json
import glob
import logging
try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required. Please run: pip install -r backend/admin_tools/requirements.txt")
from google.cloud import firestore

# Add backend root to sys.path to allow imports if run from anywhere
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PRESENTERS_DIR = os.path.join(os.path.dirname(__file__), 'presenters')

def _get_db():
    db_name = os.environ.get("FIRESTORE_DATABASE", "langbridge").strip()
    if db_name:
        return firestore.Client(database=db_name)
    return firestore.Client(database="langbridge")

def create_or_update_presenter(presenter_id, name, language, background):
    db = _get_db()
    doc_ref = db.collection('presenters').document(presenter_id)
    
    data = {
        "id": presenter_id,
        "name": name,
        "language": language,
        "background": background,
        "updated_at": firestore.SERVER_TIMESTAMP
    }
    
    doc_ref.set(data, merge=True)
    logger.info(f"Successfully updated presenter: {presenter_id}")
    logger.info(f"Data: {data}")

def sync_presenters():
    if not os.path.exists(PRESENTERS_DIR):
        logger.error(f"Presenters directory not found: {PRESENTERS_DIR}")
        return

    db = _get_db()
    batch = db.batch()
    count = 0
    
    files = glob.glob(os.path.join(PRESENTERS_DIR, "*.yaml")) + glob.glob(os.path.join(PRESENTERS_DIR, "*.yml"))
    if not files:
        logger.warning(f"No YAML files found in {PRESENTERS_DIR}")
        return

    logger.info(f"Found {len(files)} presenter definition(s) in {PRESENTERS_DIR}")

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Determine ID: use 'id' field or filename (without extension)
            presenter_id = data.get('id')
            if not presenter_id:
                presenter_id = os.path.splitext(os.path.basename(file_path))[0]
                data['id'] = presenter_id
            
            required_fields = ['name', 'language', 'background']
            missing = [f for f in required_fields if f not in data]
            if missing:
                logger.error(f"Skipping {file_path}: Missing required fields {missing}")
                continue
                
            doc_ref = db.collection('presenters').document(presenter_id)
            data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            # Ensure only relevant fields are written (optional, but good for hygiene)
            write_data = {
                "id": presenter_id,
                "name": data['name'],
                "language": data['language'],
                "background": data['background'],
                "updated_at": data['updated_at']
            }
            
            batch.set(doc_ref, write_data, merge=True)
            count += 1
            logger.info(f"Queued update for presenter: {presenter_id} ({data['name']})")
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

    if count > 0:
        batch.commit()
        logger.info(f"Successfully synchronized {count} presenters.")
    else:
        logger.info("No valid presenters found to sync.")

def list_presenters():
    db = _get_db()
    presenters = db.collection('presenters').stream()
    print(f"{'ID':<20} {'Name':<30} {'Language':<15} {'Background':<30}")
    print("-" * 95)
    for p in presenters:
        d = p.to_dict()
        # Truncate background if too long for display
        bg = d.get('background', 'N/A')
        if len(bg) > 50:
            bg = bg[:47] + "..."
        print(f"{p.id:<20} {d.get('name', 'N/A'):<30} {d.get('language', 'N/A'):<15} {bg:<30}")

def main():
    parser = argparse.ArgumentParser(description="Manage LangBridge Presenters")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # SYNC Command (Primary)
    subparsers.add_parser('sync', help='Sync presenters from backend/admin_tools/presenters/*.yaml')

    # UPDATE Command (Manual Override)
    parser_add = subparsers.add_parser('update', help='Manually create or update a presenter')
    parser_add.add_argument('--id', required=True, help='Presenter ID')
    parser_add.add_argument('--name', required=True, help='Presenter Name')
    parser_add.add_argument('--language', required=True, help='Primary Language (e.g., en-US)')
    parser_add.add_argument('--background', required=True, help='Background description')
    
    # LIST Command
    subparsers.add_parser('list', help='List all presenters')

    args = parser.parse_args()

    if args.command == 'sync':
        sync_presenters()
    elif args.command == 'update':
        create_or_update_presenter(args.id, args.name, args.language, args.background)
    elif args.command == 'list':
        list_presenters()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()