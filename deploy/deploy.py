#!./venv/bin/python
"""
CLI application used to deploy application
"""
# stdlib
from getpass import getpass
from time import sleep

# 3rd party
import boto3
import click
import requests

# local

STACK_NAME = "stonks-application"


@click.command()
def main():
    # only us-east-1 is supported since the region-specific AMI ID is hard-coded into the template.
    region = "us-east-1"
    api_key = getpass("Please provide an API Key: ")

    click.echo("creating secrets manager secret for API Key")
    secrets_client = boto3.client("secretsmanager")
    secrets_client.create_secret(
        Name="stonks-api-key",
        Description="API Key to be used with upstream API for stonks application",
        SecretString=api_key,
    )

    click.echo(f"Launching stack '{STACK_NAME}' into {region}")
    cfn_client = boto3.client("cloudformation", region_name=region)

    with open("./stonks.template") as fd:
        template_body = fd.read()
        cfn_client.create_stack(
            StackName=STACK_NAME,
            TemplateBody=template_body,
            Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
        )

    click.echo(f"waiting on {STACK_NAME} stack to complete launch...")
    waiter = cfn_client.get_waiter("stack_create_complete")
    try:
        waiter.wait(StackName=STACK_NAME)
    except Exception as e:
        click.echo(f"error launching stack: {e}")
        exit(1)
    click.echo("stack create completed!")

    stack_details = cfn_client.describe_stacks(StackName=STACK_NAME).get("Stacks")[0]
    stack_outputs = stack_details.get("Outputs")

    cluster_instance_id = None
    url = None
    for output in stack_outputs:
        if output.get("OutputKey") == "serviceURL":
            url = output.get("OutputValue")

        if output.get("OutputKey") == "clusterInstanceId":
            cluster_instance_id = output.get("OutputValue")

    click.echo(f"stonks service url: {url}")
    click.echo(
        "waiting on service to become available; success expected between 3-6 attempts."
    )
    retry_limit = 10
    counter = 1
    while counter < retry_limit:
        is_ok = False
        try:
            res = requests.get(url, timeout=3)
            is_ok = "data=" in res.text
        except:
            # we expect some initial failures right after the stack first launches
            # we could log more information here if needed; for now we'll just ignore these errors.
            pass

        click.echo(f"attempt #{counter}: OK?: {is_ok}")
        if is_ok:
            click.echo("successful response seen from application!")
            break
        sleep(30)
        counter += 1

    if counter >= 9:
        stack_id = stack_details.get("StackId")
        click.echo(f"failed to see application start in expected time; exiting!")
        click.echo(f"please review stack for more details: {stack_id}")
        exit(1)


if __name__ == "__main__":
    main()
