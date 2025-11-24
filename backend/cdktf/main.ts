import { Construct } from "constructs";
import { App, TerraformOutput, TerraformStack } from "cdktf";
import { ArchiveProvider } from "./.gen/providers/archive/provider";
import { RandomProvider } from "./.gen/providers/random/provider";
import { StringResource } from "./.gen/providers/random/string-resource";
import { DataGoogleBillingAccount } from "./.gen/providers/google-beta/data-google-billing-account";
import { GoogleBetaProvider } from "./.gen/providers/google-beta/provider/index";
import { GoogleProject } from "./.gen/providers/google-beta/google-project";
import { GoogleProjectService } from "./.gen/providers/google-beta/google-project-service";
import { CloudFunctionDeploymentConstruct } from "./components/cloud-function-deployment-construct";
import { CloudFunctionConstruct } from "./components/cloud-function-construct";
import { ApigatewayConstruct } from "./components/api-gateway-construct";
import * as dotenv from 'dotenv';
import { FirestoreConstruct } from "./components/firestore-construct";
import { GoogleStorageBucket } from "./.gen/providers/google-beta/google-storage-bucket";
import { FirebaseHostingConstruct } from "./components/firebase-hosting-construct";
import { ServiceEnablementConstruct } from "./components/service-enablement-construct";
import { IamRoleConstruct } from "./components/iam-role-construct";
import { DataGoogleFirebaseWebAppConfigA } from "./.gen/providers/google-beta/data-google-firebase-web-app-config";

import { WebClientDeploymentConstruct } from "./components/web-client-deployment-construct";
import * as path from "path";
import { NullProvider } from "./.gen/providers/null/provider";

import { TimeProvider } from "./.gen/providers/time/provider";
import { Sleep } from "./.gen/providers/time/sleep";

dotenv.config();

class LangBridgeApiStack extends TerraformStack {
  constructor(scope: Construct, id: string) {
    super(scope, id);
  }

