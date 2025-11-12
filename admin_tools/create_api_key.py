from google.cloud import api_keys_v2
from google.cloud.api_keys_v2 import Key
from google.cloud import firestore
from config import project_id, api
import sys
import json
from datetime import datetime

def add_api_key_to_firestore(project_id: str, key: str, digital_human_id: str, key_id: str, name: str) -> None:
    db = firestore.Client(project=project_id,database="xiaoice")
    api_key_ref = db.collection('ApiKey').document(key)
    api_key_ref.set({
        'digital_human_id': digital_human_id,
        'key_id': key_id,
        'name': name
    })

def create_api_key(project_id: str, id:str,name: str) -> Key:
    """
    Creates and restrict an API key. Add the suffix for uniqueness.

    TODO(Developer):
    1. Before running this sample,
      set up ADC as described in https://cloud.google.com/docs/authentication/external/set-up-adc
    2. Make sure you have the necessary permission to create API keys.

    Args:
        project_id: Google Cloud project id.

    Returns:
        response: Returns the created API Key.
    """
    # Create the API Keys client.
    client = api_keys_v2.ApiKeysClient()

    key = api_keys_v2.Key()
    key.display_name = name

    # Initialize request and set arguments.
    request = api_keys_v2.CreateKeyRequest()
    request.parent = f"projects/{project_id}/locations/global"
    request.key = key
    request.key_id = id

    # Make the request and wait for the operation to complete.
    response = client.create_key(request=request).result()

    print(f"Successfully created an API key: {response.name}")
    # For authenticating with the API key, use the value in "response.key_string".
    # To restrict the usage of this API key, use the value in "response.name".
    return response

def restrict_api_key_api(project_id: str, service:str, key_id: str) -> Key:
    """
    Restricts an API key. Restrictions specify which APIs can be called using the API key.

    TODO(Developer): Replace the variables before running the sample.

    Args:
        project_id: Google Cloud project id.
        key_id: ID of the key to restrict. This ID is auto-created during key creation.
            This is different from the key string. To obtain the key_id,
            you can also use the lookup api: client.lookup_key()

    Returns:
        response: Returns the updated API Key.
    """

    # Create the API Keys client.
    client = api_keys_v2.ApiKeysClient()

    # Restrict the API key usage by specifying the target service and methods.
    # The API key can only be used to authenticate the specified methods in the service.
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
    # Get digital human ID and name from command line arguments
    if len(sys.argv) >= 3:
        digital_human_id = sys.argv[1]
        digital_human_name = sys.argv[2]
    else:
        print("Usage: python create_api_key.py <digital_human_id> <name>")
        print("Example: python create_api_key.py 123456789 'John Doe'")
        sys.exit(1)

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
    
    with open(filename, 'w') as f:
        json.dump(key_data, f, indent=2)
    
    print(f"\nAPI key saved to: {filename}")

