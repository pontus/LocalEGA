#!/usr/bin/env bash
set -e

[ ${BASH_VERSINFO[0]} -lt 4 ] && echo 'Bash 4 (or higher) is required' 1>&2 && exit 1

HERE=$(dirname ${BASH_SOURCE[0]})
PRIVATE=${HERE}/../private
DOT_ENV=${HERE}/../.env
EXTRAS=${HERE}/../../extras
TRACE_FILE=${PRIVATE}/config/trace.yml

# Defaults
VERBOSE=no
FORCE=yes
OPENSSL=openssl
ARCHIVE_BACKEND=s3
HOSTNAME_DOMAIN='.default' #".localega"

PYTHONEXEC=python

function usage {
    echo "Usage: $0 [options]"
    echo -e "\nOptions are:"
    echo -e "\t--openssl <value>     \tPath to the Openssl executable [Default: ${OPENSSL}]"
    echo -e "\t--archive-backend <value> \tSelect the archive backend: S3 or POSIX [Default: ${ARCHIVE_BACKEND}]"
    echo -e "\t--pythonexec <value>  \tPython execute command [Default: ${PYTHONEXEC}]"
    echo -e "\t--domain <value>      \tDomain for the hostnames [Default: '${HOSTNAME_DOMAIN}']"
    echo ""
    echo -e "\t--verbose, -v     \tShow verbose output"
    echo -e "\t--polite, -p      \tDo not force the re-creation of the subfolders. Ask instead"
    echo -e "\t--help, -h        \tOutputs this message and exits"
    echo -e "\t-- ...            \tAny other options appearing after the -- will be ignored"
    echo ""
}


# While there are arguments or '--' is reached
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) usage; exit 0;;
        --verbose|-v) VERBOSE=yes;;
        --polite|-p) FORCE=no;;
        --openssl) OPENSSL=$2; shift;;
        --archive-backend) ARCHIVE_BACKEND=${2,,}; shift;;
        --pythonexec) PYTHONEXEC=$2; shift;;
        --domain) HOSTNAME_DOMAIN=${2,,}; shift;;
        --) shift; break;;
        *) echo "$0: error - unrecognized option $1" 1>&2; usage; exit 1;;
    esac
    shift
done

#########################################################################

source ${HERE}/defs.sh

[[ -x $(readlink ${OPENSSL}) ]] && echo "${OPENSSL} is not executable. Adjust the setting with --openssl" && exit 3
[[ -x $(readlink ${PYTHONEXEC}) ]] && echo "${PYTHONEXEC} is not executable. Adjust the setting with --pythonexec" && exit 3

for prog in keytool expect crypt4gh-keygen; do
    if type -p "$prog" >/dev/null  ; then
        :
    else
        echo "Could not find $prog, please make sure it's installed and in PATH"
        exit 1
    fi	
done

rm_politely ${PRIVATE}
mkdir -p ${PRIVATE}
exec 2>${PRIVATE}/.err

check_python_module shyaml &>${PRIVATE}/.err

#########################################################################
echo -n "Bootstrapping "
echomsg "\t* configuration and the SSL certificates"

if command -v legainit &>/dev/null; then
  legainit --cega --config-path  ${PRIVATE}/config &>${PRIVATE}/.err
else 
  pip install git+https://github.com/neicnordic/LocalEGA-deploy-init.git &>${PRIVATE}/.err
  legainit --cega --config-path  ${PRIVATE}/config &>${PRIVATE}/.err
fi

chmod 0600 ${PRIVATE}/config/certs/db.ca.key

#########################################################################
[[ "${VERBOSE}" == 'yes' ]] && echo "" # new line

echomsg "\t* Loading the settings"
source ${HERE}/settings.rc