  async buildLangBridgeApiStack() {
    const projectId = process.env.PROJECTID!;
    const clientProjectId = `${projectId}-client`;

    const googleBetaProvider = new GoogleBetaProvider(this, "google", {
      region: process.env.REGION!,
    });
    new TimeProvider(this, "time", {});
    const archiveProvider = new ArchiveProvider(this, "archive", {});
    const randomProvider = new RandomProvider(this, "random", {});
    new NullProvider(this, "null", {});

    const billingAccount = new DataGoogleBillingAccount(this, "billing-account", {
      billingAccount: process.env.BILLING_ACCOUNT!,
    });

    const project = new GoogleProject(this, "project", {
      projectId: projectId,
      name: projectId,
      billingAccount: billingAccount.id,
      deletionPolicy: "DELETE",
    });

    // Create the client project for Firebase Hosting and Firestore
    const clientProject = new GoogleProject(this, "client-project", {
      projectId: clientProjectId,
      name: clientProjectId,
      billingAccount: billingAccount.id,
      deletionPolicy: "DELETE",
    });

    // Enable necessary Google Cloud Platform APIs using reusable construct
    const backendServices = new ServiceEnablementConstruct(this, "backend-services", {
      project: project.projectId,
      services: [
        "cloudresourcemanager.googleapis.com",
        "serviceusage.googleapis.com",
        "compute.googleapis.com",
        "cloudfunctions.googleapis.com",
        "cloudbuild.googleapis.com",
        "artifactregistry.googleapis.com",
        "datastore.googleapis.com",
        "firebaserules.googleapis.com",
        "firebase.googleapis.com",
        "firestore.googleapis.com",
        "apigateway.googleapis.com",
        "servicemanagement.googleapis.com",
        "servicecontrol.googleapis.com",
        "iam.googleapis.com",
        "aiplatform.googleapis.com",
        "run.googleapis.com",
        "storage-api.googleapis.com",
        "storage-component.googleapis.com",
        "eventarc.googleapis.com",
        "secretmanager.googleapis.com",
        "logging.googleapis.com",
        "texttospeech.googleapis.com",
      ],
      dependsOn: [project],
    });

    // Enable services for the client project (Firebase Hosting, Firestore)
    const clientServices = new ServiceEnablementConstruct(this, "client-services", {
      project: clientProject.projectId,
      services: [
        "firebase.googleapis.com",
        "firebasehosting.googleapis.com",
        "firestore.googleapis.com",
        "datastore.googleapis.com",
        "firebaserules.googleapis.com",
      ],
      dependsOn: [clientProject],
    });

    // Wait for APIs to fully propagate
    const timeSleep = new Sleep(this, "wait_for_apis", {
      createDuration: "30s",
      dependsOn: backendServices.enabledServices,
    });
    const clientTimeSleep = new Sleep(this, "wait_for_client_apis", {
      createDuration: "30s",
      dependsOn: clientServices.enabledServices,
    });

    const cloudFunctionDeploymentConstruct = new CloudFunctionDeploymentConstruct(this, "cloud-function-deployment", {
      project: project.projectId,
      randomProvider: randomProvider,
      archiveProvider: archiveProvider,
      region: process.env.REGION!,
    });
    // Ensure APIs are enabled before deployment resources
    cloudFunctionDeploymentConstruct.node.addDependency(timeSleep);

    const speechBucketSuffix = new StringResource(this, "speechFileBucketSuffix", {
      length: 9,
      special: false,
      upper: false,
    });

    const speechFileBucket = new GoogleStorageBucket(this, "speechFileBucket", {
      name: "speechfile" + speechBucketSuffix.result,
      project: project.projectId,
      location: process.env.REGION!,
      storageClass: "REGIONAL",
      forceDestroy: true,
      uniformBucketLevelAccess: true,
      dependsOn: [timeSleep],
    });

    const artifactRegistryIamMember = IamRoleConstruct.createProjectRole(this, "cloud-functions-artifact-registry-reader", {
      project: projectId,
      role: "roles/artifactregistry.reader",
      member: `serviceAccount:service-${project.number}@gcf-admin-robot.iam.gserviceaccount.com`,
      dependsOn: [timeSleep],
    });

    const talkStreamFunction = await CloudFunctionConstruct.create(this, "talkStreamFunction", {
      functionName: "talk-stream",
      runtime: "python311",
      entryPoint: "talk_stream",
      timeout: 1200,
      availableCpu: "2",
      availableMemory: "2048Mi",
      makePublic: false,
      cloudFunctionDeploymentConstruct: cloudFunctionDeploymentConstruct,
      environmentVariables: {
        "XIAOICE_CHAT_SECRET_KEY": process.env.XIAOICE_CHAT_SECRET_KEY || "default_secret_key",
        "XIAOICE_CHAT_ACCESS_KEY": process.env.XIAOICE_CHAT_ACCESS_KEY || "default_access_key",
        "GOOGLE_CLOUD_PROJECT": projectId,
        "GOOGLE_CLOUD_LOCATION": "global",
        "GOOGLE_GENAI_USE_VERTEXAI": "True"
      },
      additionalDependencies: [artifactRegistryIamMember],
    });

    // Grant AI Platform (Vertex AI) user role to the service account for Gemini API access
    const aiPlatformIamMember = IamRoleConstruct.createProjectRole(this, "ai-platform-user", {
      project: projectId,
      role: "roles/aiplatform.user",
      member: `serviceAccount:${talkStreamFunction.serviceAccount.email}`,
      dependsOn: [timeSleep],
    });

    // Allow writing to the client's Firestore project (xiaoice-class-assistant)
    // The configFunction needs this to broadcast presentation updates to the client Firestore
    IamRoleConstruct.createProjectRole(this, "cross-project-firestore-writer", {
      project: clientProjectId,
      role: "roles/datastore.user",
      member: `serviceAccount:${talkStreamFunction.serviceAccount.email}`,
      dependsOn: [clientTimeSleep],
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
      environmentVariables: {
        "XIAOICE_CHAT_SECRET_KEY": process.env.XIAOICE_CHAT_SECRET_KEY || "default_secret_key",
        "XIAOICE_CHAT_ACCESS_KEY": process.env.XIAOICE_CHAT_ACCESS_KEY || "default_access_key",
      },
      additionalDependencies: [artifactRegistryIamMember, aiPlatformIamMember],
    });
    const speechFunction = await CloudFunctionConstruct.create(this, "speechFunction", {
      functionName: "speech",
      runtime: "python311",
      entryPoint: "speech",
      timeout: 60,
      availableMemory: "256Mi",
      makePublic: false,
      cloudFunctionDeploymentConstruct: cloudFunctionDeploymentConstruct,
      serviceAccount: talkStreamFunction.serviceAccount,
      environmentVariables: {
        "XIAOICE_CHAT_SECRET_KEY": process.env.XIAOICE_CHAT_SECRET_KEY || "default_secret_key",
        "XIAOICE_CHAT_ACCESS_KEY": process.env.XIAOICE_CHAT_ACCESS_KEY || "default_access_key",
        "SPEECH_FILE_BUCKET": speechFileBucket.name,
      },
      additionalDependencies: [artifactRegistryIamMember, aiPlatformIamMember],
    });
    // Grant storage.objectAdmin to speech function service account for bucket access
    IamRoleConstruct.createProjectRole(this, "speech-bucket-object-admin", {
      project: projectId,
      role: "roles/storage.objectAdmin",
      member: `serviceAccount:${talkStreamFunction.serviceAccount.email}`,
      dependsOn: [timeSleep],
    });
    
    // Public read access for speech bucket (serving MP3 directly)
    IamRoleConstruct.createStorageBucketRole(this, "speech-bucket-public-read", {
      bucket: speechFileBucket.name,
      role: "roles/storage.objectViewer",
      member: "allUsers",
      dependsOn: [speechFileBucket, timeSleep],
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
      environmentVariables: {
        "XIAOICE_CHAT_SECRET_KEY": process.env.XIAOICE_CHAT_SECRET_KEY || "default_secret_key",
        "XIAOICE_CHAT_ACCESS_KEY": process.env.XIAOICE_CHAT_ACCESS_KEY || "default_access_key",
      },
      additionalDependencies: [artifactRegistryIamMember, aiPlatformIamMember],
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
      environmentVariables: {
        "XIAOICE_CHAT_SECRET_KEY": process.env.XIAOICE_CHAT_SECRET_KEY || "default_secret_key",
        "XIAOICE_CHAT_ACCESS_KEY": process.env.XIAOICE_CHAT_ACCESS_KEY || "default_access_key",
      },
      additionalDependencies: [artifactRegistryIamMember, aiPlatformIamMember],
    });

    const configFunction = await CloudFunctionConstruct.create(this, "configFunction", {
      functionName: "config",
      runtime: "python311",
      entryPoint: "config",
      timeout: 1200,
      availableCpu: "2",
      availableMemory: "2048Mi",
      makePublic: false,
      cloudFunctionDeploymentConstruct: cloudFunctionDeploymentConstruct,
      serviceAccount: talkStreamFunction.serviceAccount,
      environmentVariables: {
        "GOOGLE_CLOUD_PROJECT": projectId,
        "GOOGLE_CLOUD_LOCATION": "global",
        "GOOGLE_GENAI_USE_VERTEXAI": "True",
        "SPEECH_FILE_BUCKET": speechFileBucket.name,
        "CLIENT_FIRESTORE_PROJECT_ID": clientProjectId,
        "CLIENT_FIRESTORE_DATABASE_ID": "(default)",
      },
      additionalDependencies: [artifactRegistryIamMember, aiPlatformIamMember],
    });

    const apigatewayConstruct = await ApigatewayConstruct.create(this, "api-gateway", {
      api: "langbridgeapi",
      project: project.projectId,
      provider: googleBetaProvider,
      replaces: {
        "TALK_STREAM": talkStreamFunction.cloudFunction.url,
        "WELCOME": welcomeFunction.cloudFunction.url,
        "SPEECH": speechFunction.cloudFunction.url,
        "GOODBYE": goodbyeFunction.cloudFunction.url,
        "RECQUESTIONS": recquestionsFunction.cloudFunction.url,
        "CONFIG": configFunction.cloudFunction.url
      },
      servicesAccount: talkStreamFunction.serviceAccount,
      dependsOn: [timeSleep],
    });

    // Enable the API Gateway's managed service (this is the actual API endpoint)
    // The managed service name is dynamically generated by the API Gateway
    new GoogleProjectService(this, "api-gateway-managed-service", {
      project: project.projectId,
      service: apigatewayConstruct.apiGatewayApi.managedService,
      disableOnDestroy: false,
      dependsOn: [apigatewayConstruct.apiGatewayApi],
    });

    // Explicitly enable Firestore API with a direct dependency
    // This ensures Firestore API is enabled before attempting to create the database
    const firestoreApiService = new GoogleProjectService(this, "firestore-api-explicit", {
      project: project.projectId,
      service: "firestore.googleapis.com",
      disableOnDestroy: false,
      dependsOn: [timeSleep],
    });

    FirestoreConstruct.create(this, "firestore", {
      project: project.projectId,
      servicesAccount: talkStreamFunction.serviceAccount,
      dependsOn: [firestoreApiService],
    });

    const firebaseHosting = new FirebaseHostingConstruct(this, "firebase-hosting", {
        project: clientProjectId,
        appDisplayName: "LangBridge Student Web",
        siteId: clientProjectId,
        provider: googleBetaProvider,
        dependsOn: [clientTimeSleep],
    });

    // Retrieve Firebase web app config (includes generated API key)
    const firebaseWebAppConfig = new DataGoogleFirebaseWebAppConfigA(this, "firebase-web-app-config", {
      project: clientProjectId,
      webAppId: firebaseHosting.webApp.appId,
      provider: googleBetaProvider,
      dependsOn: [firebaseHosting.webApp]
    });

    // Deploy the web client code using auto-generated Firebase API key
    new WebClientDeploymentConstruct(this, "web-client-deploy", {
        clientProjectId: clientProjectId,
        sourcePath: path.resolve(__dirname, "../../client/web-student"),
        firebaseApiKey: firebaseWebAppConfig.apiKey,
        firebaseWebAppAppId: firebaseHosting.webApp.appId,
        firebaseHostingSiteDefaultUrl: firebaseHosting.hostingSite.defaultUrl,
        dependsOn: [firebaseHosting.hostingSite]
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
    new TerraformOutput(this, "speech-file-bucket", {
      value: speechFileBucket.name,
    });

    new TerraformOutput(this, "client-project-id", {
      value: clientProject.projectId,
    });

    new TerraformOutput(this, "webapp-app-id", {
        value: firebaseHosting.webApp.appId,
    });

    new TerraformOutput(this, "hosting-url", {
        value: firebaseHosting.hostingSite.defaultUrl,
    });

    new TerraformOutput(this, "firebase-api-key", {
      value: firebaseWebAppConfig.apiKey,
      sensitive: true
    });
  }
}

async function buildStack(scope: Construct, id: string) {
  const stack = new LangBridgeApiStack(scope, id);
  await stack.buildLangBridgeApiStack();
}

async function createApp(): Promise<App> {
  const app = new App();
  await buildStack(app, "cdktf");
  return app;
}

createApp().then((app) => app.synth());
