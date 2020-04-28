Deployments and Local Bootstrap
===============================

We use different deployment strategies for environments
like Docker Swarm, Kubernetes or a local-machine. The local machine 
environment is recommeneded for development and testing, while Kubernetes
and Docker Swarm for production. 

The production deployment repositories are:

* `Kubernetes Helm charts <https://github.com/neicnordic/sda-helm/>`_;
* `Docker Swarm <https://github.com/neicnordic/LocalEGA-deploy-swarm/>`_.

The following container images are used in the deployments:

* ``neicnordic/sda-base``, and containing `python 3.6` and the LocalEGA services;
* ``neicnordic/sda-mq`` (based on `rabbitmq:3.7.8-management`);
* ``neicnordic/sda-db`` (based on `postgres:11.2`);
* ``neicnordic/sda-inbox-sftp`` (based on Apache Mina);
* ``neicnordic/sda-doa`` (Data Out API);
* ``neicnordic/sda-s3-proxy`` (S3 proxy inbox).

In order to simplify the setup of SDA's components, we have
developed a a bootstrap script (one for the `Docker`_ deployment).
The bootstrap deployment creates all the necessary configuration 
simulating an deployment. The bootstrap is also used for integration testing

.. _Docker: https://github.com/neicnordic/LocalEGA/tree/master/deploy
