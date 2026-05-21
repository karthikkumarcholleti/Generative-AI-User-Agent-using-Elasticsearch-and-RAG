"""
Phase 4 — Populate embedding field in Elasticsearch using GPU.

Reads all existing docs from ES via scroll API, generates all-MiniLM-L6-v2
embeddings for the content field, and bulk-updates the embedding field only.

Does NOT delete or recreate the index — all Phase 3 data is preserved.
Safe to stop and restart — skips docs that already have embeddings.

Run with GPUs free (backend stopped):
  pkill -f uvicorn
  python3 scripts/populate_embeddings.py
  # restart backend after
"""

import os
import sys
import time
import torch
import numpy as np
from elasticsearch import Elasticsearch, helpers

ES_HOST = "http://localhost:9200"
INDEX   = "patient_data"
BATCH   = 512   # docs per embedding batch — larger = faster on GPU
SCROLL  = "5m"


def main():
    # -----------------------------------------------------------------------
    # Device selection
    # -----------------------------------------------------------------------
    if torch.cuda.is_available():
        device = "cuda"
        n_gpus = torch.cuda.device_count()
        for i in range(n_gpus):
            free, total = torch.cuda.mem_get_info(i)
            print(f"  GPU {i}: {free/1e9:.1f} GB free / {total/1e9:.1f} GB total")
    else:
        device = "cpu"
        print("  WARNING: CUDA not available, using CPU (will be slow)")
    print(f"  Using device: {device}")

    # -----------------------------------------------------------------------
    # Load embedding model
    # -----------------------------------------------------------------------
    print("\nLoading all-MiniLM-L6-v2 ...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    print(f"  Model loaded on {device}")

    # -----------------------------------------------------------------------
    # Connect to ES
    # -----------------------------------------------------------------------
    es = Elasticsearch(ES_HOST, request_timeout=120)
    if not es.ping():
        sys.exit("ERROR: Cannot connect to Elasticsearch")

    total_docs = es.count(index=INDEX)["count"]
    print(f"\n  Total docs in index: {total_docs:,}")

    # Count already-embedded docs so we can skip them
    already = es.count(index=INDEX, body={"query": {"exists": {"field": "embedding"}}})["count"]
    print(f"  Already have embeddings: {already:,}")
    remaining = total_docs - already
    print(f"  Need to embed: {remaining:,}")

    if remaining == 0:
        print("\nAll docs already have embeddings. Nothing to do.")
        return

    # -----------------------------------------------------------------------
    # Scroll + embed + bulk update
    # -----------------------------------------------------------------------
    # Only scroll docs that are missing embeddings
    scroll_query = {
        "query": {"bool": {"must_not": {"exists": {"field": "embedding"}}}},
        "_source": ["content"],   # only need content + _id
    }

    page = es.search(index=INDEX, body=scroll_query, scroll=SCROLL, size=BATCH)
    scroll_id = page["_scroll_id"]
    hits = page["hits"]["hits"]

    processed = 0
    t0 = time.time()

    while hits:
        ids      = [h["_id"]                        for h in hits]
        contents = [h["_source"].get("content", "") for h in hits]

        # Generate embeddings for this batch
        embeddings = model.encode(
            contents,
            batch_size=BATCH,
            show_progress_bar=False,
            normalize_embeddings=True,   # cosine similarity = dot product after L2-norm
            convert_to_numpy=True,
        )

        # Bulk update — only write the embedding field
        actions = [
            {
                "_op_type": "update",
                "_index":   INDEX,
                "_id":      doc_id,
                "doc":      {"embedding": emb.tolist()},
            }
            for doc_id, emb in zip(ids, embeddings)
        ]
        for ok, info in helpers.parallel_bulk(es, actions, chunk_size=256, thread_count=2):
            if not ok:
                print(f"  WARN: {info}")

        processed += len(hits)
        elapsed   = time.time() - t0
        rate      = processed / elapsed if elapsed > 0 else 0
        eta_min   = (remaining - processed) / rate / 60 if rate > 0 else 0
        print(f"  Embedded {processed:,} / {remaining:,}  "
              f"({rate:.0f} docs/s | ETA {eta_min:.1f} min)", end="\r", flush=True)

        # Next scroll page
        page     = es.scroll(scroll_id=scroll_id, scroll=SCROLL)
        scroll_id = page["_scroll_id"]
        hits     = page["hits"]["hits"]

    es.clear_scroll(scroll_id=scroll_id)
    print(f"\n\nDone. Embedded {processed:,} docs in {(time.time()-t0)/60:.1f} min.")

    # Final verification
    final = es.count(index=INDEX, body={"query": {"exists": {"field": "embedding"}}})["count"]
    print(f"Docs with embedding: {final:,} / {total_docs:,}")
    if final < total_docs:
        print(f"WARNING: {total_docs - final:,} docs still missing embeddings — re-run to fill gaps.")


if __name__ == "__main__":
    main()