echomsg "\t* Fake Central EGA parameters"
# For the fake CEGA
CEGA_CONNECTION_PARAMS=$(url_encode ${HOSTNAME_DOMAIN} cega)
CEGA_PASSWORD=$(get_trace_value secrets.cega_mq_pass)
CEGA_CONNECTION="amqps://lega:${CEGA_PASSWORD}@cega-mq${HOSTNAME_DOMAIN}:5671/lega?${CEGA_CONNECTION_PARAMS}"
CEGA_USERS_ENDPOINT="https://cega-users${HOSTNAME_DOMAIN}/lega/v1/legas/users"
CEGA_USERS_CREDS=$'legatest:legatest'

echomsg "\t* Fake Central EGA users"
# For the fake Users
source ${HERE}/users.sh

#########################################################################

backup ${DOT_ENV}

cat > ${DOT_ENV} <<EOF
COMPOSE_PROJECT_NAME=lega
COMPOSE_FILE=${PRIVATE}/lega.yml:${PRIVATE}/cega.yml
COMPOSE_PATH_SEPARATOR=:
EOF

#########################################################################

mkdir -p $PRIVATE/{keys,logs}
chmod 700 $PRIVATE/{keys,logs}

echomsg "\t* the C4GH key"

# C4GH_PASSPHRASE is an env var
cat > ${PRIVATE}/keys/c4gh_keygen.sh <<EOF
set timeout -1
spawn crypt4gh-keygen -f --pk ${PRIVATE}/keys/ega.pub --sk ${PRIVATE}/keys/ega.sec
expect "Passphrase for *"
send -- "${C4GH_PASSPHRASE}\r"
expect eof
EOF
expect -f ${PRIVATE}/keys/c4gh_keygen.sh &>/dev/null
rm -f ${PRIVATE}/keys/c4gh_keygen.sh

# Making the key readable, because when it's injected inside the container
# it retains the permissions. Therefore, originally 400, will make it unreadable to the lega user.
chmod 444 ${PRIVATE}/keys/ega.sec

#########################################################################

echomsg "\t* Entrypoint"

# This script is used to go around a feature (bug?) of docker.
# When the /etc/ega/ssl.key is injected,
# it is owned by the host user that injected it.
# On Travis, it's the travis (2000) user.
# It needs to be 600 or less, meaning no group nor world access.
#
# In other words, the lega user cannot read that file.
#
# So we use the following trick.
# We make:
#     * /etc/ega/ssl.key world-readable.
#     * /etc/ega owned by the lega group (so we can write a file in it)
# and then, we copy /etc/ega/ssl.key to /etc/ega/ssl.key.lega
# But this time, owned by lega, and with 400 permissions
#
# This should not be necessary for the deployment
# as they are capable of injecting a file with given owner and permissions.
#

cat > ${PRIVATE}/entrypoint.sh <<'EOF'
#!/bin/sh
set -e
cp /etc/ega/ssl.key /etc/ega/ssl.key.lega
chmod 400 /etc/ega/ssl.key.lega
exec $@
EOF
chmod +x ${PRIVATE}/entrypoint.sh


#########################################################################

echomsg "\t* conf.ini"
cat > ${PRIVATE}/conf.ini <<EOF
[DEFAULT]
log = debug
#log = silent

master_key = c4gh_file

[c4gh_file]
loader_class = C4GHFileKey
passphrase = ${C4GH_PASSPHRASE}
filepath = /etc/ega/ega.sec

EOF

# Local broker connection
MQ_CONNECTION_PARAMS=$(url_encode ${HOSTNAME_DOMAIN} mq)

# Pika is not parsing the URL the way RabbitMQ likes.
# So we add the parameters on the configuration file and
# create the SSL socket ourselves
# Some parameters can be passed in the URL, though.
MQ_CONNECTION="amqps://${MQ_USER}:${MQ_PASSWORD}@localega-mq-server${HOSTNAME_DOMAIN}:5671/%2F"

# Database connection
DB_CONNECTION_PARAMS=$(url_encode ${HOSTNAME_DOMAIN} db)

DB_CONNECTION="postgres://lega_in:${DB_LEGA_IN_PASSWORD}@localega-db${HOSTNAME_DOMAIN}:5432/lega"

#
# Configuration file
#

cat >> ${PRIVATE}/conf.ini <<EOF

