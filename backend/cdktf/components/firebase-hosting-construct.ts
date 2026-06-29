import { Construct } from "constructs";
import { GoogleFirebaseWebApp } from "../.gen/providers/google-beta/google-firebase-web-app";
import { GoogleFirebaseHostingSite } from "../.gen/providers/google-beta/google-firebase-hosting-site";
import { GoogleFirebaseProject } from "../.gen/providers/google-beta/google-firebase-project";
import { GoogleBetaProvider } from "../.gen/providers/google-beta/provider";
import { ITerraformDependable } from "cdktn";

export interface FirebaseHostingConstructProps {
    readonly project: string;
    readonly appDisplayName: string;
    readonly siteId?: string;
    readonly provider: GoogleBetaProvider;
    readonly dependsOn?: ITerraformDependable[];
}

/**
 * Construct for setting up Firebase Hosting with a web app.
 * Creates Firebase project initialization, web app, and hosting site.
 */
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
            dependsOn: [this.firebaseProject],
        });

        // Create the Firebase Hosting Site
        const siteId = props.siteId || props.project;

        this.hostingSite = new GoogleFirebaseHostingSite(this, "firebase-hosting-site", {
            provider: props.provider,
            project: props.project,
            siteId: siteId,
            appId: this.webApp.appId,
            dependsOn: [this.firebaseProject],
        });
    }
}
