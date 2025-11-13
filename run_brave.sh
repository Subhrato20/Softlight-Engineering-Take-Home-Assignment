#!/usr/bin/env bash
pkill -f "Brave Browser" || true

/Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser \
  --remote-debugging-port=9222 \
  --profile-directory="Default" \
  --no-first-run \
  --no-default-browser-check \
  --disable-features=OptimizationGuideModelDownloading

