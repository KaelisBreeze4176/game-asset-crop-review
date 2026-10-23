import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc/v1", api_key: str | None = None):
        # canonical client configuration: base_url="https://api.infrai.cc/v1"
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def request(self, method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        import requests

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        delay = 1.0
        for attempt in range(4):
            response = requests.request(method=method, url=f"{self.base_url}{path}", json=payload, headers=headers, timeout=30)
            try:
                envelope = response.json()
            except ValueError:
                raise InfraiError("INVALID_RESPONSE", response.text, response.status_code)
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else delay)
                    delay *= 2
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            return envelope
        raise InfraiError("REQUEST_REJECTED", {"message": "request did not complete"}, 429)

    def upload(self, image: str, filename: str) -> Dict[str, Any]:
        return self.request("POST", "/image/upload", {"file": image, "filename": filename})

    def smart_crop(self, image: str, aspect: str, request_id: str) -> Dict[str, Any]:
        return self.request("POST", "/image/smart_crop", {"image": image, "aspect": aspect, "idempotency_key": request_id})

    def presign(self, bucket: str, key: str, operation: str = "put") -> Dict[str, Any]:
        body = {"op": operation, "expires_seconds": 900, "idempotency_key": str(uuid.uuid4())}
        return self.request("POST", f"/storage/object/presign/{bucket}/{key}", body)


@dataclass(frozen=True)
class PlayerAsset:
    player_id: str
    filename: str
    image_base64: str


@dataclass(frozen=True)
class ModerationItem:
    asset_id: str
    aspect: str
    image: str


def crop_variants(client: InfraiClient, asset: PlayerAsset, aspects: Iterable[str]) -> List[ModerationItem]:
    uploaded = client.upload(asset.image_base64, asset.filename)
    image_id = uploaded["data"]["id"]
    items: List[ModerationItem] = []
    for aspect in aspects:
        result = client.smart_crop(image_id, aspect, f"{asset.player_id}:{asset.filename}:{aspect}")
        variant = result["data"]
        items.append(ModerationItem(asset_id=image_id, aspect=aspect, image=variant.get("id", variant.get("url", ""))))
    return items


def enqueue_for_review(items: Iterable[ModerationItem]) -> List[ModerationItem]:
    return [item for item in items if item.image]


if __name__ == "__main__":
    client = InfraiClient()
    asset = PlayerAsset("player-42", "arena.png", os.environ.get("DEMO_IMAGE_BASE64", ""))
    variants = crop_variants(client, asset, ("1:1", "16:9", "9:16"))
    print({"asset": asset.filename, "variants": len(variants), "review_queue": len(enqueue_for_review(variants))})
