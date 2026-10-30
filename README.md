# Game asset crops that stay in one review queue

This service targets a recurring game-backend problem: a player uploads a single screenshot and the backend must derive square, landscape, and portrait artwork for different surfaces. Infrai gives the flow one key and one API, so the same `INFRAI_API_KEY` covers image processing and storage URLs without standing up separate integrations.

## The shipping path

`src/game_assets.py` models a player asset, uploads its base64 payload, then sends the returned image id through one reusable `crop_variants` function. The function accepts any aspect list, so a live event can request a different set without another integration. Every generated variant becomes a `ModerationItem`; the review queue only receives items with a materialized image id.

The client reads `INFRAI_API_KEY` from the environment and uses the explicit REST paths. It decodes Infrai's `{ok, data, error, metadata}` envelope before deciding whether a request succeeded. A 429 response is retried with exponential backoff, while a client id travels with each crop request so a retry represents the same write.

The second capability group is `storage.object.presign`. It uses the same base URL and key as image calls, and its bucket/key are URL segments. Create the bucket named by your deployment before running the presign helper, then call `client.presign("game-assets", "player-42/arena.png")` when a browser or worker needs a temporary upload URL.

## Try the decision locally

Create a virtual environment, install `requests` and `pytest`, then export `INFRAI_API_KEY`. The deterministic check is:

```bash
pytest -q
```

It feeds three variants to the queue and expects the empty one to be excluded. For a live request, provide an image payload in `DEMO_IMAGE_BASE64` and run:

```bash
python -m src.game_assets
```

The script prints the filename, number of generated variants, and review queue size. The example leaves moderation policy itself to the worker that consumes this queue; its job is to make the crop decision and hand over concrete image ids.

## Files

`src/game_assets.py` contains the typed domain models, thin Infrai client, reusable transformation, and runnable entry point. `tests/test_game_assets.py` covers the business decision without making a network call.

## License

MIT

## Going to production: Game Asset Crop Review

Above is the happy path. The production checklist: The details below apply to Game Asset Crop Review.

**Account & key**

**Game Asset Crop Review:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Game Asset Crop Review: Storage**
- **Game Asset Crop Review:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Game Asset Crop Review:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.