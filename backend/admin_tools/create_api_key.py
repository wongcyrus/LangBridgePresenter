from google.cloud import api_keys_v2
from google.cloud.api_keys_v2 import Key
from google.cloud import firestore
import sys
import json
import argparse
import os
from datetime import datetime
try:
    from runtime_config import default_project_id, default_api_service
except ModuleNotFoundError:
    from backend.admin_tools.runtime_config import default_project_id, default_api_service


def add_api_key_to_firestore(
    project_id: str,
    key: str,
    digital_human_id: str,
    key_id: str,
    name: str
) -> None:
    db_name = (os.environ.get("FIRESTORE_DATABASE") or "").strip()
    if not db_name:
        raise RuntimeError("FIRESTORE_DATABASE is not configured.")
    db = firestore.Client(project=project_id, database=db_name)
    api_key_ref = db.collection('ApiKey').document(key)
    api_key_ref.set({
        'digital_human_id': digital_human_id,
        'key_id': key_id,
        'name': name
    })


def create_api_key(project_id: str, key_id: str, name: str) -> Key:
    """
    Creates and restricts an API key for the specified project.
    
    Prerequisites:
    1. Set up Application Default Credentials (ADC) as described in:
       https://cloud.google.com/docs/authentication/external/set-up-adc
    2. Ensure you have the necessary permissions to create API keys.

    Args:
        project_id: Google Cloud project id.
        key_id: Unique identifier for the API key.
        name: Display name for the API key.

    Returns:
        response: The created API Key object.
    """
    # Create the API Keys client.
    client = api_keys_v2.ApiKeysClient()

    key = api_keys_v2.Key()
    key.display_name = name

    # Initialize request and set arguments.
    request = api_keys_v2.CreateKeyRequest()
    request.parent = f"projects/{project_id}/locations/global"
    request.key = key
    request.key_id = key_id

    # Make the request and wait for the operation to complete.
    response = client.create_key(request=request).result()

    print(f"Successfully created an API key: {response.name}")
    # For authenticating with the API key, use the value in
    # "response.key_string".
    # To restrict the usage of this API key, use "response.name".
    return response


def restrict_api_key_api(project_id: str, service: str, key_id: str) -> Key:
    """
    Restricts an API key to specific APIs and services.

    Args:
        project_id: Google Cloud project id.
        service: The service to restrict the API key to.
        key_id: ID of the key to restrict. This ID is auto-created
            during key creation. This is different from the key string.
            To obtain the key_id, you can use: client.lookup_key()

    Returns:
        response: The updated API Key object.
    """

    # Create the API Keys client.
    client = api_keys_v2.ApiKeysClient()

    # Restrict the API key usage by specifying the target service
    # and methods. The API key can only be used to authenticate
    # the specified methods in the service.
    api_target = api_keys_v2.ApiTarget()
    api_target.service = service
    api_target.methods = ["*"]

    # Set the API restriction(s).
    # For more information on API key restriction, see:
    # https://cloud.google.com/docs/authentication/api-keys
    restrictions = api_keys_v2.Restrictions()
    restrictions.api_targets = [api_target]

    key = api_keys_v2.Key()
    key.name = f"projects/{project_id}/locations/global/keys/{key_id}"
    key.restrictions = restrictions

    # Initialize request and set arguments.
    request = api_keys_v2.UpdateKeyRequest()
    request.key = key
    request.update_mask = "restrictions"

    # Make the request and wait for the operation to complete.
    response = client.update_key(request=request).result()

    # Use response.key_string to authenticate.
    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create and register API key")
    parser.add_argument("digital_human_id", help="Digital human ID")
    parser.add_argument("name", help="Digital human display name")
    parser.add_argument("--project-id", required=True, help="Target GCP project")
    parser.add_argument("--api-service", required=True, help="API service name")
    parser.add_argument("--database", default="langbridge", help="Firestore database")
    args = parser.parse_args()

    os.environ["ADMIN_TOOLS_PROJECT_ID"] = args.project_id
    os.environ["ADMIN_TOOLS_API_SERVICE"] = args.api_service
    os.environ["FIRESTORE_DATABASE"] = args.database

    project_id = default_project_id()
    api = default_api_service()
    digital_human_id = args.digital_human_id
    digital_human_name = args.name

    # Create the API key
    print(f"Creating API key for digital human: {digital_human_id}")
    key = create_api_key(
        project_id, f"digital-human-{digital_human_id}", digital_human_name
    )

    # Restrict the API key
    response = restrict_api_key_api(project_id, api, key.uid)

    # Add to Firestore
    add_api_key_to_firestore(
        project_id,
        key.key_string,
        digital_human_id,
        key.uid,
        digital_human_name
    )

    print("\nAPI Key created successfully!")
    print(f"Key ID: {key.uid}")
    print(f"Key String: {key.key_string}")
    print(f"Digital Human ID: {digital_human_id}")
    print(f"Digital Human Name: {digital_human_name}")

    # Save key to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"api_key_{digital_human_id}_{timestamp}.json"
    
    key_data = {
        "digital_human_id": digital_human_id,
        "digital_human_name": digital_human_name,
        "key_id": key.uid,
        "key_string": key.key_string,
        "created_at": timestamp,
        "project_id": project_id
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(key_data, f, indent=2)
    
    print(f"\nAPI key saved to: {filename}")
