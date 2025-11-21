import { Construct } from "constructs";
import { GoogleFirestoreDatabase } from "../.gen/providers/google-beta/google-firestore-database";
import { GoogleProjectIamMember } from "../.gen/providers/google-beta/google-project-iam-member";
import { GoogleServiceAccount } from "../.gen/providers/google-beta/google-service-account";
import { ITerraformDependable } from "cdktf";

export interface FirestoreConstructProps {
  project: string;
  servicesAccount: GoogleServiceAccount;
  dependsOn?: ITerraformDependable[];
}

export class FirestoreConstruct extends Construct {
  private firestoreDatabase: GoogleFirestoreDatabase; // Declare as a private property

  constructor(scope: Construct, id: string, props: FirestoreConstructProps) {
    super(scope, id);

    this.firestoreDatabase = new GoogleFirestoreDatabase(this, "firestore-database", {
      project: props.project,
      name: "langbridge",
      locationId: "nam5",
      type: "FIRESTORE_NATIVE",
      deletionPolicy: "DELETE",
      dependsOn: props.dependsOn,
    });

    new GoogleProjectIamMember(this, "firestore-iam-member", {
      project: props.project,
      role: "roles/datastore.owner",
      member: `serviceAccount:${props.servicesAccount.email}`,
      dependsOn: [this.firestoreDatabase], // Refer to the class property
    });
  }

  public static create(scope: Construct, id: string, props: FirestoreConstructProps) {
    return new FirestoreConstruct(scope, id, props);
  }
}
