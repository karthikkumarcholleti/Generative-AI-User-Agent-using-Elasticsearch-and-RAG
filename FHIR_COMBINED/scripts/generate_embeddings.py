"""
Generate embeddings for all patient_data ES documents using base conda Python.
Run with: /home/kchollet/miniconda3/bin/python3 scripts/generate_embeddings.py

Uses sentence-transformers (all-MiniLM-L6-v2, 384-dim) on GPU.
Reads 'content' field from each ES doc, writes 'embedding' vector back.
"""

import time
import torch
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch, helpers

ES_HOST  = "http://localhost:9200"
INDEX    = "patient_data"
BATCH    = 512   # docs per ES scroll page + encode batch
MODEL_ID = "all-MiniLM-L6-v2"

def run():
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    print(f"Loading model {MODEL_ID}...")
    model = SentenceTransformer(MODEL_ID, device=device)

    es = Elasticsearch(ES_HOST, request_timeout=120)
    if not es.ping():
        raise RuntimeError(f"Cannot connect to ES at {ES_HOST}")

    total = es.count(index=INDEX)["count"]
    print(f"Total docs to embed: {total:,}")

    t0 = time.time()
    done = 0
    errors = 0

    # Scroll through all docs, batch-encode, bulk-update
    scroll = es.search(
        index=INDEX,
        scroll="10m",
        size=BATCH,
        _source=["content"],
        body={"query": {"match_all": {}}},
    )
    sid = scroll["_scroll_id"]

    while True:
        hits = scroll["hits"]["hits"]
        if not hits:
            break

        ids    = [h["_id"]                            for h in hits]
        texts  = [h["_source"].get("content") or ""   for h in hits]

        vecs = model.encode(texts, batch_size=BATCH, show_progress_bar=False,
                            convert_to_numpy=True, normalize_embeddings=True)

        actions = [
            {
                "_op_type": "update",
                "_index":   INDEX,
                "_id":      doc_id,
                "doc":      {"embedding": vec.tolist()},
            }
            for doc_id, vec in zip(ids, vecs)
        ]

        for ok, info in helpers.parallel_bulk(es, actions, chunk_size=BATCH,
                                              thread_count=2, raise_on_error=False):
            if not ok:
                errors += 1

        done += len(hits)
        elapsed = time.time() - t0
        rate = done / elapsed
        eta  = (total - done) / rate if rate > 0 else 0
        print(f"  {done:,}/{total:,} | {rate:.0f} docs/sec | ETA {eta/60:.1f} min",
              flush=True)

        scroll = es.scroll(scroll_id=sid, scroll="10m")

    es.clear_scroll(scroll_id=sid)
    elapsed = time.time() - t0
    print(f"\nDone: {done:,} embedded, {errors} errors, {elapsed/60:.1f} min total")

if __name__ == "__main__":
    run()