## Connecting to Local EGA

[archive]
EOF
if [[ ${ARCHIVE_BACKEND} == 's3' ]]; then
    cat >> ${PRIVATE}/conf.ini <<EOF
storage_driver = S3Storage
s3_url = https://minio${HOSTNAME_DOMAIN}:9000
s3_access_key = ${S3_ACCESS_KEY}
s3_secret_key = ${S3_SECRET_KEY}
s3_bucket = lega
#region = lega
cacertfile = /etc/ega/CA.cert
certfile = /etc/ega/ssl.cert
keyfile = /etc/ega/ssl.key
EOF
else
    # POSIX file system
    cat >> ${PRIVATE}/conf.ini <<EOF
storage_driver = FileStorage
location = /ega/archive/%s/
user = lega
EOF
fi

cat >> ${PRIVATE}/conf.ini <<EOF
# Default: POSIX file system
[inbox]
location = /ega/inbox/%s/
chroot_sessions = True
user = lega
EOF


#########################################################################
# Specifying the LocalEGA components in the docke-compose file
#########################################################################
cat > ${PRIVATE}/lega.yml <<EOF
version: '3.2'

networks:
  lega:
    # user overlay in swarm mode
    # default is bridge
    driver: bridge

# Use the default driver for volume creation
volumes:
  mq:
  db:
  inbox:
  archive:
EOF

cat >> ${PRIVATE}/lega.yml <<EOF

services:

  ############################################
  # Local EGA instance
  ############################################

  # Local Message broker
  localega-mq-server:
    environment:
      - CEGA_CONNECTION=${CEGA_CONNECTION}
      - MQ_USER=${MQ_USER}
      - MQ_PASSWORD_HASH=${MQ_PASSWORD_HASH}
      - MQ_CA=/etc/rabbitmq/CA.cert
      - MQ_SERVER_CERT=/etc/rabbitmq/ssl.cert
      - MQ_SERVER_KEY=/etc/rabbitmq/ssl.key
    hostname: mq${HOSTNAME_DOMAIN}
    ports:
      - "${DOCKER_PORT_mq}:15672"
    image: "neicnordic/sda-mq:latest"
    container_name: localega-mq-server${HOSTNAME_DOMAIN}
    labels:
        lega_label: "localega-mq-server"
    restart: on-failure:3
    networks:
      - lega
    volumes:
      - mq:/var/lib/rabbitmq
      - ./config/certs/mq-server.ca.crt:/etc/rabbitmq/ssl.cert
      - ./config/certs/mq-server.ca.key:/etc/rabbitmq/ssl.key
      - ./config/certs/root.ca.crt:/etc/rabbitmq/CA.cert

  # Local Database
  localega-db:
    environment:
      - DB_LEGA_IN_PASSWORD=${DB_LEGA_IN_PASSWORD}
      - DB_LEGA_OUT_PASSWORD=${DB_LEGA_OUT_PASSWORD}
      - PG_SERVER_CERT=/tls/db.ca.crt
      - PG_SERVER_KEY=/tls/db.ca.key
      - PG_CA=/tls/root.ca.crt
      - PG_VERIFY_PEER=0
    hostname: localega-db${HOSTNAME_DOMAIN}
    container_name: localega-db${HOSTNAME_DOMAIN}
    labels:
        lega_label: "localega-db"
    image: neicnordic/sda-db:latest
    ports:
      - "5432:5432"
    volumes:
      - db:/var/lib/postgresql
      - ./config/certs/db.ca.crt:/tls/db.ca.crt
      - ./config/certs/db.ca.key:/tls/db.ca.key:ro
      - ./config/certs/root.ca.crt:/tls/root.ca.crt
    restart: on-failure:3
    networks:
      - lega

  # SFTP inbox
  localega-inbox:
    hostname: localega-inbox${HOSTNAME_DOMAIN}
    depends_on:
      - localega-mq-server
    # Required external link
    container_name: localega-inbox${HOSTNAME_DOMAIN}
    labels:
        lega_label: "localega-inbox"
    restart: on-failure:3
    networks:
      - lega
    environment:
      - BROKER_USERNAME=${MQ_USER}
      - BROKER_PASSWORD=${MQ_PASSWORD}
      - BROKER_HOST=localega-mq-server${HOSTNAME_DOMAIN}
      - BROKER_PORT=5671
      - BROKER_VHOST=/
      - CEGA_ENDPOINT=${CEGA_USERS_ENDPOINT%/}/%s?idType=username
      - CEGA_ENDPOINT_CREDS=${CEGA_USERS_CREDS}
      - KEYSTORE_TYPE=PKCS12
      - KEYSTORE_PASSWORD=changeit
      - KEYSTORE_PATH=/ega/tls/inbox.p12
      - USE_SSL=true
    ports:
      - "${DOCKER_PORT_inbox}:2222"
    image: neicnordic/sda-inbox-sftp
    volumes:
      - inbox:/ega/inbox
      - ./config/certs/inbox.p12:/ega/tls/inbox.p12
      - ./config/certs/cacerts:/opt/openjdk-13/lib/security/cacerts
