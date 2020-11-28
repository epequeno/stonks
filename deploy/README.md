# stonks

A web application which reads stock data from an upstream API and summarizes stock price data. Deployed into a minikube cluster which runs on an EC2 instance in AWS.

## Project structure

- `./src/main.rs` contains the source code for the web application
- `./deploy/template.py` is a python script to create the CloudFormation template (using the `troposphere` library). 
- `./deploy/stonks.template` is the CloudFormation template which does the following
  - Creates underlying AWS infrastructure (instance, security group, etc)
  - Installs and starts `minikube`
  - obtains application manifest from github and launches application within K8S
- `./deploy/userData.sh` is a bash script which is provided to the ec2 instance to run at boot, this does most of the "work" related to bootstrapping the instance at launch.
- `./deploy/stonks.yaml` is the k8s manifest which is pulled by the ec2 instance and created within `minikube`
- `./deploy/deploy.py` is a python CLI application used to automate deploying this application (both aws infra and k8s).


## Deployment

The application is designed to be deployed using CloudFormation. Since additional steps are required to ensure the correct API key is provided to the application, a python CLI app has been provided to coordinate gathering this API key as well as deploying the CFN stack automatically.

### Requirements
Please ensure you have an AWS account to launch into and have credentials configured in the standard locations as described here: [Using the Default Credential Provider Chain](https://docs.aws.amazon.com/sdk-for-php/v3/developer-guide/guide_credentials.html#default-credential-chain)

The following steps were developed with a linux system in mind, these should also be applicable to MacOS, a process for Windows systems has not been provided.

Python 3 is required for the CLI app.

### Procedure

Follow these steps to configure your local environment for deployment. These steps should be run from the base of this repository (the same location as this `README.md` file.)

```bash
$ cd ./deploy

# create and use a python virtual environment (assuming BASH shell)
$ virtualenv -p $(which python3) venv
$ source ./venv/bin/activate

# install dependencies
(venv) $ pip install -r requirements.txt

# run the deploy.py application
(venv) $ ./deploy.py
```

Here is an example of what a deployment should look like:

```text
(venv) $ ./deploy.py
Please provide an API Key: 
creating secrets manager secret for API Key
Launching stack 'stonks-application' into us-east-1
waiting on stonks-application stack to complete launch...
stack create completed!
stonks service url: http://<redacted_ip_address>:30007
waiting on service to become available; success expected between 3-6 attempts.
attempt #1: OK?: False
attempt #2: OK?: False
attempt #3: OK?: False
attempt #4: OK?: False
attempt #5: OK?: True
successful response seen from application!
```

At this point the live application is accessible at the service URL provided by the CLI application. 

After the stack has completed launching this service URL can also be obtained at any time by querying the stack outputs:

```bash
$ aws cloudformation describe-stacks --stack-name stonks-application --query "Stacks[0].Outputs[?OutputKey=='serviceURL'].OutputValue|[0]"

"http://<redacted_ip_address>:30007"
```

## Build web application

To build the web application (rust application) run the following command from the base of this repository.

```bash
$ cargo build --release
```

## Build the docker container

The following steps were used to build the docker container which has been pushed to docker hub: [dockerhub/epequeno/stonks](https://hub.docker.com/r/epequeno/stonks).

```bash
$ docker login
$ docker build -t stonks .
$ docker tag stonks epequeno/stonks:latest
$ docker push epequeno/stonks
```

## additional info

The deployment script creates an AWS secret to hold the API key used in the application. Deleting this secret through the web console forces a 7 day wait before fully removing it. The secret can be forcefully deleted through the cli using the following command:

```bash
$ aws secretsmanager delete-secret --secret-id stonks-api-key --force-delete-without-recovery
```

The ec2 instance was launched **WITHOUT** an SSH key. All remote access is intended to be done through SSM session manager as described here: [Starting a session (AWS CLI)](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html#sessions-start-cli). 

Please ensure you have the session manager plugin installed in order to start remote sessions from your local terminal: [(Optional) Install the Session Manager plugin for the AWS CLI ](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html). Otherwise, a session can be started through a web-browser console session using the following procedure: [Starting a session (Systems Manager console)](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html#start-sys-console)

```bash
# get the instance ID from the stack outputs
$ aws cloudformation describe-stacks --stack-name stonks-application --query "Stacks[0].Outputs[?OutputKey=='clusterInstanceId'].OutputValue|[0]"

i-example

# use that instance ID to connect to start a remote session
$ aws ssm start-session --target i-example
sh-4.2$ sudo -i
[root@ip-x-x-x-x ~]$ kubectl get po
NAME                      READY   STATUS    RESTARTS   AGE
stonks-66cd84868c-qzqp9   1/1     Running   0          26m

```