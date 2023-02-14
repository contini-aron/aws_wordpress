import aws_cdk as cdk
from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_ptn,
    aws_efs as efs,
    aws_rds as rds,
    aws_secretsmanager as smg,
    aws_iam as iam,
)

from constructs import Construct


def gen_salt(context, id) -> smg.Secret:
    return smg.Secret(
        context,
        id,
        generate_secret_string=smg.SecretStringGenerator(
            exclude_characters="'\"",
            password_length=64,
        ),
        removal_policy=cdk.RemovalPolicy.DESTROY,
    )


def snake_to_pascal(snake_word: str):
    """
    convert snake case to camel case ignoring the first word
    """
    words = snake_word.split("_")
    return "".join(w.title() for w in words[1:])


class AwsWordpressStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        vpc = ec2.Vpc(self, "VPC")
        # create the ecs cluster
        cluster = ecs.Cluster(self, id="Cluster", vpc=vpc)

        # create wordpress secrets
        secret_db_cred = smg.Secret(
            self,
            "DatabaseCredentials",
            generate_secret_string=smg.SecretStringGenerator(
                password_length=30,
                exclude_punctuation=True,
                include_space=False,
                secret_string_template='{"username":"admin"}',
                generate_string_key="password",
            ),
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        salt_names = [
            "secret_auth_key",
            "secret_secure_auth_key",
            "secret_logged_in_key",
            "secret_nonce_key",
            "secret_auth_salt",
            "secret_secure_auth_salt",
            "secret_logged_in_salt",
            "secret_nonce_salt",
        ]
        salts: dict = {k: gen_salt(self, snake_to_pascal(k)) for k in salt_names}

        db = rds.ServerlessCluster(
            self,
            "DataBase",
            engine=rds.DatabaseClusterEngine.AURORA_MYSQL,
            default_database_name="wordpress",
            #############################################################
            credentials=rds.Credentials.from_secret(secret_db_cred, username="admin"),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        fs_sec_group = ec2.SecurityGroup(
            self, "EfsSecurityGroup", vpc=vpc, description="Worpress access to EFS"
        )

        file_system = efs.FileSystem(
            self,
            "Content",
            vpc=vpc,
            encrypted=True,
            security_group=fs_sec_group,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        task_exec_role = iam.Role(
            self,
            "TaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        task_exec_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AmazonECSTaskExecutionRolePolicy"
            )
        )
        secret_db_cred.grant_read(task_exec_role)

        # grant task exec read for all salts
        for salt in salts.values():
            salt.grant_read(task_exec_role)

        task_sec_group = ec2.SecurityGroup(
            self,
            "TaskSecurityGroup",
            vpc=vpc,
            description="allow access to the task",
            allow_all_outbound=True,
        )

        task = ecs.FargateTaskDefinition(
            self,
            "TaskDef",
            family="wordpress",
            memory_limit_mib=1024,
            cpu=512,
            volumes=[
                ecs.Volume(
                    name="wp-content",
                    efs_volume_configuration=ecs.EfsVolumeConfiguration(
                        file_system_id=file_system.file_system_id,
                        transit_encryption="ENABLED",
                    ),
                )
            ],
        )

        secrets = {
            k.replace("secret", "wordpress").upper(): ecs.Secret.from_secrets_manager(v)
            for k, v in salts.items()
        }
        secrets["WORDPRESS_DB_PASSWORD"] = ecs.Secret.from_secrets_manager(
            secret_db_cred, field="password"
        )

        container = task.add_container(
            "WordPress",
            image=ecs.ContainerImage.from_registry("wordpress:latest"),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="WordPress"),
            memory_limit_mib=1024,
            cpu=512,
            environment={
                "WORDPRESS_DB_HOST": db.cluster_endpoint.socket_address,
                "WORDPRESS_DB_NAME": "wordpress",
                "WORDPRESS_DB_USER": "admin",
            },
            secrets=secrets,
        )

        container.add_port_mappings(ecs.PortMapping(container_port=80))

        container.add_mount_points(
            ecs.MountPoint(
                container_path="/var/www/html/wp-content",
                read_only=False,
                source_volume="wp-content",
            )
        )

        wordpress = ecs_ptn.ApplicationLoadBalancedFargateService(
            self,
            "Service",
            cluster=cluster,
            task_definition=task,
            platform_version=ecs.FargatePlatformVersion.VERSION1_4,
        )

        wordpress.service.connections.add_security_group(task_sec_group)
        wordpress.service.auto_scale_task_count(min_capacity=2, max_capacity=4)

        wordpress.target_group.configure_health_check(
            enabled=True,
            path="/index.php",
            healthy_http_codes="200,201,302",
            interval=cdk.Duration.seconds(15),
            timeout=cdk.Duration.seconds(10),
            healthy_threshold_count=3,
            unhealthy_threshold_count=2,
        )

        db.connections.allow_from(
            ec2.Peer.ipv4(vpc.vpc_cidr_block),
            ec2.Port.tcp(3306),
            description="allow connections inside VPC",
        )
        fs_sec_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block), connection=ec2.Port.tcp(2049)
        )
