import { Construct } from "constructs";
import { App, TerraformOutput, TerraformStack } from "cdktf";
import { ArchiveProvider } from "./.gen/providers/archive/provider";
import { RandomProvider } from "./.gen/providers/random/provider";
import { DataGoogleBillingAccount } from "./.gen/providers/google-beta/data-google-billing-account";
import { GoogleBetaProvider } from "./.gen/providers/google-beta/provider/index";
import { GoogleProject } from "./.gen/providers/google-beta/google-project";
import { CloudFunctionDeploymentConstruct } from "./components/cloud-function-deployment-construct";
import { CloudFunctionConstruct } from "./components/cloud-function-construct";
import { ApigatewayConstruct } from "./components/api-gateway-construct";
import { GoogleProjectIamMember } from "./.gen/providers/google-beta/google-project-iam-member";
import * as dotenv from 'dotenv';
import { FirestoreConstruct } from "./components/firestore-construct";

dotenv.config();

class XiaoiceApiStack extends TerraformStack {
  constructor(scope: Construct, id: string) {
    super(scope, id);
  }

  async buildXiaoiceApiStack() {
    const projectId = process.env.PROJECTID!;

    const googleBetaProvider = new GoogleBetaProvider(this, "google", {
      region: process.env.REGION!,
    });
    const archiveProvider = new ArchiveProvider(this, "archive", {});
    const randomProvider = new RandomProvider(this, "random", {});

    const billingAccount = new DataGoogleBillingAccount(this, "billing-account", {
      billingAccount: process.env.BILLING_ACCOUNT!,
    });

    const project = new GoogleProject(this, "project", {
      projectId: projectId,
      name: projectId,
      billingAccount: billingAccount.id,
      deletionPolicy: "DELETE",
    });



    const cloudFunctionDeploymentConstruct = new CloudFunctionDeploymentConstruct(this, "cloud-function-deployment", {
      project: project.projectId,
      region: process.env.REGION!,
      archiveProvider: archiveProvider,
      randomProvider: randomProvider,
    });

    const artifactRegistryIamMember = new GoogleProjectIamMember(this, "cloud-functions-artifact-registry-reader", {
      project: projectId,
      role: "roles/artifactregistry.reader",
      member: `serviceAccount:service-${project.number}@gcf-admin-robot.iam.gserviceaccount.com`,
      dependsOn: cloudFunctionDeploymentConstruct.services,
    });

    const talkStreamFunction = await CloudFunctionConstruct.create(this, "talkStreamFunction", {
      functionName: "talk-stream",
      runtime: "python311",
      entryPoint: "talk_stream",
      timeout: 600,
      availableMemory: "512Mi",
      makePublic: false,
      cloudFunctionDeploymentConstruct: cloudFunctionDeploymentConstruct,
      additionalDependencies: [artifactRegistryIamMember],
    });

    const welcomeFunction = await CloudFunctionConstruct.create(this, "welcomeFunction", {
      functionName: "welcome",
      runtime: "python311",
      entryPoint: "welcome",
      timeout: 60,
      availableMemory: "256Mi",
      makePublic: false,
      cloudFunctionDeploymentConstruct: cloudFunctionDeploymentConstruct,
      serviceAccount: talkStreamFunction.serviceAccount,
      additionalDependencies: [artifactRegistryIamMember],
    });

    const goodbyeFunction = await CloudFunctionConstruct.create(this, "goodbyeFunction", {
      functionName: "goodbye",
      runtime: "python311",
      entryPoint: "goodbye",
      timeout: 60,
      availableMemory: "256Mi",
      makePublic: false,
      cloudFunctionDeploymentConstruct: cloudFunctionDeploymentConstruct,
      serviceAccount: talkStreamFunction.serviceAccount,
      additionalDependencies: [artifactRegistryIamMember],
    });

    const recquestionsFunction = await CloudFunctionConstruct.create(this, "recquestionsFunction", {
      functionName: "recquestions",
      runtime: "python311",
      entryPoint: "recquestions",
      timeout: 60,
      availableMemory: "256Mi",
      makePublic: false,
      cloudFunctionDeploymentConstruct: cloudFunctionDeploymentConstruct,
      serviceAccount: talkStreamFunction.serviceAccount,
      additionalDependencies: [artifactRegistryIamMember],
    });

    const apigatewayConstruct = await ApigatewayConstruct.create(this, "api-gateway", {
      api: "xiaoiceapi",
      project: project.projectId,
      provider: googleBetaProvider,
      replaces: {
        "TALK_STREAM": talkStreamFunction.cloudFunction.url,
        "WELCOME": welcomeFunction.cloudFunction.url,
        "GOODBYE": goodbyeFunction.cloudFunction.url,
        "RECQUESTIONS": recquestionsFunction.cloudFunction.url
      },
      servicesAccount: talkStreamFunction.serviceAccount,
    });

    FirestoreConstruct.create(this, "firestore", {
      project: project.projectId,
      servicesAccount: talkStreamFunction.serviceAccount
    });

    new TerraformOutput(this, "project-id", {
      value: project.projectId,
    });

    new TerraformOutput(this, "api-url", {
      value: apigatewayConstruct.gateway.defaultHostname,
    });

    new TerraformOutput(this, "api-service-name", {
      value: apigatewayConstruct.apiGatewayApi.managedService,
    });
  }
}

async function buildStack(scope: Construct, id: string) {
  const stack = new XiaoiceApiStack(scope, id);
  await stack.buildXiaoiceApiStack();
}

async function createApp(): Promise<App> {
  const app = new App();
  await buildStack(app, "cdktf");
  return app;
}

createApp().then((app) => app.synth());
