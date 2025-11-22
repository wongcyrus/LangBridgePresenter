pip install virtualenv
python -m venv venv
source venv/bin/activate
venv/bin/pip install -r requirements.txt

# Set the quota project for application default credentials
# Replace 'langbridge-presenter' with your actual GCP project ID
echo "Setting up Application Default Credentials quota project..."
gcloud auth application-default set-quota-project langbridge-presenter
echo "Setup complete!"