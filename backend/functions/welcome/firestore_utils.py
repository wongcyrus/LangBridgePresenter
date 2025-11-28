from google.cloud import firestore
import logging
import os

logger = logging.getLogger(__name__)

def get_config():
    try:
        db = firestore.Client(database="langbridge")
        doc_ref = db.collection('langbridge_config').document('messages')
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        else:
            logger.warning("Config document not found, using default.")
            return get_default_config()
    except Exception as e:
        logger.error(f"Failed to load config from Firestore: {e}")
        return get_default_config()

def get_default_config():
    return {
        "welcome_messages": {
            "en": "Welcome! How can I help you today?",
            "zh": "欢迎！今天我能为您做些什么？"
        },
        "goodbye_messages": {
            "en": "Goodbye! Have a great day!",
            "zh": "再见！祝您有美好的一天！"
        },
        "recommended_questions": {
            "en": [
                "What can you help me with?",
                "How does this work?",
                "Can you explain more about this topic?"
            ],
            "zh": [
                "你能帮我做什么？",
                "这是如何工作的？",
                "你能详细解释一下这个话题吗？"
            ]
        },
        "talk_responses": {
            "en": "I understand your question. Let me help you with that.",
            "zh": "我理解您的问题。让我来帮助您。"
        },
        "presentation_messages": {
            "en": "Hello! I am your presenter for today. Let's get started.",
            "zh-CN": "大家好！我是今天的演讲者。让我们开始吧。",
            "yue-HK": "大家好！我係今日嘅演讲者。让我哋开始啦。"
        }
    }

def _get_db():
    # Assuming the database name is consistent across the project or set via env var
    db_name = os.environ.get("FIRESTORE_DATABASE", "langbridge").strip()
    if db_name:
        return firestore.Client(database=db_name)
    return firestore.Client(database="langbridge")

def get_document(collection_name, document_id):
    db = _get_db()
    doc_ref = db.collection(collection_name).document(document_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None
