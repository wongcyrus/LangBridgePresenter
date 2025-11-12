
"""
Delete or undelete an API key from a hardcoded list for authentication only.
No Google Cloud logic.
"""

VALID_API_KEYS = [
    {"student_id": "1", "name": "Alice", "key": "key1"},
    {"student_id": "2", "name": "Bob", "key": "key2"},
    {"student_id": "3", "name": "Charlie", "key": "key3"}
]


def delete_key(key):
    global VALID_API_KEYS
    before = len(VALID_API_KEYS)
    VALID_API_KEYS = [k for k in VALID_API_KEYS if k["key"] != key]
    after = len(VALID_API_KEYS)
    print(f"Deleted key {key}. Keys before: {before}, after: {after}")


def undelete_key(student_id, name, key):
    global VALID_API_KEYS
    VALID_API_KEYS.append({"student_id": student_id, "name": name, "key": key})
    print(f"Undeleted key {key} for {name} (student_id: {student_id})")


if __name__ == "__main__":
    # Example usage
    delete_key("key1")
    undelete_key("1", "Alice", "key1")


if __name__ == "__main__":
    undelete_key(name="projects/310301685106/locations/global/keys/studentid-12345678")