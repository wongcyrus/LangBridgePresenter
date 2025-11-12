import { Construct } from "constructs";
import { GoogleProjectIamMember } from "../.gen/providers/google-beta/google-project-iam-member";
import { GoogleServiceAccount } from "../.gen/providers/google-beta/google-service-account";
import { GoogleProjectService } from "../.gen/providers/google-beta/google-project-service";
import { GoogleFirestoreDatabase } from "../.gen/providers/google-beta/google-firestore-database";

export interface FirestoreConstructProps {
    readonly project: string;
    readonly servicesAccount: GoogleServiceAccount;
}

export class FirestoreConstruct extends Construct {

    public readonly apis = [
        "firestore.googleapis.com",
    ];

    private constructor(scope: Construct, id: string, props: FirestoreConstructProps) {
        super(scope, id);
        const services = [];
        for (const api of this.apis) {
            services.push(new GoogleProjectService(this, `${api.replaceAll(".", "")}`, {
                project: props.project,
                service: api,
                disableOnDestroy: false,
            }));
        }

        // const googleFirestoreDatabase = 
        new GoogleFirestoreDatabase(this, "Firestore", {
            project: props.project,
            name: "pytestrunner",
            locationId: "nam5",
            type: "FIRESTORE_NATIVE",
            deleteProtectionState: "DELETE_PROTECTION_DISABLED",
            deletionPolicy: "DELETE",
            dependsOn: services,
        });
    }

    private async build(props: FirestoreConstructProps) {
        new GoogleProjectIamMember(this, "DatastoreProjectIamMember", {
            project: props.project,
            role: "roles/firebase.admin",
            member: "serviceAccount:" + props.servicesAccount.email,
        });
    }

    public static async create(scope: Construct, id: string, props: FirestoreConstructProps) {
        const me = new FirestoreConstruct(scope, id, props);
        await me.build(props);
        return me;
    }
}