EOF


cat >> ${PRIVATE}/lega.yml <<EOF

  # Ingestion Workers
  ingest:
    hostname: ingest${HOSTNAME_DOMAIN}
    depends_on:
      - localega-db
      - localega-mq-server
    image: neicnordic/sda-base:latest
    container_name: ingest${HOSTNAME_DOMAIN}
    labels:
        lega_label: "ingest"
    environment:
      - DB_CONNECTION=${DB_CONNECTION}?${DB_CONNECTION_PARAMS}
      - BROKER_CACERTFILE=/etc/ega/CA.cert
      - BROKER_CERTFILE=/etc/ega/ssl.cert
      - BROKER_KEYFILE=/etc/ega/ssl.key
      - BROKER_VERIFY_HOSTNAME=no
      - BROKER_VERIFY_PEER=yes
      - BROKER_CONNECTION=${MQ_CONNECTION}?${MQ_CONNECTION_PARAMS}
      - S3_ACCESS_KEY=${S3_ACCESS_KEY}
      - S3_SECRET_KEY=${S3_SECRET_KEY}
      - AWS_ACCESS_KEY_ID=${S3_ACCESS_KEY}
      - AWS_SECRET_ACCESS_KEY=${S3_SECRET_KEY}
    volumes:
      - inbox:/ega/inbox
      - ./conf.ini:/etc/ega/conf.ini:ro
      - ./entrypoint.sh:/usr/local/bin/lega-entrypoint.sh
      - ./config/certs/ingest.ca.crt:/etc/ega/ssl.cert
      - ./config/certs/ingest.ca.key:/etc/ega/ssl.key
      - ./config/certs/root.ca.crt:/etc/ega/CA.cert
EOF
if [[ ${ARCHIVE_BACKEND} == 'posix' ]]; then
cat >> ${PRIVATE}/lega.yml <<EOF
      - archive:/ega/archive
EOF
fi

cat >> ${PRIVATE}/lega.yml <<EOF
    restart: on-failure
    networks:
      - lega
    user: lega
    entrypoint: ["lega-entrypoint.sh"]
    command: ["ega-ingest"]
    # entrypoint: ["/bin/sleep", "1000000000000"]

  # Consistency Control
  verify:
    depends_on:
      - localega-db
      - localega-mq-server
    hostname: verify${HOSTNAME_DOMAIN}
    container_name: verify${HOSTNAME_DOMAIN}
    labels:
        lega_label: "verify"
    image: neicnordic/sda-base:latest
    environment:
      - DB_CONNECTION=${DB_CONNECTION}?${DB_CONNECTION_PARAMS}
      - BROKER_CACERTFILE=/etc/ega/CA.cert
      - BROKER_CERTFILE=/etc/ega/ssl.cert
      - BROKER_KEYFILE=/etc/ega/ssl.key
      - BROKER_VERIFY_HOSTNAME=no
      - BROKER_VERIFY_PEER=yes
      - BROKER_CONNECTION=${MQ_CONNECTION}?${MQ_CONNECTION_PARAMS}
      - S3_ACCESS_KEY=${S3_ACCESS_KEY}
      - S3_SECRET_KEY=${S3_SECRET_KEY}
      - AWS_ACCESS_KEY_ID=${S3_ACCESS_KEY}
      - AWS_SECRET_ACCESS_KEY=${S3_SECRET_KEY}
    volumes:
      - ./conf.ini:/etc/ega/conf.ini:ro
      - ./keys/ega.sec:/etc/ega/ega.sec
      - ./entrypoint.sh:/usr/local/bin/lega-entrypoint.sh
      - ./config/certs/verify.ca.crt:/etc/ega/ssl.cert
      - ./config/certs/verify.ca.key:/etc/ega/ssl.key
      - ./config/certs/root.ca.crt:/etc/ega/CA.cert
