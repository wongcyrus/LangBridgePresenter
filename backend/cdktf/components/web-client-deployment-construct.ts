import { Construct } from "constructs";
import { Resource } from "../.gen/providers/null/resource";
import { DataArchiveFile } from "../.gen/providers/archive/data-archive-file";
import * as path from "path";

export interface WebClientDeploymentConstructProps {
    readonly clientProjectId: string;
    readonly sourcePath: string; // Absolute path to client/web-student
    readonly firebaseApiKey: string;
    readonly firebaseWebAppAppId: string;
    readonly firebaseHostingSiteDefaultUrl: string;
    readonly dependsOn?: any[];
}

export class WebClientDeploymentConstruct extends Construct {
    constructor(scope: Construct, id: string, props: WebClientDeploymentConstructProps) {
        super(scope, id);

        // We cannot parse the App ID in TypeScript because it might be a Terraform Token.
        // Instead, we will parse it in the shell script.
        // We still construct a string for the 'triggers' so Terraform updates if any value changes.
        // Note: SENDER_ID logic is moved to the shell command.
        const triggerEnvContent = [
            `VITE_FIREBASE_API_KEY=${props.firebaseApiKey}`,
            `VITE_FIREBASE_AUTH_DOMAIN=${props.clientProjectId}.firebaseapp.com`,
            `VITE_FIREBASE_PROJECT_ID=${props.clientProjectId}`,
            `VITE_FIREBASE_STORAGE_BUCKET=${props.clientProjectId}.appspot.com`,
            `VITE_FIREBASE_APP_ID=${props.firebaseWebAppAppId}`,
            `VITE_FIREBASE_HOSTING_URL=${props.firebaseHostingSiteDefaultUrl}`
        ].join("\n");

        // Calculate hash of the source code to trigger updates.
        const sourceCodeHash = new DataArchiveFile(this, "source-code-hash", {
            type: "zip",
            sourceDir: props.sourcePath,
            outputPath: path.resolve(process.cwd(), "cdktf.out/web-student-hash.zip"),
            excludes: [
                "node_modules",
                "dist",
                ".firebase",
                "package-lock.json",
                "*.log"
            ],
        });

        // The deployment resource
        new Resource(this, "web-deploy-trigger", {
            triggers: {
                "src_hash": sourceCodeHash.outputBase64Sha256,
                "env_config": triggerEnvContent
            },
            dependsOn: props.dependsOn,
            provisioners: [
                {
                    type: "local-exec",
                    command: `
                        set -e
                        echo "Building and deploying web client..."
                        cd "${props.sourcePath}"
                        
                        # Extract Sender ID (Project Number) from App ID (1:PROJECT_NUMBER:web:APP_ID)
                        APP_ID="${props.firebaseWebAppAppId}"
                        SENDER_ID=$(echo "$APP_ID" | cut -d: -f2)

                        echo "Generating .env file..."
                        cat <<EOF > .env
VITE_FIREBASE_API_KEY=${props.firebaseApiKey}
VITE_FIREBASE_AUTH_DOMAIN=${props.clientProjectId}.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=${props.clientProjectId}
VITE_FIREBASE_STORAGE_BUCKET=${props.clientProjectId}.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=$SENDER_ID
VITE_FIREBASE_APP_ID=${props.firebaseWebAppAppId}
VITE_FIREBASE_HOSTING_URL=${props.firebaseHostingSiteDefaultUrl}
EOF

                        npm install
                        npm run build
                        firebase deploy --only hosting --project "${props.clientProjectId}"
                    `,
                }
            ]
        });
    }
}