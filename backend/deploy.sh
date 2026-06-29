SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/cdktf"
npm install cdktn-cli@latest
npm i
npx cdktn get
npx cdktn deploy --auto-approve