EOF
if [[ ${ARCHIVE_BACKEND} == 'posix' ]]; then
cat >> ${PRIVATE}/lega.yml <<EOF
      - archive:/ega/archive
EOF
fi

cat >> ${PRIVATE}/lega.yml <<EOF
    restart: on-failure
    networks:
      - lega
    user: lega
    entrypoint: ["lega-entrypoint.sh"]
    command: ["ega-verify"]
    # entrypoint: ["/bin/sleep", "1000000000000"]

  # Stable ID mapper
  finalize:
    hostname: finalize${HOSTNAME_DOMAIN}
    depends_on:
      - localega-db
      - localega-mq-server
    image: neicnordic/sda-base:latest
    container_name: finalize${HOSTNAME_DOMAIN}
    labels:
        lega_label: "finalize"
    environment:
      - DB_CONNECTION=${DB_CONNECTION}?${DB_CONNECTION_PARAMS}
      - BROKER_CACERTFILE=/etc/ega/CA.cert
      - BROKER_CERTFILE=/etc/ega/ssl.cert
      - BROKER_KEYFILE=/etc/ega/ssl.key
      - BROKER_VERIFY_HOSTNAME=no
      - BROKER_VERIFY_PEER=yes
      - BROKER_CONNECTION=${MQ_CONNECTION}?${MQ_CONNECTION_PARAMS}
    volumes:
      - ./conf.ini:/etc/ega/conf.ini:ro
      - ./entrypoint.sh:/usr/local/bin/lega-entrypoint.sh
      - ./config/certs/finalize.ca.crt:/etc/ega/ssl.cert
      - ./config/certs/finalize.ca.key:/etc/ega/ssl.key
      - ./config/certs/root.ca.crt:/etc/ega/CA.cert
    restart: on-failure
    networks:
      - lega
    user: lega
    entrypoint: ["lega-entrypoint.sh"]
    command: ["ega-finalize"]
    # entrypoint: ["/bin/sleep", "1000000000000"]

EOF

if [[ ${ARCHIVE_BACKEND} == 's3' ]]; then
cat >> ${PRIVATE}/lega.yml <<EOF

  # Storage backend: S3
  minio:
    hostname: minio${HOSTNAME_DOMAIN}
    container_name: minio${HOSTNAME_DOMAIN}
    labels:
        lega_label: "archive"
    image: minio/minio:RELEASE.2018-12-19T23-46-24Z
    environment:
      - MINIO_ACCESS_KEY=${S3_ACCESS_KEY}
      - MINIO_SECRET_KEY=${S3_SECRET_KEY}
    volumes:
      - archive:/data
      - ./config/certs/s3.ca.crt:/root/.minio/certs/public.crt
      - ./config/certs/s3.ca.key:/root/.minio/certs/private.key
      - ./config/certs/root.ca.crt:/root/.minio/CAs/LocalEGA.crt
    restart: on-failure:3
    networks:
      - lega
    # ports:
    #   - "${DOCKER_PORT_s3}:9000"
    command: ["server", "/data"]
EOF
fi

