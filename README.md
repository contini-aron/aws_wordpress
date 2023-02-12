# aws_wordpress
PoC of a high availability wordpress deployment on AWS

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

