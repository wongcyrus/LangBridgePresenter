import { Construct } from "constructs";
import { GoogleFirebaseWebApp } from "../.gen/providers/google-beta/google-firebase-web-app";
import { GoogleFirebaseHostingSite } from "../.gen/providers/google-beta/google-firebase-hosting-site";
import { GoogleFirebaseProject } from "../.gen/providers/google-beta/google-firebase-project";
import { GoogleBetaProvider } from "../.gen/providers/google-beta/provider";
import { ITerraformDependable } from "cdktf";

export interface FirebaseHostingConstructProps {
    readonly project: string;
    readonly appDisplayName: string;
    readonly siteId?: string; // Optional: custom site ID, otherwise defaults to project ID usually
    readonly provider: GoogleBetaProvider;
    readonly dependsOn?: ITerraformDependable[];
}

export class FirebaseHostingConstruct extends Construct {
    public readonly firebaseProject: GoogleFirebaseProject;
    public readonly webApp: GoogleFirebaseWebApp;
    public readonly hostingSite: GoogleFirebaseHostingSite;

    constructor(scope: Construct, id: string, props: FirebaseHostingConstructProps) {
        super(scope, id);

        // Initialize Firebase on the project
        this.firebaseProject = new GoogleFirebaseProject(this, "firebase-project", {
            provider: props.provider,
            project: props.project,
            dependsOn: props.dependsOn,
        });

        // Create the Firebase Web App
        this.webApp = new GoogleFirebaseWebApp(this, "firebase-web-app", {
            provider: props.provider,
            project: props.project,
            displayName: props.appDisplayName,
            dependsOn: [this.firebaseProject, ...(props.dependsOn || [])],
        });

        // Create (or reference) the Firebase Hosting Site
        // Note: For the default site, siteId usually matches the project ID. 
        // Creating a specific one allows for custom subdomains like "my-app-staging".
        // If we want to configure the default site, we might need to import it or just use the project default.
        // Here we create a specific one or use the provided one.
        
        const siteId = props.siteId || props.project; // Default to project ID for main site

        this.hostingSite = new GoogleFirebaseHostingSite(this, "firebase-hosting-site", {
            provider: props.provider,
            project: props.project,
            siteId: siteId,
            appId: this.webApp.appId, // Link the site to the web app
            dependsOn: [this.firebaseProject, ...(props.dependsOn || [])],
        });
    }
}