if [[ ${REAL_CEGA} != 'yes' ]]; then

    #########################################################################
    # Specifying a fake Central EGA broker if requested
    #########################################################################
    cat > ${PRIVATE}/cega.yml <<EOF
############################################
# Faking Central EGA MQ and Users 
# on the lega network, for simplicity
############################################

version: '3.2'

services:

  cega-users:
    hostname: cega-users${HOSTNAME_DOMAIN}
    ports:
      - "15671:443"
    image: neicnordic/sda-base:latest
    container_name: cega-users${HOSTNAME_DOMAIN}
    labels:
        lega_label: "cega-users"
    volumes:
      - ../../tests/_common/users.py:/cega/users.py
      - ../../tests/_common/users:/cega/users
      - ./config/certs/cega-users.ca.crt:/cega/ssl.crt
      - ./config/certs/cega-users.ca.key:/cega/ssl.key
      - ./config/certs/root.ca.crt:/cega/CA.crt
    networks:
      - lega
    user: root
    entrypoint: ["python", "/cega/users.py", "0.0.0.0", "443", "/cega/users"]

  cega-mq:
    hostname: cega-mq${HOSTNAME_DOMAIN}
    environment:
      - RABBITMQ_CONFIG_FILE=/etc/rabbitmq/conf/cega
      - RABBITMQ_ENABLED_PLUGINS_FILE=/etc/rabbitmq/conf/cega.plugins
    ports:
      - "15670:15671"
      - "5670:5671"
    image: rabbitmq:3.7.8-management-alpine
    container_name: cega-mq${HOSTNAME_DOMAIN}
    labels:
        lega_label: "cega-mq"
    volumes:
      - ./config/cega.json:/etc/rabbitmq/conf/cega.json
      - ./config/cega.conf:/etc/rabbitmq/conf/cega.conf
      - ./config/cega.plugins:/etc/rabbitmq/conf/cega.plugins
      - ./config/certs/root.ca.crt:/etc/rabbitmq/ssl/root.ca.crt
      - ./config/certs/cega-mq.ca.crt:/etc/rabbitmq/ssl/cega-mq.ca.crt
      - ./config/certs/cega-mq.ca.key:/etc/rabbitmq/ssl/cega-mq.ca.key
    restart: on-failure:3
    networks:
      - lega
EOF
fi


#########################################################################
# Keeping a trace of if
#########################################################################

cat >> ${PRIVATE}/.trace <<EOF
#####################################################################
#
# Generated by bootstrap/boot.sh
#
#####################################################################
#
C4GH_PASSPHRASE           = ${C4GH_PASSPHRASE}
#
# Database users are 'lega_in' and 'lega_out'
DB_LEGA_IN_PASSWORD       = ${DB_LEGA_IN_PASSWORD}
DB_LEGA_OUT_PASSWORD      = ${DB_LEGA_OUT_PASSWORD}
#
# Central EGA mq and user credentials
CEGA_CONNECTION           = ${CEGA_CONNECTION}
CEGA_ENDPOINT_CREDS       = ${CEGA_USERS_CREDS}
#
S3_ACCESS_KEY             = ${S3_ACCESS_KEY}
S3_SECRET_KEY             = ${S3_SECRET_KEY}
#
DOCKER_PORT_inbox         = ${DOCKER_PORT_inbox}
DOCKER_PORT_mq            = ${DOCKER_PORT_mq}
DOCKER_PORT_s3            = ${DOCKER_PORT_s3}
#
# Local Message Broker (used by mq and inbox)
MQ_USER                   = ${MQ_USER}
MQ_PASSWORD               = ${MQ_PASSWORD}
MQ_CONNECTION             = ${MQ_CONNECTION}?${MQ_CONNECTION_PARAMS}
MQ_EXCHANGE               = cega
MQ_ROUTING_KEY            = files.inbox
EOF

task_complete "Bootstrap complete"
echo "Run: sudo chown 70 ${PRIVATE}/config/certs/db.ca.key"
echo "to fix ownership of db.ca.key file"
