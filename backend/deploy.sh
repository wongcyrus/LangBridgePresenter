cd "$(dirname "$0")/cdktf"
npm install cdktf-cli@latest
npm i
npx cdktf-cli get
npx cdktf-cli deploy --auto-approve

# Update configuration files from Terraform outputs
echo "Updating configuration files..."
if [ -f "../admin_tools/update_config_from_cdktf.sh" ]; then
    bash "../admin_tools/update_config_from_cdktf.sh"
else
    echo "Warning: update_config_from_cdktf.sh not found."
fi