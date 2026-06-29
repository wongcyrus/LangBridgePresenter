import { Construct } from "constructs";
import { GoogleProjectIamMember } from "../.gen/providers/google-beta/google-project-iam-member";
import { GoogleStorageBucketIamMember } from "../.gen/providers/google-beta/google-storage-bucket-iam-member";
import { ITerraformDependable } from "cdktn";

export interface ProjectIamRoleProps {
    readonly project: string;
    readonly role: string;
    readonly member: string;
    readonly dependsOn?: ITerraformDependable[];
}

export interface StorageBucketIamRoleProps {
    readonly bucket: string;
    readonly role: string;
    readonly member: string;
    readonly dependsOn?: ITerraformDependable[];
}

/**
 * Reusable construct for managing IAM role bindings.
 * Provides consistent interface for granting roles on projects and storage buckets.
 */
export class IamRoleConstruct {
    private constructor() {
        // Static utility class - no instantiation
    }

    /**
     * Create an IAM role binding for a project
     */
    public static createProjectRole(
        scope: Construct,
        id: string,
        props: ProjectIamRoleProps
    ): GoogleProjectIamMember {
        return new GoogleProjectIamMember(scope, id, {
            project: props.project,
            role: props.role,
            member: props.member,
            dependsOn: props.dependsOn,
        });
    }

    /**
     * Create an IAM role binding for a storage bucket
     */
    public static createStorageBucketRole(
        scope: Construct,
        id: string,
        props: StorageBucketIamRoleProps
    ): GoogleStorageBucketIamMember {
        return new GoogleStorageBucketIamMember(scope, id, {
            bucket: props.bucket,
            role: props.role,
            member: props.member,
            dependsOn: props.dependsOn,
        });
    }

    /**
     * Grant multiple project roles to the same member at once
     */
    public static grantProjectRoles(
        scope: Construct,
        idPrefix: string,
        project: string,
        member: string,
        roles: string[],
        dependsOn?: ITerraformDependable[]
    ): GoogleProjectIamMember[] {
        return roles.map((role, index) =>
            IamRoleConstruct.createProjectRole(scope, `${idPrefix}-${index}`, {
                project,
                role,
                member,
                dependsOn,
            })
        );
    }
}
