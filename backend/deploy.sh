SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ENV_FILE="${1:-$SCRIPT_DIR/cdktf/.env.dev}"
ENV_FILE="$(realpath "$ENV_FILE")"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: env file not found: $ENV_FILE"
  exit 1
fi

export CDKTF_ENV_FILE="$ENV_FILE"

cd "$SCRIPT_DIR/cdktf"
npm install cdktn-cli@latest
npm i
npx cdktn get
npx cdktn deploy --auto-approve