#!/usr/bin/env bash

set -e
#set -x

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
EGA=$HERE/..
[ -n "$1" ] && [ -d "$1" ] && EGA=$1

function cleanup {
    echo -e "\nStopping background jobs"
    kill -9 -"$$"
    exit 1
}
trap 'cleanup' INT TERM

echo "Starting EGA in $EGA"
pushd $EGA >/dev/null

# Start the frontend
ega-ingestion &
# Start the vault listener
ega-vault &
# re-start the GPG agent
$EGA/tools/start_agent.sh
# Start 2 workers
source $EGA/private/gpg/agent.env && ega-worker &
source $EGA/private/gpg/agent.env && ega-worker &
# Start the monitors
ega-monitor --sys &
ega-monitor --user &

popd >/dev/null
sleep 3
echo "EGA running..."

# Wait for everyone to finish
wait