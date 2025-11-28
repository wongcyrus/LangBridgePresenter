import argparse
import json
import logging
import os
import sys
import time
import glob
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.cloud import storage, firestore, texttospeech

# Add backend root to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add functions/config to sys.path to allow importing logic modules
functions_config_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "functions",
    "config"
)
sys.path.append(functions_config_path)

# Import admin tool for creating the course
from admin_tools.manage_courses import create_or_update_course

# --- SETUP ENV VARS BEFORE IMPORTS ---
# This is critical for google.genai / vertexai initialization in message_generator

def _preload_env_vars():
    """Pre-loads project config to set env vars before modules initialize."""
    # Try to find cdktf_outputs.json
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "cdktf_outputs.json"
    )
    
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-east1")
    
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r') as f:
                data = json.load(f)
                outputs = data.get("cdktf", data)
                project_id = outputs.get("project-id", project_id)
        except Exception:
            pass

    if project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
        os.environ["GOOGLE_CLOUD_LOCATION"] = location
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
        print(f"✅ Pre-set Env: PROJECT={project_id}, LOCATION={location}, VERTEXAI=true")
    else:
        print("⚠️  Warning: GOOGLE_CLOUD_PROJECT not found. GenAI might fail.")

_preload_env_vars()

# Import logic modules from functions/config
try:
    import message_generator
    import course_utils
    import firestore_utils
    import utils
except ImportError as e:
    logging.error(f"Failed to import function modules: {e}", exc_info=True)
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- HELPERS ---

