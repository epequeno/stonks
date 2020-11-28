"""
generate a CFN template suitable to deploy the `stonks` application
usage: $ python template.py > stonks.template
"""
# stdlib

# 3rd party
from troposphere import Template, Ref, GetAtt, Tags, Base64, Join, Output, Sub
from troposphere.ec2 import (
    VPC,
    Subnet,
    Route,
    RouteTable,
    NatGateway,
    InternetGateway,
    EIP,
    VPCGatewayAttachment,
    Instance,
    SubnetRouteTableAssociation,
    SecurityGroup,
    SecurityGroupRule,
)
from troposphere.iam import InstanceProfile, Role
from awacs.aws import (
    PolicyDocument,
    Statement,
    Action,
    Principal,
)


# local

t = Template()
t.set_version()
t.set_description(
    "stonks.template - deploy minikube onto an ec2 instance, then deploy stonks application into the k8s cluster."
)

# === NETWORK === #
# vpc
vpc_resource = t.add_resource(
    VPC("vpc", CidrBlock="10.0.0.0/16", Tags=Tags(Name="k8s-VPC"))
)

# subnets
public_subnet_resource = t.add_resource(
    Subnet(
        "publicSubnet",
        CidrBlock="10.0.1.0/20",
        VpcId=Ref(vpc_resource),
        MapPublicIpOnLaunch=True,
        Tags=Tags(Name="k8s-public-subnet"),
    )
)

# gateways
internet_gw_resource = t.add_resource(InternetGateway("IGW", Tags=Tags(Name="k8s-IGW")))
igw_attachment_resource = t.add_resource(
    VPCGatewayAttachment(
        "igwAttachment",
        InternetGatewayId=Ref(internet_gw_resource),
        VpcId=Ref(vpc_resource),
    )
)

# routes
public_route_table_resource = t.add_resource(
    RouteTable(
        "publicRouteTable",
        VpcId=Ref(vpc_resource),
        Tags=Tags(Name="k8s-public-RouteTable"),
    )
)

public_route_resource = t.add_resource(
    Route(
        "publicRoute",
        DestinationCidrBlock="0.0.0.0/0",
        GatewayId=Ref(internet_gw_resource),
        RouteTableId=Ref(public_route_table_resource),
    )
)

public_subnet_association_resource = t.add_resource(
    SubnetRouteTableAssociation(
        "publicSubnetAssociation",
        SubnetId=Ref(public_subnet_resource),
        RouteTableId=Ref(public_route_table_resource),
    )
)

# security groups
cluster_security_group_resource = t.add_resource(
    SecurityGroup(
        "k8sClusterSG",
        GroupDescription="SG for the k8s cluster",
        GroupName="k8s-cluster-SG",
        SecurityGroupIngress=[
            SecurityGroupRule(
                IpProtocol="tcp", FromPort="30007", ToPort="30007", CidrIp="0.0.0.0/0"
            )
        ],
        SecurityGroupEgress=[SecurityGroupRule(IpProtocol="-1", CidrIp="0.0.0.0/0")],
        VpcId=Ref(vpc_resource),
    )
)

# === K8S CLUSTER === #
instance_role_resource = t.add_resource(
    Role(
        "instanceRole",
        RoleName="k8sClusterRole",
        ManagedPolicyArns=["arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"],
        AssumeRolePolicyDocument=PolicyDocument(
            Statement=[
                Statement(
                    Effect="Allow",
                    Principal=Principal("Service", "ec2.amazonaws.com"),
                    Action=[Action("sts", "AssumeRole")],
                )
            ]
        ),
    )
)

instance_profile_resource = t.add_resource(
    InstanceProfile(
        "instanceProfile",
        InstanceProfileName="k8s-cluster-profile",
        Roles=[Ref(instance_role_resource)],
    )
)

# minikube will only start automatically once after the instance is first launched
# possible solution is to create a systemd service file to ensure the service stays running.
with open("./userData.sh") as fd:
    user_data = fd.read().splitlines()

ec2_instance_resource = t.add_resource(
    Instance(
        "k8sInstance",
        # minikube requires at least 2 CPU, t2.medium is the smallest available size with this many vCPU
        InstanceType="t2.medium",
        ImageId="ami-04d29b6f966df1537",  # Amazon Linux 2 AMI (HVM), SSD Volume Type - (64-bit x86)
        SubnetId=Ref(public_subnet_resource),
        SecurityGroupIds=[Ref(cluster_security_group_resource)],
        IamInstanceProfile=Ref(instance_profile_resource),
        UserData=Base64(Join("\n", user_data)),
        Tags=Tags(Name="k8s-cluster"),
    )
)

# === OUTPUTS ===#
t.add_output(
    Output(
        "serviceURL",
        Description="url for the stonks service",
        Value=Sub("http://${IP}:30007", IP=GetAtt(ec2_instance_resource, "PublicIp")),
    )
)

if __name__ == "__main__":
    print(t.to_json())
