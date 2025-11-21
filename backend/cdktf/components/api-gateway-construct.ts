import { Construct } from "constructs";
import { GoogleApiGatewayApi } from "../.gen/providers/google-beta/google-api-gateway-api";
import { GoogleApiGatewayApiConfigA } from "../.gen/providers/google-beta/google-api-gateway-api-config";
import { GoogleApiGatewayGateway } from "../.gen/providers/google-beta/google-api-gateway-gateway";
import { GoogleBetaProvider } from "../.gen/providers/google-beta/provider";
import { GoogleServiceAccount } from "../.gen/providers/google-beta/google-service-account";
import path = require("path");
import { Fn, ITerraformDependable } from "cdktf";

export interface ApigatewayConstructProps {
    readonly api: string;
    readonly project: string;
    readonly provider: GoogleBetaProvider;
    readonly replaces: { [key: string]: string };
    readonly servicesAccount: GoogleServiceAccount;
    readonly dependsOn?: ITerraformDependable[];
}

export class ApigatewayConstruct extends Construct {
    public apiGatewayApi!: GoogleApiGatewayApi;
    public apiGatewayApiConfig!: GoogleApiGatewayApiConfigA;
    public gateway!: GoogleApiGatewayGateway;

    private constructor(scope: Construct, id: string) {
        super(scope, id);
    }

    private async build(props: ApigatewayConstructProps) {
        this.apiGatewayApi = new GoogleApiGatewayApi(this, "api", {
            provider: props.provider,
            apiId: props.api,
            project: props.project,
            displayName: props.api,
            dependsOn: props.dependsOn,
        });

        this.apiGatewayApiConfig = new GoogleApiGatewayApiConfigA(this, "apiConfig", {
            provider: props.provider,
            api: this.apiGatewayApi.apiId,
            project: props.project,
            openapiDocuments: [
                {
                    document: {
                        path: "spec.yaml",
                        contents: Fn.base64encode(
                            Fn.templatefile(
                                path.resolve(__dirname, "spec.yaml"),
                                props.replaces
                            )
                        ),
                    },
                },
            ],
            gatewayConfig: {
                backendConfig: {
                    googleServiceAccount: props.servicesAccount.email,
                },
            },
            dependsOn: props.dependsOn ? [this.apiGatewayApi, ...props.dependsOn] : [this.apiGatewayApi],
        });

        this.gateway = new GoogleApiGatewayGateway(this, "gateway", {
            provider: props.provider,
            gatewayId: "gateway",
            project: props.project,
            apiConfig: this.apiGatewayApiConfig.id,
            displayName: "langbridge-presenter-gateway",
            region: "us-east1", // hardcoded for now as it's limited availability
            dependsOn: props.dependsOn ? [this.apiGatewayApiConfig, ...props.dependsOn] : [this.apiGatewayApiConfig],
        });
    }

    public static async create(scope: Construct, id: string, props: ApigatewayConstructProps) {
        const me = new ApigatewayConstruct(scope, id);
        await me.build(props);
        return me;
    }
}