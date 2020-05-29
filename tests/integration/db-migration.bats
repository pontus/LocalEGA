#!/usr/bin/env bats

load ../_common/helpers

function setup () {
  true  
}

function teardown () {
  true
}

@test "Check database has migrations" {
    wait_db
    legarun query_db local_ega.dbschema_version 'count(version)'

    schemas_applied=$(echo "$output" | grep '^\s*[0-9]$')
    [ 1 -le "$schemas_applied" ]
}

@test "Check database upgrade of empty dump" {

    dumpfile=/tmp/current_db.dump.$$
    
    # Disable authentication for local connections
    run docker exec localega-db.default bash -c 'sed -i -e "2 i local all all trust" "${PGDATA}/pg_hba.conf"'

    # Restart for effect
    run docker stop localega-db.default
    run docker start localega-db.default

    legarun wait_db

    # Save current contents
    run docker exec -i localega-db.default pg_dumpall -c -h /var/lib/postgresql/ > "$dumpfile"

    run docker exec -i localega-db.default psql -h /var/lib/postgresql < tests/_common/db/empty_db.dump

    run docker stop localega-db.default
    run docker start localega-db.default

    legarun wait_db
    legarun query_db local_ega.dbschema_version 'max(version)' 

    schema_version=$(echo "$output" | grep '^\s*[0-9]$')

    # Restore old contents
    run docker exec -i localega-db.default psql -h /var/lib/postgresql < "$dumpfile"
    
    [ 1 -le "$schema_version" ]
}

@test "Check database upgrade of (not-empty) dump" {

    dumpfile=/tmp/current_db.dump.$$

    # Disable authentication for local connections
    run docker exec localega-db.default bash -c 'sed -i -e "2 i local all all trust" "${PGDATA}/pg_hba.conf"'

    # Restart for effect
    run docker stop localega-db.default
    run docker start localega-db.default

    legarun wait_db

    # Save current contents
    run docker exec -i localega-db.default pg_dumpall -c -h /var/lib/postgresql/ > "$dumpfile"

    run docker exec -i localega-db.default psql -h /var/lib/postgresql < tests/_common/db/data_db.dump

    run docker stop localega-db.default
    run docker start localega-db.default

    legarun wait_db
    legarun query_db local_ega.dbschema_version 'max(version)' 

    schema_version=$(echo "$output" | grep '^\s*[0-9]$')

    # Restore old contents
    run docker exec -i localega-db.default psql -h /var/lib/postgresql < "$dumpfile"

    [ 1 -le "$schema_version" ]
}
