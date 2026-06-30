import importlib.util
import os

import pytest

pytestmark = pytest.mark.unit


def _load_module():
    module_name = "manage_admin_users_under_test"
    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../admin_tools/manage_admin_users.py")
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_doc_id_requires_uid_or_email():
    module = _load_module()
    with pytest.raises(ValueError):
        module._doc_id(None, None)


def test_grant_admin_sets_active_record(monkeypatch):
    module = _load_module()
    from unittest.mock import MagicMock

    db = MagicMock()
    collection_ref = db.collection.return_value
    doc_ref = collection_ref.document.return_value
    monkeypatch.setattr(module, "_get_db", lambda: db)

    module.grant_admin(uid=None, email="Admin@Example.com", note="test")

    collection_ref.document.assert_called_once_with("email:admin@example.com")
    assert doc_ref.set.called
    payload = doc_ref.set.call_args[0][0]
    assert payload["active"] is True
    assert payload["email"] == "admin@example.com"


def test_revoke_admin_marks_inactive(monkeypatch):
    module = _load_module()
    from unittest.mock import MagicMock

    db = MagicMock()
    collection_ref = db.collection.return_value
    doc_ref = collection_ref.document.return_value
    snap = MagicMock()
    snap.exists = True
    doc_ref.get.return_value = snap
    monkeypatch.setattr(module, "_get_db", lambda: db)

    module.revoke_admin(uid="u-1", email=None)

    collection_ref.document.assert_called_once_with("uid:u-1")
    assert doc_ref.set.called
    payload = doc_ref.set.call_args[0][0]
    assert payload["active"] is False
