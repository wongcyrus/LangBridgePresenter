# Deployment Guide

This guide covers the complete deployment process for the LangBridge Presenter system, including the serverless backend (Google Cloud Platform) and the student web client (Firebase Hosting).

## Overview

The system uses **Terraform** (via CDKTF) as the Infrastructure-as-Code tool to provision all resources. A unified deployment script `deploy.sh` is provided to orchestrate the process.

**What gets deployed:**
1.  **Google Cloud Infrastructure**:
    *   Cloud Functions (2nd Gen)
    *   API Gateway & Config
    *   Firestore Database
    *   Cloud Storage Buckets
    *   IAM Roles & Service Accounts
2.  **Firebase Resources**:
    *   Firebase Project configuration
    *   Firebase Hosting site
    *   Web App registration
3.  **Web Client**:
    *   Builds the React application (`client/web-student`)
    *   Deploys static assets to Firebase Hosting

## Deployment Flow Diagram

```mermaid
flowchart TD
    A[Run ./deploy.sh] --> B[Load backend/cdktf/.env]
    B --> C[cdktf deploy]
    C --> D[Provision GCP resources<br/>Functions, Gateway, Firestore, Storage, IAM]
    C --> E[Deploy web client to Firebase Hosting]
    D --> F[Generate cdktf outputs]
    F --> G[Sync local configs]
    G --> H[backend/admin_tools/config.py]
    G --> I[backend/presentation-preloader/config.py]
    G --> J[backend/tests/.env.test]
    G --> K[client/web-student/.env]
```

## Prerequisites

Before running the deployment, ensure you have the following installed and authenticated:

1.  **Google Cloud CLI (`gcloud`)**:
    *   Install: [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
    *   Login: `gcloud auth login`
    *   Set Project: `gcloud config set project <YOUR_PROJECT_ID>`
    *   Auth defaults: `gcloud auth application-default login`

2.  **Firebase CLI**:
    *   Install: `npm install -g firebase-tools`
    *   Login: `firebase login`

3.  **Node.js & npm**:
    *   Required for CDKTF and the Web Client build.
    *   Version 18+ recommended.

4.  **Python 3.11+**:
    *   Required for backend scripts and tests.

## Configuration

The system uses a **single source of truth** for configuration: the `.env` file located in `backend/cdktf/.env`.

1.  Navigate to `backend/cdktf/`.
2.  Copy the template:
    ```bash
    cp .env.template .env
    ```
3.  Edit `.env` with your specific values:
    ```env
    PROJECTID=your-google-cloud-project-id
    BILLING_ACCOUNT=your-billing-account-id
    REGION=us-east1
    
    # API Keys for the AI Service (e.g., Xiaoice / Azure OpenAI)
    XIAOICE_CHAT_SECRET_KEY=your_secret_key
    XIAOICE_CHAT_ACCESS_KEY=your_access_key
    ```

**Important:** This `.env` file drives both the infrastructure provisioning and the runtime configuration of the backend and frontend.

## One-Step Deployment

From the root of the project (`xiaoice_class_assistant/`), run the unified deployment script:

```bash
./deploy.sh
```

### What this script does:

1.  **Deploys Infrastructure**: Runs `npx cdktf deploy` to provision GCP resources.
    *   *Note: This step includes a `local-exec` provisioner that automatically builds and deploys the web client to Firebase Hosting.*
2.  **Syncs Configuration**:
    *   Extracts outputs (API Gateway URL, Bucket names, Keys) from the Terraform state.
    *   Updates `backend/admin_tools/config.py`.
    *   Updates `backend/presentation-preloader/config.py`.
    *   Generates `backend/tests/.env.test` for integration testing.
    *   Generates `client/web-student/.env` for local frontend development.

## Verification

After deployment, the script will output key information. You can verify the deployment by:

1.  **Checking the Web Client**:
    *   Visit the hosting URL provided in the output (e.g., `https://<your-project>.web.app`).
    *   You should see the student interface.

2.  **Running Integration Tests**:
    ```bash
    cd backend/tests
    ./run_tests.sh
    ```
    All tests should pass if the environment is correctly configured.

## Troubleshooting

### "Error: backend/cdktf/.env not found"
*   Ensure you have created the `.env` file in `backend/cdktf/` as described in the Configuration section.

### Permission Errors
*   Ensure your `gcloud` user has the `Owner` or `Editor` role on the GCP project.
*   Ensure the `Cloud Resource Manager API` is enabled on your project.

### Firebase Deploy Failures
*   If the web client deployment fails during the Terraform run, check that you are logged into Firebase (`firebase login`).
*   You can manually retry the web client deployment (after infrastructure is up) by navigating to `client/web-student` and running `npm run build && firebase deploy`.

## Multi-Machine Workflow (Dev/Test)

If you need to run development or tests on a machine **different** from the one where you deployed the infrastructure:

1.  **On the Deployment Machine**:
    *   Run `./deploy.sh`.
    *   Locate the generated file: `backend/cdktf_outputs.json`.
    *   Securely copy this file to the `backend/` directory on your Dev/Test machine.

2.  **On the Dev/Test Machine**:
    *   Ensure the repository is cloned.
    *   Place `cdktf_outputs.json` inside `backend/`.
    *   (Optional) If you need access to the secret keys (`XIAOICE_CHAT_SECRET_KEY`), either:
        *   Create a `.env` file in `backend/cdktf/` with those keys.
        *   **OR** export them as environment variables in your shell.
    *   Run the sync script manually:
        ```bash
        python3 backend/sync_config.py
        ```
    *   This will configure your local environment (`tests/.env.test`, `client/web-student/.env`, etc.) using the deployment outputs from the other machine.

```mermaid
flowchart LR
    A[Deployment machine] -->|Run ./deploy.sh| B[backend/cdktf_outputs.json]
    B -->|Secure copy| C[Dev/Test machine backend/cdktf_outputs.json]
    C -->|Run python3 backend/sync_config.py| D[Local env files synced]
```
