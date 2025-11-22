cd "$(dirname "$0")/cdktf"
npm install cdktf-cli@latest
npm i
npx cdktf-cli get
npx cdktf-cli deploy --auto-approve