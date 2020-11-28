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

echo "whoami"
echo whoami
cd /root
minikube start --driver=none

echo "UserData script complete!"
