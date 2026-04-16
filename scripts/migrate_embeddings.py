#!/usr/bin/env python3
"""Re-embed all memories after changing the embedding model.

Run this INSIDE the mnemory container (or a container with the same
volume mounted) AFTER stopping the mnemory server.

Usage (from host):
    docker compose stop mnemory
    docker compose run --rm mnemory python /app/scripts/migrate_embeddings.py
    docker compose up -d mnemory

Environment variables (read from container env or override):
    EMBED_BASE_URL   - Embedding API base URL (e.g. http://ollama:11434/v1)
    EMBED_MODEL      - New embedding model name (e.g. qllama/bge-m3:latest)
    EMBED_DIMS       - New embedding dimensions (e.g. 1024)
    DATA_DIR         - Mnemory data directory (default: /data)
    QDRANT_COLLECTION - Collection name (default: mnemory)
"""

from __future__ import annotations

import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("migrate_embeddings")


def main() -> int:
    # ── Read config from environment ─────────────────────────────────
    embed_base_url = os.environ.get("EMBED_BASE_URL")
    embed_model = os.environ.get("EMBED_MODEL")
    embed_dims = int(os.environ.get("EMBED_DIMS", "0"))
    data_dir = os.environ.get("DATA_DIR", "/data")
    collection_name = os.environ.get("QDRANT_COLLECTION", "mnemory")
    qdrant_path = os.environ.get("QDRANT_PATH", os.path.join(data_dir, "qdrant"))

    if not embed_base_url or not embed_model or not embed_dims:
        logger.error(
            "Required env vars: EMBED_BASE_URL, EMBED_MODEL, EMBED_DIMS. "
            "Example:\n"
            "  EMBED_BASE_URL=http://openwebui:11434/v1\n"
            "  EMBED_MODEL=qllama/bge-m3:latest\n"
            "  EMBED_DIMS=1024"
        )
        return 1

    logger.info("=== Mnemory Embedding Migration ===")
    logger.info("Qdrant path:   %s", qdrant_path)
    logger.info("Collection:    %s", collection_name)
    logger.info("New model:     %s", embed_model)
    logger.info("New dims:      %d", embed_dims)
    logger.info("Embed API:     %s", embed_base_url)

    # ── Import dependencies ──────────────────────────────────────────
    from openai import OpenAI
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        Modifier,
        PointStruct,
        SparseVectorParams,
        VectorParams,
    )

    # Sparse embeddings (BM25, local — no API call)
    try:
        from fastembed import SparseTextEmbedding
        from qdrant_client.models import SparseVector

        sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        logger.info("BM25 sparse model loaded")
    except Exception as e:
        logger.warning("Could not load sparse model, skipping BM25: %s", e)
        sparse_model = None

    # ── Connect to Qdrant (local embedded mode) ─────────────────────
    logger.info("Opening Qdrant at %s ...", qdrant_path)
    client = QdrantClient(path=qdrant_path)

    collections = [c.name for c in client.get_collections().collections]
    if collection_name not in collections:
        logger.error("Collection '%s' not found. Available: %s", collection_name, collections)
        client.close()
        return 1

    # ── Check for leftover backup from a failed previous run ─────────
    backup_name = f"_migration_backup_{collection_name}"
    info = client.get_collection(collection_name)
    total = info.points_count or 0

    if total == 0 and backup_name in collections:
        backup_info = client.get_collection(backup_name)
        backup_count = backup_info.points_count or 0
        if backup_count > 0:
            logger.info(
                "Main collection is empty but backup '%s' has %d points — "
                "resuming from previous failed migration",
                backup_name,
                backup_count,
            )
            source_collection = backup_name
            total = backup_count
        else:
            logger.info("Nothing to migrate — both collections are empty")
            client.close()
            return 0
    elif total == 0:
        logger.info("Nothing to migrate — collection is empty")
        client.close()
        return 0
    else:
        source_collection = collection_name

    logger.info("Found %d memories to migrate (source: %s)", total, source_collection)

    logger.info("Step 1/4: Reading all memories from '%s' ...", source_collection)
    all_points = []
    offset = None
    BATCH = 256

    while True:
        points, next_offset = client.scroll(
            collection_name=source_collection,
            limit=BATCH,
            offset=offset,
            with_payload=True,
            with_vectors=True,  # Keep sparse vectors if present
        )
        all_points.extend(points)
        logger.info("  Read %d / %d memories", len(all_points), total)
        if next_offset is None:
            break
        offset = next_offset

    logger.info("Read %d memories total", len(all_points))

    # ── Backup: create temp collection (skip if resuming from backup) ─
    temp_name = f"_migration_backup_{collection_name}"
    if source_collection == temp_name:
        logger.info("Already reading from backup — skipping backup step")
    else:
        if temp_name in collections:
            logger.info("Removing previous backup collection '%s'", temp_name)
            client.delete_collection(temp_name)

        logger.info("Step 2/4: Creating backup collection '%s' ...", temp_name)
        # Read original config to preserve it in backup
        orig_info = client.get_collection(collection_name)
        orig_dense = orig_info.config.params.vectors
        orig_sparse = orig_info.config.params.sparse_vectors
        client.create_collection(
            collection_name=temp_name,
            vectors_config=orig_dense,
            sparse_vectors_config=orig_sparse or {},
        )

        # Copy all points to backup
        for i in range(0, len(all_points), BATCH):
            batch = all_points[i : i + BATCH]
            structs = []
            for p in batch:
                structs.append(
                    PointStruct(
                        id=p.id,
                        vector=p.vector,
                        payload=p.payload,
                    )
                )
            client.upsert(collection_name=temp_name, points=structs)
            logger.info("  Backed up %d / %d", min(i + BATCH, len(all_points)), len(all_points))

        backup_info = client.get_collection(temp_name)
        if (backup_info.points_count or 0) < len(all_points):
            logger.error(
                "Backup verification failed: expected %d, got %d. Aborting.",
                len(all_points),
                backup_info.points_count,
            )
            client.close()
            return 1

        logger.info("Backup verified: %d points", backup_info.points_count)

    # ── Recreate collection with new dimensions ──────────────────────
    logger.info("Step 3/4: Recreating collection with %d dimensions ...", embed_dims)
    client.delete_collection(collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=embed_dims,
            distance=Distance.COSINE,
        ),
        sparse_vectors_config={
            "bm25": SparseVectorParams(modifier=Modifier.IDF),
        },
    )
    logger.info("Collection recreated with dims=%d", embed_dims)

    # ── Re-embed and insert ──────────────────────────────────────────
    logger.info("Step 4/4: Re-embedding %d memories with %s ...", len(all_points), embed_model)

    embed_client = OpenAI(
        api_key=os.environ.get("LLM_API_KEY", os.environ.get("EMBED_API_KEY", "ollama")),
        base_url=embed_base_url,
    )

    EMBED_BATCH = 64  # Ollama handles smaller batches better
    start_time = time.monotonic()
    inserted = 0

    for i in range(0, len(all_points), EMBED_BATCH):
        batch = all_points[i : i + EMBED_BATCH]

        # Get text content for embedding
        texts = []
        for p in batch:
            text = (p.payload.get("data", "") if p.payload else "").replace("\n", " ")
            texts.append(text if text else "empty")

        # Dense embeddings via Ollama
        try:
            response = embed_client.embeddings.create(
                input=texts,
                model=embed_model,
            )
            dense_vectors = [item.embedding for item in response.data]
        except Exception as e:
            logger.error("Embedding API error at batch %d: %s", i // EMBED_BATCH, e)
            logger.error(
                "Backup preserved in collection '%s'. "
                "Fix the issue and re-run the script.",
                temp_name,
            )
            client.close()
            return 1

        # Verify dimensions match
        if dense_vectors and len(dense_vectors[0]) != embed_dims:
            logger.error(
                "Dimension mismatch! Model returned %d dims, expected %d. "
                "Update EMBED_DIMS to match your model's output.",
                len(dense_vectors[0]),
                embed_dims,
            )
            client.close()
            return 1

        # Sparse embeddings (local BM25)
        sparse_vectors = None
        if sparse_model is not None:
            try:
                results = list(sparse_model.embed(texts))
                sparse_vectors = [
                    SparseVector(
                        indices=r.indices.tolist(),
                        values=r.values.tolist(),
                    )
                    for r in results
                ]
            except Exception as e:
                logger.warning("Sparse embedding failed, skipping BM25: %s", e)

        # Build points with new vectors
        structs = []
        for j, p in enumerate(batch):
            vector = {"": dense_vectors[j]}
            if sparse_vectors and j < len(sparse_vectors):
                vector["bm25"] = sparse_vectors[j]
            structs.append(
                PointStruct(
                    id=p.id,
                    vector=vector,
                    payload=p.payload,
                )
            )

        client.upsert(collection_name=collection_name, points=structs)
        inserted += len(batch)

        elapsed = time.monotonic() - start_time
        rate = inserted / elapsed if elapsed > 0 else 0
        remaining = (len(all_points) - inserted) / rate if rate > 0 else 0
        logger.info(
            "  Re-embedded %d / %d (%.1f/s, ~%.0fs remaining)",
            inserted,
            len(all_points),
            rate,
            remaining,
        )

    # ── Verify ───────────────────────────────────────────────────────
    final_info = client.get_collection(collection_name)
    final_count = final_info.points_count or 0
    elapsed = time.monotonic() - start_time

    if final_count < len(all_points):
        logger.error(
            "Migration incomplete: %d / %d points inserted. "
            "Backup preserved in '%s'.",
            final_count,
            len(all_points),
            temp_name,
        )
        client.close()
        return 1

    logger.info("=== Migration Complete ===")
    logger.info("  Memories migrated: %d", final_count)
    logger.info("  New model: %s (%d dims)", embed_model, embed_dims)
    logger.info("  Time: %.1fs", elapsed)
    logger.info(
        "  Backup collection '%s' preserved. "
        "Delete it manually after verifying everything works:\n"
        "    docker compose exec mnemory python -c \""
        "from qdrant_client import QdrantClient; "
        "c = QdrantClient(path='/data/qdrant'); "
        "c.delete_collection('%s'); "
        "print('Backup deleted')\"",
        temp_name,
        temp_name,
    )

    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
