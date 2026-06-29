import { Construct } from "constructs";
import { GoogleProjectService } from "../.gen/providers/google-beta/google-project-service";
import { ITerraformDependable } from "cdktn";

export interface ServiceEnablementConstructProps {
    readonly project: string;
    readonly services: string[];
    readonly dependsOn?: ITerraformDependable[];
}

/**
 * Reusable construct for enabling Google Cloud services on a project.
 * Centralizes service enablement logic to avoid duplication and ensures
 * consistent dependency management.
 */
export class ServiceEnablementConstruct extends Construct {
    public readonly enabledServices: GoogleProjectService[];

    constructor(scope: Construct, id: string, props: ServiceEnablementConstructProps) {
        super(scope, id);

        this.enabledServices = [];
        for (const service of props.services) {
            const svc = new GoogleProjectService(this, `${service.replace(/\./g, '-')}`, {
                project: props.project,
                service: service,
                disableOnDestroy: false,
                dependsOn: props.dependsOn,
            });
            this.enabledServices.push(svc);
        }
    }

    /**
     * Returns the list of enabled service resources for use in dependsOn chains
     */
    public getServices(): GoogleProjectService[] {
        return this.enabledServices;
    }
}