def load_cdktf_outputs():
    """
    Loads backend/cdktf_outputs.json to get infrastructure details.
    """
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "cdktf_outputs.json"
    )
    
    if not os.path.exists(output_path):
        return {}
        
    try:
        with open(output_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read cdktf_outputs.json: {e}")
        return {}

def upload_to_bucket(bucket_name, source_file_path, destination_blob_name):
    """
    Uploads a file to the bucket and returns the public URL.
    """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_filename(source_file_path)
        
        # Construct public URL (assuming the bucket allows public access or we use the media link)
        url = blob.public_url
        logger.info(f"✅ Uploaded {source_file_path} to {destination_blob_name}. URL: {url}")
        return url
    except Exception as e:
        logger.error(f"❌ Failed to upload {source_file_path} to bucket: {e}")
        return None

def load_notes_for_language(json_path, lang_code):
    """
    Loads slide notes from a language-specific progress JSON file.
    Returns a dict: {slide_number_str: note_text}
    """
    if not os.path.exists(json_path):
        return {}
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        slides_dict = data.get("slides", {})
        notes_map = {}
        
        for slide in slides_dict.values():
            # Priority: original_notes (often English source) -> note (generated translation)
            # For non-English files, 'note' usually contains the translated text.
            note = slide.get("note", "")
            if not note and lang_code == "en":
                 note = slide.get("original_notes", "")
            
            idx = str(slide.get("slide_index"))
            if note:
                notes_map[idx] = note
                
        return notes_map
    except Exception as e:
        logger.error(f"Failed to load notes from {json_path}: {e}")
        return {}

def load_slides_structure(json_path):
    """
    Parses the 'en' progress JSON to establish the slide order and structure.
    Returns a list of dicts with 'slide_number' and 'original_context' (English).
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        slides_dict = data.get("slides", {})
        sorted_slides = sorted(slides_dict.values(), key=lambda x: x.get("slide_index", 0))
        
        slides_data = []
        for slide in sorted_slides:
            note = slide.get("original_notes", "") or slide.get("note", "")
            slides_data.append({
                "slide_number": str(slide.get("slide_index")),
                "context": note 
            })
            
        return slides_data
    except Exception as e:
        logger.error(f"Failed to load structure from {json_path}: {e}")
        return []

# --- LOGIC MIGRATION ---

def process_slide_locally(
    slide_number, 
    context, 
    ppt_filename, 
    course_id, 
    languages, 
    bucket_name, 
    backend_project_id, 
    client_project_id, 
    visual_links,
    pre_generated_messages=None
):
    """
    Replicates logic to generate/broadcast. 
    Now accepts `pre_generated_messages`: { 'zh-CN': '...', 'yue-HK': '...' }
    """
    logger.info(f"--- Processing Slide {slide_number} ---")
    pre_generated_messages = pre_generated_messages or {}
    
    os.environ["GOOGLE_CLOUD_PROJECT"] = backend_project_id

    # Log the event 
    _preview = context[:50] + ("..." if len(context) > 50 else "")
    course_utils.log_presentation_event(course_id, {
        "type": "slide_change",
        "context_snippet": _preview,
        "languages": languages,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

    # Prepare broadcast payload
    broadcast_payload = {
        "updated_at": firestore.SERVER_TIMESTAMP,
        "languages": {},
        "original_context": context,
        "course_id": course_id,
        "supported_languages": languages,
        "page_number": slide_number
    }

    # Normalize ppt filename
    if ppt_filename:
        try:
            _ppt_norm = os.path.splitext(ppt_filename.lower())[0]
            for _s in ("_with_visuals", "_with_notes", "_visuals", "_en", "_zh-cn", "_yue-hk"):
                if _ppt_norm.endswith(_s):
                    _ppt_norm = _ppt_norm[: -len(_s)]
            broadcast_payload["ppt_filename"] = ppt_filename
            broadcast_payload["ppt_filename_norm"] = _ppt_norm
        except Exception:
            broadcast_payload["ppt_filename"] = ppt_filename
    
    # Compute context hash
    try:
        _norm_ctx = utils.normalize_context(context)
        _ctx_hash = hashlib.sha256(_norm_ctx.encode("utf-8")).hexdigest()[:12]
        broadcast_payload["context_hash"] = _ctx_hash
    except Exception:
        pass

    # Step 1: Generate/Retrieve Messages
    logger.info("Preparing messages for %d languages...", len(languages))
    message_results = {}

    def generate_for_language(lang):
        # OPTIMIZATION: Check if we already have the text
        if lang in pre_generated_messages:
            existing_text = pre_generated_messages[lang]
            if existing_text:
                logger.info(f"[{lang}] ✅ Found pre-generated text.")
                return (lang, existing_text, None, None)
        
        # Fallback to Agent Generation
        logger.info(f"[{lang}] ⚠️  No pre-generated text found. Calling Agent...")
        try:
            result = message_generator.generate_presentation_message(lang, context, course_id=course_id)
            if isinstance(result, tuple):
                generated, audio_url = result
            else:
                generated = result
                audio_url = None
            
            if generated:
                return (lang, generated, audio_url, None)
            else:
                return (lang, None, None, "Generation failed")
        except Exception as e:
            return (lang, None, None, str(e))

    with ThreadPoolExecutor(max_workers=min(len(languages), 5)) as executor:
        future_to_lang = {executor.submit(generate_for_language, lang): lang for lang in languages}
        for future in as_completed(future_to_lang):
            lang, generated, audio_url, error = future.result()
            if generated:
                message_results[lang] = {
                    "text": generated,
                    "audio_url": audio_url
                }
                # logger.info(f"[{lang}] Text ready.")
            elif error:
                logger.warning(f"[{lang}] Failed: {error}")

    # Step 2: Generate MP3s
    if not bucket_name:
        logger.warning("SPEECH_FILE_BUCKET not provided - skipping audio.")
        for lang, data in message_results.items():
             broadcast_payload["languages"][lang] = {"text": data["text"]}
             if lang in visual_links:
                 broadcast_payload["languages"][lang]["slide_link"] = visual_links[lang]
    else:
        logger.info("Generating/checking MP3s...")
        
        def generate_mp3_for_language(lang, data):
            generated = data["text"]
            cached_audio_url = data.get("audio_url")
            
            if cached_audio_url:
                logger.info(f"[{lang}] Using cached audio: {cached_audio_url}")
                return (lang, {"text": generated, "audio_url": cached_audio_url}, None)
            
            lang_data = {"text": generated}
            try:
                norm_ctx = utils.normalize_context(context)
                content_hash = hashlib.sha256(norm_ctx.encode("utf-8")).hexdigest()[:12]
                filename = f"speech_{lang}_{content_hash}.mp3"
                
                storage_client = storage.Client(project=backend_project_id)
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(filename)
                
                if not blob.exists():
                    logger.info(f"[{lang}] Generating TTS...")
                    tts_client = texttospeech.TextToSpeechClient()
                    voice = course_utils.get_voice_params(course_id, lang)
                    
                    clean_text = utils.sanitize_text_for_tts(generated)
                    synthesis_input = texttospeech.SynthesisInput(text=clean_text)
                    audio_config = texttospeech.AudioConfig(
                        audio_encoding=texttospeech.AudioEncoding.MP3,
                        speaking_rate=1.0
                    )
                    
                    tts_response = tts_client.synthesize_speech(
                        input=synthesis_input,
                        voice=voice,
                        audio_config=audio_config
                    )
                    
                    blob.upload_from_string(
                        tts_response.audio_content,
                        content_type="audio/mpeg"
                    )
                    logger.info(f"[{lang}] Uploaded {filename}")
                
                speech_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
                lang_data["audio_url"] = speech_url
                
                # Update cache
                firestore_utils.cache_presentation_message(
                    lang, generated, context, course_id=course_id, audio_url=speech_url
                )
                return (lang, lang_data, None)
                
            except Exception as tts_e:
                logger.error(f"[{lang}] TTS Failed: {tts_e}")
                return (lang, lang_data, str(tts_e))

        if message_results:
            with ThreadPoolExecutor(max_workers=min(len(message_results), 5)) as executor:
                future_to_lang = {
                    executor.submit(generate_mp3_for_language, lang, data): lang 
                    for lang, data in message_results.items()
                }
                for future in as_completed(future_to_lang):
                    lang, lang_data, error = future.result()
                    
                    if lang in visual_links:
                        lang_data["slide_link"] = visual_links[lang]
                    
                    broadcast_payload["languages"][lang] = lang_data
        else:
            logger.warning("No messages generated, skipping MP3 generation.")

    # Step 3: Broadcast to Client Firestore
    if broadcast_payload.get("languages") and client_project_id:
        logger.info(f"Broadcasting to Client Project: {client_project_id}")
        try:
            broadcast_db = firestore.Client(
                project=client_project_id,
                database="(default)"
            )
            
            doc_id = course_id if course_id else 'current'
            broadcast_ref = broadcast_db.collection('presentation_broadcast').document(doc_id)
            
            ppt_fname = broadcast_payload.get('ppt_filename_norm') or broadcast_payload.get('ppt_filename')

            # Registry Update (Always happens for seeding)
            if ppt_fname and slide_number is not None:
                safe_ppt_id = ppt_fname.replace('/', '_').replace('\\', '_')

                ppt_ref = broadcast_ref.collection('presentations').document(safe_ppt_id)
                ppt_ref.set({"updated_at": firestore.SERVER_TIMESTAMP}, merge=True)

                slide_ref = broadcast_ref.collection('presentations').document(safe_ppt_id).collection('slides').document(str(slide_number))
                slide_ref.set(broadcast_payload, merge=True)
                logger.info(f"Updated registry: {safe_ppt_id} / {slide_number}")

            logger.info("✅ Registry population complete.")
            
        except Exception as e:
            logger.error(f"❌ Failed to broadcast: {e}")
    else:
        logger.warning("Skipping broadcast (no languages or no client_project_id)")


# --- DEMO DATA ---

DEMO_COURSE_ID = "showcase"
DEMO_COURSE_TITLE = "Showcase"
DEMO_LANGUAGES = ["en-US", "zh-CN", "yue-HK"]

# Mapping for visual folder suffixes
LANG_VISUAL_SUFFIX_MAP = {
    "en-US": "en",
    "zh-CN": "zh-CN",
    "yue-HK": "yue-HK"
}

# Mapping for progress files (source text)
# Looks for {basename}_{suffix}_progress.json
LANG_PROGRESS_SUFFIX_MAP = {
    "en-US": "en",
    "zh-CN": "zh-CN",
    "yue-HK": "yue-HK"
}

# -----------------

def create_demo_course():
    """Creates the demo course in Firestore using admin tools."""
    logger.info(f"Creating demo course: {DEMO_COURSE_ID}...")
    
    voice_configs = {
        "en-US": {"name": "en-US-Neural2-F", "gender": "FEMALE"},
        "zh-CN": {"name": "cmn-CN-Chirp3-HD-Achernar", "gender": "FEMALE"},
        "yue-HK": {"name": "yue-HK-Standard-A", "gender": "FEMALE"}
    }
    
    try:
        create_or_update_course(
            DEMO_COURSE_ID, 
            DEMO_COURSE_TITLE, 
            DEMO_LANGUAGES, 
            voice_configs
        )
        logger.info("✅ Course created successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to create course: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Seed Demo Class and Generate Content Locally")
    parser.add_argument("--skip-create", action="store_true", help="Skip creating the course")
    
    args = parser.parse_args()
    
    # Load infra config
    outputs = load_cdktf_outputs()
    cdktf_outputs = outputs.get("cdktf", outputs)
    
    # Extract IDs
    backend_project_id = cdktf_outputs.get("project-id")
    client_project_id = cdktf_outputs.get("client-project-id")
    bucket_name = cdktf_outputs.get("speech-file-bucket")
    
    if not backend_project_id or not client_project_id:
        logger.error("❌ Project IDs not found in cdktf_outputs.json")
        sys.exit(1)

    logger.info(f"Backend Project: {backend_project_id}")
    logger.info(f"Client Project: {client_project_id}")
    logger.info(f"Bucket: {bucket_name}")

    # Ensure we use backend project for initial setup
    os.environ["GOOGLE_CLOUD_PROJECT"] = backend_project_id

    if not args.skip_create:
        create_demo_course()
    else:
        logger.info("Skipping course creation.")
        
    # Find and process presentations
    seeds_dir = os.path.dirname(os.path.abspath(__file__))
    generate_dir = os.path.join(seeds_dir, "generate")
    
    # Find all base 'en' progress files to drive the loop
    progress_files = glob.glob(os.path.join(generate_dir, "*_en_progress.json"))
    progress_files.sort()
    
    if not progress_files:
        logger.warning(f"No *_en_progress.json files found in {generate_dir}")
        return

    for json_path in progress_files:
        logger.info(f"Found base progress file: {json_path}")
        
        # Determine Base Name
        # e.g. "cloudtech_en_progress.json" -> "cloudtech"
        filename = os.path.basename(json_path)
        base_name = filename.replace("_en_progress.json", "")
        
        # Find matching PPT
        ppt_candidates = [
            f"{base_name}_with_visuals.pptm",
            f"{base_name}_with_visuals.pptx",
            f"{base_name}_en_with_visuals.pptm" 
        ]
        
        ppt_path = None
        for cand in ppt_candidates:
            cand_path = os.path.join(generate_dir, cand)
            if os.path.exists(cand_path):
                ppt_path = cand_path
                break
        
        if not ppt_path:
            logger.warning(f"Could not find matching PPT file for {json_path}")
            # Fallback to filename if file not found locally, just for ID
            ppt_filename = f"{base_name}_with_visuals.pptm"
        else:
            ppt_filename = os.path.basename(ppt_path)
            
        ppt_basename = os.path.splitext(ppt_filename)[0]
        
        # Load Structure (from EN)
        slides_structure = load_slides_structure(json_path)
        if not slides_structure:
            continue

        # Pre-load all language notes
        # Map: { slide_index_str: { 'en-US': '...', 'zh-CN': '...' } } 
        slide_notes_map = {} 
        
        for lang in DEMO_LANGUAGES:
            suffix = LANG_PROGRESS_SUFFIX_MAP.get(lang)
            if suffix:
                # Try to find specific progress file for this language
                lang_prog_file = os.path.join(generate_dir, f"{base_name}_{suffix}_progress.json")
                if os.path.exists(lang_prog_file):
                    logger.info(f"Loading pre-generated text for {lang} from {os.path.basename(lang_prog_file)}")
                    notes = load_notes_for_language(lang_prog_file, lang)
                    for idx, text in notes.items():
                        if idx not in slide_notes_map:
                            slide_notes_map[idx] = {}
                        slide_notes_map[idx][lang] = text
                else:
                    logger.info(f"No progress file found for {lang} ({lang_prog_file})")

        # Process slides
        for slide in slides_structure:
            slide_num = slide["slide_number"]
            context = slide["context"] # Original EN notes
            
            # Get pre-generated messages for this slide
            pre_gen = slide_notes_map.get(slide_num, {})
            
            # Prepare visual links
            visual_links = {}
            if bucket_name:
                # Clean up basename for visual folder search
                # e.g. "cloudtech_en_with_visuals" -> "cloudtech"
                base_search_name = base_name
                image_filename = f"slide_{slide_num}_reimagined.png"
                
                for lang_code, suffix in LANG_VISUAL_SUFFIX_MAP.items():
                    visuals_dir_candidates = [
                        os.path.join(generate_dir, f"{base_search_name}_{suffix}_visuals"),
                        os.path.join(generate_dir, f"{base_search_name}_visuals"),
                        # Try common variations
                        os.path.join(generate_dir, f"{base_search_name}_en_visuals"), 
                    ]
                    
                    found_image = None
                    for v_dir in visuals_dir_candidates:
                        cand_p = os.path.join(v_dir, image_filename)
                        if os.path.exists(cand_p):
                            found_image = cand_p
                            break
                    
                    if found_image:
                        blob_name = f"generated_visuals/{base_search_name}/{lang_code}/{image_filename}"
                        url = upload_to_bucket(bucket_name, found_image, blob_name)
                        if url:
                            visual_links[lang_code] = url

            # Call logic locally
            process_slide_locally(
                slide_number=slide_num,
                context=context,
                ppt_filename=ppt_filename,
                course_id=DEMO_COURSE_ID,
                languages=DEMO_LANGUAGES,
                bucket_name=bucket_name,
                backend_project_id=backend_project_id,
                client_project_id=client_project_id,
                visual_links=visual_links,
                pre_generated_messages=pre_gen
            )
            
            logger.info("Waiting 1s...")
            time.sleep(1)

    # Final Step: Set Live Pointer to the first slide of the last processed presentation
    # to ensure the client app shows something immediately.
    if client_project_id and ppt_filename:
        logger.info(f"Setting live pointer to {ppt_filename} ...")
        try:
            broadcast_db = firestore.Client(
                project=client_project_id,
                database="(default)"
            )
            doc_id = DEMO_COURSE_ID
            broadcast_ref = broadcast_db.collection('presentation_broadcast').document(doc_id)
            
            # Normalize for ID (Consistency with process_slide_locally)
            safe_ppt_id = ppt_filename
            try:
                _ppt_norm = os.path.splitext(ppt_filename.lower())[0]
                for _s in ("_with_visuals", "_with_notes", "_visuals", "_en", "_zh-cn", "_yue-hk"):
                    if _ppt_norm.endswith(_s):
                        _ppt_norm = _ppt_norm[: -len(_s)]
                safe_ppt_id = _ppt_norm.replace('/', '_').replace('\\', '_')
            except:
                safe_ppt_id = ppt_filename.replace('/', '_').replace('\\', '_')

            # Find first slide number
            first_slide = "0"
            if 'slides_structure' in locals() and slides_structure:
                first_slide = str(slides_structure[0]["slide_number"])

            logger.info(f"Targeting Slide {first_slide} of {safe_ppt_id}")

            # Fetch 'latest_languages' from the registry we just populated
            # so the live view has data immediately
            slide_ref = broadcast_ref.collection('presentations').document(safe_ppt_id).collection('slides').document(first_slide)
            slide_snap = slide_ref.get()
            
            latest_languages = {}
            if slide_snap.exists:
                latest_languages = slide_snap.get("languages") or {}

            broadcast_ref.set({
                "current_presentation_id": safe_ppt_id,
                "current_slide_id": first_slide,
                "latest_languages": latest_languages,
                "updated_at": firestore.SERVER_TIMESTAMP
            }, merge=True)
            logger.info("✅ Live pointer set.")
            
        except Exception as e:
            logger.error(f"Failed to set live pointer: {e}")

if __name__ == "__main__":
    main()