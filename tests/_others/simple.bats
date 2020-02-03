#!/usr/bin/env bats

load ../_common/helpers

# CEGA_CONNECTION and CEGA_USERS_CREDS should be already set,
# when this script runs

function setup() {

    # Defining the TMP dir
    TESTFILES=${BATS_TEST_FILENAME}.d
    mkdir -p "$TESTFILES"

    # Start an SSH-agent for this env
    eval $(ssh-agent) &>/dev/null
    # That adds SSH_AUTH_SOCK and SSH_AUTH_PID to this env

    [[ -z "${SSH_AGENT_PID}" ]] && echo "Could not start the local ssh-agent" 2>/dev/null && exit 2

    # Test user
    TESTUSER=dummy
    load_into_ssh_agent ${TESTUSER}
    [[ $? != 0 ]] && echo "Error loading the test user into the local ssh-agent" >&2 && exit 3

    TESTUSER_SECKEY=$(get_user_seckey ${TESTUSER})
    TESTUSER_PASSPHRASE=$(get_user_passphrase ${TESTUSER})

    echo "Test user sec key: ${TESTUSER_SECKEY}"
    echo "Test user passphrase: ${TESTUSER_PASSPHRASE}"

    # Find inbox port mapping. Usually 2222:9000
    INBOX_PORT="2222"
    # legarun docker port inbox 9000
    # [ "$status" -eq 0 ]
    # INBOX_PORT=${output##*:}
    LEGA_SFTP="sftp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -P ${INBOX_PORT}"
}

function teardown() {
    rm -rf ${TESTFILES}

    # Kill an SSH-agent for this env
    [[ -n "${SSH_AGENT_PID}" ]] && kill -TERM "${SSH_AGENT_PID}"

    # unset TESTUSER
    # unset TESTUSER_SECKEY
}

# Ingesting a 1 MB file
# ----------------------
# A message should be found in the completed queue

@test "Ingest properly a test file" {
    
    lega_ingest $(uuidgen) 1 v1.files.completed /dev/urandom
}
