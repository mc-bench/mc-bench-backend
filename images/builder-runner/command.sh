#! /bin/bash
set -e

cp /build-scripts/build-script.js build-script.js

xvfb-run -a node build-script.js
exit_status=$?
pkill Xvfb || true
exit $exit_status