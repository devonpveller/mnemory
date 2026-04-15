# Mnemory Backup & Restore

## How It Works

A lightweight Alpine sidecar container (`mnemory-backup`) runs alongside the main mnemory service. It uses `crond` to execute a nightly backup of the entire `/data` volume (Qdrant database, artifacts, and session state) into a compressed tarball stored in the `./backups/` directory on the host.

### What gets backed up

| Path | Contents |
|---|---|
| `/data/qdrant/` | Embedded Qdrant vector database (all 3 collections) |
| `/data/artifacts/` | Uploaded artifact files |
| `/data/sessions.db` | SQLite session database |

## Configuration

All settings are controlled via environment variables in `docker-compose.yaml` or a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `BACKUP_CRON` | `0 2 * * *` | Cron schedule (default: 2:00 AM daily) |
| `BACKUP_RETAIN_DAYS` | `7` | Number of days to retain old backups |

### Changing the schedule

Set `BACKUP_CRON` in your `.env` file or `docker-compose.yaml`:

```bash
# Every 6 hours
BACKUP_CRON=0 */6 * * *

# Every night at midnight
BACKUP_CRON=0 0 * * *

# Every Sunday at 3 AM
BACKUP_CRON=0 3 * * 0
```

## Usage

### Start with backups enabled

```bash
docker compose up -d
```

The `mnemory-backup` service starts automatically alongside the main service. Backups appear in `./backups/` on the host.

### Run a manual backup

```bash
docker exec mnemory-backup sh /scripts/backup.sh
```

### List backups

```bash
ls -lht ./backups/
```

### Check backup logs

```bash
docker logs mnemory-backup
```

## Restore

**Important**: Stop the mnemory container before restoring.

```bash
# 1. Stop mnemory
docker compose stop mnemory

# 2. Restore from a specific backup
docker run --rm \
  -v mnemory-data:/data \
  -v ./backups:/backups:ro \
  alpine sh -c "
    rm -rf /data/*
    tar xzf /backups/mnemory-backup-YYYYMMDD-HHMMSS.tar.gz -C /data
  "

# 3. Start mnemory
docker compose start mnemory
```

Replace `YYYYMMDD-HHMMSS` with the timestamp of the backup you want to restore.

### Using the restore script

Alternatively, use the included restore script:

```bash
docker compose stop mnemory

docker run --rm \
  -v mnemory-data:/data \
  -v ./backups:/backups:ro \
  -v ./backup/restore.sh:/restore.sh:ro \
  alpine sh /restore.sh /backups/mnemory-backup-YYYYMMDD-HHMMSS.tar.gz

docker compose start mnemory
```

## Disable backups

To run mnemory without the backup sidecar, use a profile or simply stop the service:

```bash
docker compose stop mnemory-backup
```
