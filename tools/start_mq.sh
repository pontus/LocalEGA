#!/usr/bin/env bash

CONTAINER=ega-mq
DOCKER_EXEC="docker exec -it ${CONTAINER}"

# Kill the previous container
docker kill ${CONTAINER} || true #&& docker rm  ${CONTAINER}

# Starting RabbitMQ with docker
docker run -it --rm -d --hostname localhost -p 4369:4369 -p 5671:5671 -p 5672:5672 -p 15671:15671 -p 15672:15672 -p 25672:25672 --name ${CONTAINER} rabbitmq:management

echo "Waiting 10 seconds for the container to start"
sleep 10

# Updating it
${DOCKER_EXEC} rabbitmqctl set_disk_free_limit 1GB

PARAMS='-i -u guest:guest -H "content-type:application/json"'
# Create the exchange
curl $PARAMS -X PUT -d '{"type":"topic","durable":true}' http://localhost:15672/api/exchanges/%2f/lega

# Create the queues
curl $PARAMS -X PUT -d '{"durable":true}' http://localhost:15672/api/queues/%2f/tasks
curl $PARAMS -X PUT -d '{"durable":true}' http://localhost:15672/api/queues/%2f/completed
# curl $PARAMS -X PUT -d '{"durable":true}' http://localhost:15672/api/queues/%2f/errors-ega
# curl $PARAMS -X PUT -d '{"durable":true}' http://localhost:15672/api/queues/%2f/errors-users

# Binding them to the amq.topic exchange
curl $PARAMS -X POST -d '{"routing_key":"lega.task"}' http://localhost:15672/api/bindings/%2f/e/lega/q/tasks
curl $PARAMS -X POST -d '{"routing_key":"lega.complete"}' http://localhost:15672/api/bindings/%2f/e/lega/q/completed
curl $PARAMS -X POST -d '{"routing_key":"lega.done"}' http://localhost:15672/api/bindings/%2f/e/lega/q/tasks
# curl $PARAMS -X POST -d '{"routing_key":"lega.error.all"}' http://localhost:15672/api/bindings/%2f/e/lega/q/errors-ega
# curl $PARAMS -X POST -d '{"routing_key":"lega.error.user"}' http://localhost:15672/api/bindings/%2f/e/lega/q/errors-users
