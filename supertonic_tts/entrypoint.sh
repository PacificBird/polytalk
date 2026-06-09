#!/bin/sh
set -eu

mkdir -p /data/cache /data/home
chown -R supertonic:supertonic /data

exec gosu supertonic "$@"
