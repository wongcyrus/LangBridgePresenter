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
try:
    from runtime_config import default_project_id
except ModuleNotFoundError:
    from backend.admin_tools.runtime_config import default_project_id

def _get_db():
    project_id = default_project_id()
    db_name = (os.environ.get("FIRESTORE_DATABASE") or "").strip()
    if not db_name:
        raise RuntimeError("FIRESTORE_DATABASE is not configured.")
    return firestore.Client(project=project_id, database=db_name)

def create_or_update_course(
    course_id,
    title,
    languages,
    voice_configs,
    styles=None,
    package_id=None,
    package_bucket=None,
    package_prefix=None,
    package_manifest_url=None,
    package_version=None,
):
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

    if package_id:
        data["package_id"] = package_id
    if package_bucket:
        data["package_bucket"] = package_bucket
    if package_prefix:
        data["package_prefix"] = package_prefix
    data["package_manifest_path"] = ""
    if package_manifest_url:
        data["package_manifest_url"] = package_manifest_url
    if package_version:
        data["package_version"] = package_version
    if package_id or package_bucket or package_prefix or package_manifest_url:
        data["package_status"] = "ready"
    
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


def link_course_package(course_id, package_id, package_bucket="", package_prefix="", manifest_url="", package_version="", status="ready"):
    if not manifest_url:
        raise ValueError("manifest_url is required")
    db = _get_db()
    now = firestore.SERVER_TIMESTAMP
    package_ref = db.collection("course_packages").document(package_id)
    package_ref.set(
        {
            "package_id": package_id,
            "course_id": course_id,
            "package_bucket": package_bucket,
            "package_prefix": package_prefix,
            "manifest_path": "",
            "manifest_url": manifest_url,
            "package_version": package_version,
            "status": status,
            "source": "admin_script",
            "updated_at": now,
            "created_at": now,
        },
        merge=True,
    )
    db.collection("courses").document(course_id).set(
        {
            "package_id": package_id,
            "package_bucket": package_bucket,
            "package_prefix": package_prefix,
            "package_manifest_path": "",
            "package_manifest_url": manifest_url,
            "package_version": package_version,
            "package_status": status,
            "updated_at": now,
        },
        merge=True,
    )
    logger.info(f"Linked course {course_id} to package {package_id}")


def main():
    parser = argparse.ArgumentParser(description="Manage LangBridge Courses")
    parser.add_argument("--project-id", required=True, help="Target GCP project")
    parser.add_argument("--database", default="langbridge", help="Firestore database")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # ADD/UPDATE Command
    parser_add = subparsers.add_parser('update', help='Create or update a course')
    parser_add.add_argument('--id', required=True, help='Course ID (e.g., course_101)')
    parser_add.add_argument('--title', required=True, help='Course Title')
    parser_add.add_argument('--langs', required=True, help='Comma-separated languages (e.g., en-US,zh-CN,yue-HK)')
    parser_add.add_argument('--styles', help='Comma-separated list of available styles for this course')
    parser_add.add_argument('--package-id', help='Optional linked package ID')
    parser_add.add_argument('--package-bucket', help='Optional package bucket')
    parser_add.add_argument('--package-prefix', help='Optional package prefix')
    parser_add.add_argument('--package-manifest-url', help='Optional package manifest URL')
    parser_add.add_argument('--package-version', help='Optional package version')
    
    # LIST Command
    subparsers.add_parser('list', help='List all courses')
    
    # LIST STYLES Command
    subparsers.add_parser('styles', help='List all available presentation styles')

    # LINK PACKAGE Command
    parser_link = subparsers.add_parser('link-package', help='Create/update course_packages doc and link it to a course')
    parser_link.add_argument('--course-id', required=True, help='Course ID')
    parser_link.add_argument('--package-id', required=True, help='Immutable package ID')
    parser_link.add_argument('--package-bucket', default='', help='Package bucket (optional metadata)')
    parser_link.add_argument('--package-prefix', default='', help='Package prefix (optional metadata)')
    parser_link.add_argument('--manifest-url', required=True, help='Manifest URL (HTTP/HTTPS)')
    parser_link.add_argument('--package-version', default='', help='Human-readable package version')
    parser_link.add_argument('--status', default='ready', help='Package status')

    args = parser.parse_args()
    os.environ["ADMIN_TOOLS_PROJECT_ID"] = args.project_id
    os.environ["FIRESTORE_DATABASE"] = args.database

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
        
        create_or_update_course(
            args.id,
            args.title,
            langs,
            voice_configs,
            styles_list,
            package_id=args.package_id,
            package_bucket=args.package_bucket,
            package_prefix=args.package_prefix,
            package_manifest_url=args.package_manifest_url,
            package_version=args.package_version,
        )
        
    elif args.command == 'list':
        list_courses()
    elif args.command == 'styles':
        list_styles()
    elif args.command == 'link-package':
        link_course_package(
            course_id=args.course_id,
            package_id=args.package_id,
            package_bucket=args.package_bucket,
            package_prefix=args.package_prefix,
            manifest_url=args.manifest_url,
            package_version=args.package_version,
            status=args.status,
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
