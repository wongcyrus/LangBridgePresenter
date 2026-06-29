import os
import sys
import pytest
import pandas as pd
import uuid
import time
from google.cloud import firestore

# Add backend directory to path so we can import admin_tools
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from admin_tools import export_cache_to_excel
from admin_tools import import_cache_from_excel
from admin_tools import config

pytestmark = [pytest.mark.integration, pytest.mark.admin, pytest.mark.slow]

# Use a unique course ID for this test run to avoid collisions
TEST_COURSE_ID = f"test_course_{str(uuid.uuid4())[:8]}"
TEST_EXCEL_FILE = f"test_cache_{str(uuid.uuid4())[:8]}.xlsx"

@pytest.fixture(scope="module")
def db():
    """Return a real Firestore client connected to the project."""
    project_id = getattr(config, 'project_id', None)
    if not project_id:
        pytest.skip("Project ID not found in config.py")
    return firestore.Client(project=project_id, database="langbridge")

@pytest.fixture(scope="module")
def setup_test_data(db):
    """Create a seed cache entry in Firestore."""
    collection_ref = db.collection("langbridge_presentation_cache")
    
    # Unique cache key with timestamp to avoid collisions
    context_hash = f"testhash_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    cache_key = f"v1:en:{context_hash}"
    
    data = {
        "message": "Original Message",
        "language_code": "en",
        "context": "Test Context",
        "context_hash": context_hash,
        "course_ids": [TEST_COURSE_ID],
        "audio_url": "http://original-url",
        "updated_at": firestore.SERVER_TIMESTAMP
    }
    
    doc_ref = collection_ref.document(cache_key)
    try:
        doc_ref.set(data)
    except Exception as e:
        pytest.skip(f"Failed to create test data in Firestore: {e}")
    
    yield cache_key
    
    # Cleanup
    try:
        doc_ref.delete()
    except Exception as e:
        print(f"Warning: Failed to delete test document: {e}")
    
    if os.path.exists(TEST_EXCEL_FILE):
        try:
            os.remove(TEST_EXCEL_FILE)
        except Exception as e:
            print(f"Warning: Failed to delete test Excel file: {e}")

def test_export_and_import_cycle(db, setup_test_data):
    """
    Integration Test:
    1. Export the seeded data to Excel.
    2. Verify Excel content.
    3. Modify Excel (change message).
    4. Import back to Firestore.
    5. Verify Firestore update (Message change & Audio URL change).
    """
    cache_key = setup_test_data
    
    # --- Step 1: Export ---
    print(f"\n[1/5] Exporting cache for course {TEST_COURSE_ID}...")
    try:
        export_cache_to_excel.export_to_excel(TEST_COURSE_ID, TEST_EXCEL_FILE)
    except Exception as e:
        pytest.fail(f"Export failed: {e}")
    
    assert os.path.exists(TEST_EXCEL_FILE), "Export file was not created"
    
    # --- Step 2: Verify Export ---
    print("[2/5] Verifying exported Excel content...")
    try:
        df = pd.read_excel(TEST_EXCEL_FILE)
    except Exception as e:
        pytest.fail(f"Failed to read Excel file: {e}")
    
    assert len(df) >= 1, f"Expected at least 1 row in exported Excel, got {len(df)}"
    
    # Find the row with our cache key
    matching_rows = df[df["Cache Key (Do Not Edit)"] == cache_key]
    assert len(matching_rows) == 1, f"Expected exactly 1 row with cache key {cache_key}"
    
    row = matching_rows.iloc[0]
    assert row["Generated Message (Edit this)"] == "Original Message", \
        f"Expected 'Original Message', got '{row['Generated Message (Edit this)']}'"
    
    # --- Step 3: Modify Excel ---
    print("[3/5] Modifying Excel with new message...")
    new_message = f"Updated Message {str(uuid.uuid4())[:8]}"
    row_index = matching_rows.index[0]
    df.at[row_index, "Generated Message (Edit this)"] = new_message
    
    try:
        df.to_excel(TEST_EXCEL_FILE, index=False)
    except Exception as e:
        pytest.fail(f"Failed to save modified Excel: {e}")
    
    # --- Step 4: Import ---
    print("[4/5] Importing modified Excel...")
    try:
        import_cache_from_excel.import_from_excel(TEST_COURSE_ID, TEST_EXCEL_FILE)
    except Exception as e:
        pytest.fail(f"Import failed: {e}")
    
    # Wait for async operations to complete
    time.sleep(2)
    
    # --- Step 5: Verify Firestore Update ---
    print("[5/5] Verifying Firestore update...")
    doc_ref = db.collection("langbridge_presentation_cache").document(cache_key)
    doc = doc_ref.get()
    assert doc.exists, f"Document {cache_key} not found in Firestore"
    
    data = doc.to_dict()
    assert data["message"] == new_message, \
        f"Expected message '{new_message}', got '{data['message']}'"
    assert data["audio_url"] != "http://original-url", \
        f"Audio URL should have been updated, still: {data['audio_url']}"
    
    print(f"✓ Test cycle completed successfully! New audio URL: {data['audio_url']}")