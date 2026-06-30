#!/usr/bin/env python3
import argparse
import os
from typing import Optional

from google.cloud import firestore
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


def _doc_id(uid: Optional[str], email: Optional[str]) -> str:
    if uid:
        return f"uid:{uid.strip()}"
    if email:
        return f"email:{email.strip().lower()}"
    raise ValueError("uid or email is required")


def grant_admin(uid: Optional[str], email: Optional[str], note: str):
    db = _get_db()
    doc_id = _doc_id(uid, email)
    payload = {
        "uid": uid.strip() if uid else None,
        "email": email.strip().lower() if email else None,
        "active": True,
        "note": note or "",
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    db.collection("admin_users").document(doc_id).set(payload, merge=True)
    print(f"Granted admin: {doc_id}")


def revoke_admin(uid: Optional[str], email: Optional[str]):
    db = _get_db()
    doc_id = _doc_id(uid, email)
    ref = db.collection("admin_users").document(doc_id)
    snap = ref.get()
    if not snap.exists:
        print(f"Admin user not found: {doc_id}")
        return
    ref.set({"active": False, "updated_at": firestore.SERVER_TIMESTAMP}, merge=True)
    print(f"Revoked admin: {doc_id}")


def delete_admin(uid: Optional[str], email: Optional[str]):
    db = _get_db()
    doc_id = _doc_id(uid, email)
    db.collection("admin_users").document(doc_id).delete()
    print(f"Deleted admin record: {doc_id}")


def list_admins(active_only: bool):
    db = _get_db()
    query = db.collection("admin_users")
    if active_only:
        query = query.where("active", "==", True)

    docs = list(query.stream())
    if not docs:
        print("No admin users found.")
        return

    print(f"{'DOC_ID':<45} {'ACTIVE':<8} {'UID':<32} {'EMAIL':<40} NOTE")
    print("-" * 140)
    for doc in docs:
        data = doc.to_dict() or {}
        print(
            f"{doc.id:<45} "
            f"{str(data.get('active', False)):<8} "
            f"{str(data.get('uid', '') or ''):<32} "
            f"{str(data.get('email', '') or ''):<40} "
            f"{str(data.get('note', '') or '')}"
        )


def main():
    parser = argparse.ArgumentParser(description="Manage admin users for voice-chat admin APIs")
    parser.add_argument("--project-id", required=True, help="Target GCP project")
    parser.add_argument("--database", default="langbridge", help="Firestore database")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_grant = subparsers.add_parser("grant", help="Grant admin access")
    parser_grant.add_argument("--uid", help="Firebase UID")
    parser_grant.add_argument("--email", help="User email")
    parser_grant.add_argument("--note", default="", help="Optional note")

    parser_revoke = subparsers.add_parser("revoke", help="Revoke admin access")
    parser_revoke.add_argument("--uid", help="Firebase UID")
    parser_revoke.add_argument("--email", help="User email")

    parser_delete = subparsers.add_parser("delete", help="Delete admin record")
    parser_delete.add_argument("--uid", help="Firebase UID")
    parser_delete.add_argument("--email", help="User email")

    parser_list = subparsers.add_parser("list", help="List admin users")
    parser_list.add_argument("--active-only", action="store_true", help="Show only active admin users")

    args = parser.parse_args()
    os.environ["ADMIN_TOOLS_PROJECT_ID"] = args.project_id
    os.environ["FIRESTORE_DATABASE"] = args.database

    if args.command == "grant":
        grant_admin(args.uid, args.email, args.note)
    elif args.command == "revoke":
        revoke_admin(args.uid, args.email)
    elif args.command == "delete":
        delete_admin(args.uid, args.email)
    elif args.command == "list":
        list_admins(args.active_only)


if __name__ == "__main__":
    main()
