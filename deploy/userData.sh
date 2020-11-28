#!/bin/bash

INSTALL_DIR=/usr/local/sbin

# install dependencies and enable docker
yum install docker conntrack -y
systemctl enable docker
systemctl start docker

# install kubectl (from https://kubernetes.io/docs/tasks/tools/install-kubectl/)
curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ./kubectl
mv ./kubectl "${INSTALL_DIR}/kubectl"

# install minikube (from https://minikube.sigs.k8s.io/docs/start/)
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
cp minikube-linux-amd64 "${INSTALL_DIR}/minikube"
chmod +x "${INSTALL_DIR}/minikube"

minikube start --driver=none

# userData is run under / and so the `root` users configuration is incorrect. The following steps apply a
# correct configuration for the user so subsequent steps (installing the application) can proceed.
# also see: https://github.com/kubernetes/minikube/issues/8363#issuecomment-637892712
rm -rf /root/.kube /root/.minikube
mv /.kube /.minikube /root
# replace references to .minikube/ to /root/.minikube in kube config
sed -i 's|\.minikube|/root/\.minikube|g' /root/.kube/config
cd /root || exit

# set up stonks application
APIKEY=$(echo -n "$(aws --region us-east-1 secretsmanager get-secret-value --secret-id stonks-api-key --query 'SecretString')" | base64)
wget https://raw.githubusercontent.com/epequeno/stonks/master/deploy/stonks.yaml
sed -i "s/key: \"demo\"/key: ${APIKEY}/" stonks.yaml
kubectl apply -f stonks.yaml

echo "UserData script complete!"
