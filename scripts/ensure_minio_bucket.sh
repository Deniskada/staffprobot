#!/bin/bash
# Создаёт бакет staffprobot-media в MinIO (dev). Запускать после docker compose up.
# Использует mc в одноразовом контейнере в той же сети.

set -e
NETWORK="${STAFFPROBOT_NETWORK:-staffprobot_dev_network}"
BUCKET="${MINIO_BUCKET:-staffprobot-media}"

docker run --rm --network "$NETWORK" --entrypoint sh minio/mc -c "
  mc alias set local http://minio:9000 minioadmin minioadmin &&
  mc mb local/$BUCKET --ignore-existing &&
  echo \"Bucket $BUCKET ready.\"
"
