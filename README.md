# aws_wordpress
PoC of a high availability wordpress deployment on AWS

## Architectural Overview
![Alt text](resources/architectural_overview.png?raw=true "Title")

This repository uses ECS with Fargate to deploy an highly available and scalable Wordpress installation on AWS Fargate on Amazon ECS. 
It will provision a VPC, ECS Cluster, EFS Filesystem, Secrets, Aurora, and Wordpress Containers.

To deploy Wordpress we use the official Wordpress container image available on Docker hub.

In order to share between containers the wp-content folder of Wordpress (plugins, themes...) an EFS volume is attached to all the running containers.

AWS Secrets Manager to store database credentials for the Serverless Aurora Cluster and to generate the Wordpress Salts.

## Test it!
[install](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_install) and [bootstrap](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html) aws cdk

clone the repository
```
git clone https://github.com/contini-aron/aws_wordpress.git
```
change directory into the folder
```
cd aws_wordpress
```

make a virtualenv:
```
virtualenv env
```
activate env  and install requirements
``` bash
source ./env/bin/activate
pip install -r requirements.txt
```

run a cdk synthesize
```
cdk synth
```
run a cdk deploy
```
cdk deploy
```
## Test cleanup

make sure to cleanup the resources by running the command 
```
cdk destroy
```
to avoid paying unnecessary $

## Development setup
make a dev virtualenv:
```
virtualenv env_dev
```
activate env  and install requirements
``` bash
source ./env_dev/bin/activate
pip install -r requirements-dev.txt
```
install pre-commit hooks:
```
pre-commit install
pre-commit install --hook-type commit-msg
```

