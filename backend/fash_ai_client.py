import requests
import uuid
import time
import json
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urljoin


def spoof_head() -> dict:
    # As close as possible to a real Chrome-on-Android fingerprint
    return {
        "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
    }


class HeadshotMaster:
    def __init__(self):
        # Random identity per instance
        self.rand = str(uuid.uuid4())

        # Configuration copied from the working script
        self.cfg = {
            "base_url": "https://api.headshotmaster.io/hsmaster/api",
            "origin": "https://headshotmaster.io",
            "referer": "https://headshotmaster.io/",
            "identity_id": self.rand,
            "ua": (
                "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36"
            ),
            "models": {
                "combiner": ["nano_banana", "seedream_4_2k", "pruna_image_editor"],
                "generator": ["headshot_master_ai"],
                "styles": [
                    "action_figure",
                    "3d_chibi_toy",
                    "barbie",
                    "realistic",
                    "pop_mart",
                    "lego",
                    "jellycat",
                    "craft_style",
                    "soft_toy",
                ],
            },
            "apps": {
                "COMBINER": "image_combiner",
                "FIGURE": "action_figure_generator",
            },
        }

        # Initial auth challenge token just uses the random UUID
        self.token = self.rand

        # Session with all spoofed headers
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Accept-Language": "id-ID",
                "Origin": self.cfg["origin"],
                "Referer": self.cfg["referer"],
                "User-Agent": self.cfg["ua"],
                "x-identity-id": self.cfg["identity_id"],
                **spoof_head(),
            }
        )

    # ------------------------
    # Validation
    # ------------------------

    def validate(self, opt: dict = None) -> Dict[str, Any]:
        if opt is None:
            opt = {}

        errors = []
        warnings = []

        valid_apps = list(self.cfg["apps"].values())

        if opt.get("app") and opt["app"] not in valid_apps:
            errors.append(
                {
                    "field": "app",
                    "value": opt["app"],
                    "valid": valid_apps,
                    "message": f"Invalid app. Use: {', '.join(valid_apps)}",
                }
            )

        all_models = self.cfg["models"]["combiner"] + self.cfg["models"]["generator"]
        if opt.get("model") and opt["model"] not in all_models:
            errors.append(
                {
                    "field": "model",
                    "value": opt["model"],
                    "valid": all_models,
                    "message": f"Invalid model. Use: {', '.join(all_models)}",
                }
            )

        if opt.get("style") and opt["style"] not in self.cfg["models"]["styles"]:
            errors.append(
                {
                    "field": "style",
                    "value": opt["style"],
                    "valid": self.cfg["models"]["styles"],
                    "message": f"Invalid style. Use: {', '.join(self.cfg['models']['styles'])}",
                }
            )

        # App-model compatibility warnings
        if (
            opt.get("app") == self.cfg["apps"]["COMBINER"]
            and opt.get("model")
            and opt["model"] not in self.cfg["models"]["combiner"]
        ):
            warnings.append(
                {
                    "field": "model",
                    "message": (
                        f"Model '{opt['model']}' may not work with '{opt['app']}'. "
                        f"Try: {', '.join(self.cfg['models']['combiner'])}"
                    ),
                }
            )

        if (
            opt.get("app") == self.cfg["apps"]["FIGURE"]
            and opt.get("model")
            and opt["model"] not in self.cfg["models"]["generator"]
        ):
            warnings.append(
                {
                    "field": "model",
                    "message": (
                        f"Model '{opt['model']}' may not work with '{opt['app']}'. "
                        f"Try: {', '.join(self.cfg['models']['generator'])}"
                    ),
                }
            )

        if not opt.get("image") and not opt.get("prompt"):
            errors.append(
                {
                    "field": "input",
                    "message": "Provide image or prompt",
                }
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    # ------------------------
    # Internal Request
    # ------------------------

    def _request(self, endpoint: str, data: dict = None, method: str = None) -> Any:
        url = urljoin(self.cfg["base_url"] + "/", endpoint.lstrip("/"))

        method = method or ("POST" if data else "GET")

        headers = {
            "x-auth-challenge": self.token,
        }
        if data:
            headers["Content-Type"] = "application/json"

        try:
            if method.upper() == "GET":
                r = self.session.get(url, params=data, headers=headers)
            else:
                r = self.session.post(url, json=data, headers=headers)

            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            error_data = {}
            try:
                error_data = e.response.json() if e.response else {}
            except Exception:
                error_data = {"message": str(e)}

            raise Exception(f"[API_ERR] {endpoint}: {json.dumps(error_data, ensure_ascii=False)}")

    # ------------------------
    # Auth
    # ------------------------

    def auth(self):
        print("🛡 Authenticating...")
        self.token = self.rand

        data = self._request("/sys/challenge/token")
        if data.get("data", {}).get("challenge_token"):
            self.token = data["data"]["challenge_token"]
            print("✅ Auth Token Secured")
        else:
            raise Exception("Failed to get challenge token")

    # ------------------------
    # Upload
    # ------------------------

    def upload(self, images: Union[str, bytes, List[Union[str, bytes]]]) -> List[str]:
        if not images:
            return []

        image_list = [images] if not isinstance(images, list) else images
        count = len(image_list)

        pre = self._request(f"/aigc/file/upload/request?f_suffix=png&count={count}&unsafe=1")
        slots = pre.get("data", [])

        if len(slots) != count:
            raise Exception("Upload slot count mismatch")

        uploaded_urls = []

        for i, img in enumerate(image_list):
            print(f"📤 Uploading {i+1}/{count}...")

            if isinstance(img, str) and img.startswith(("http://", "https://")):
                # Download remote image
                r = requests.get(img)
                r.raise_for_status()
                buffer = r.content
            else:
                # Assume bytes / file content
                buffer = img if isinstance(img, bytes) else bytes(img)

            put_url = slots[i]["put"]
            get_url = slots[i]["get"]

            resp = requests.put(put_url, data=buffer, headers={"Content-Type": "image/png"})
            resp.raise_for_status()

            uploaded_urls.append(get_url)

        return uploaded_urls

    # ------------------------
    # Poll
    # ------------------------

    def poll(self, creation_id: str, timeout: int = 180, interval: int = 3) -> Dict:
        print(f"📋 Monitoring: {creation_id}")

        start = time.time()
        while time.time() - start < timeout:
            res = self._request(f"/aigc/task/result/get?creation_id={creation_id}")
            data = res.get("data", {})
            status = data.get("status")

            if status == 2:
                return {"result": data.get("list", [])}
            if status == 3:
                raise Exception("Task failed")

            print(".", end="", flush=True)
            time.sleep(interval)

        raise TimeoutError("Polling timeout exceeded")

    # ------------------------
    # Generic Generate
    # ------------------------

    def generate(self, opt: dict = None) -> Dict[str, Any]:
        if opt is None:
            opt = {}

        validation = self.validate(opt)
        if not validation["valid"]:
            return {
                "success": False,
                "errors": validation["errors"],
                "warnings": validation["warnings"],
            }

        if validation["warnings"]:
            print("⚠️ Warnings:")
            print(json.dumps(validation["warnings"], indent=2, ensure_ascii=False))

        try:
            self.auth()

            media_urls = self.upload(opt.get("image"))

            payload = {
                "app_code": opt.get("app", self.cfg["apps"]["COMBINER"]),
                "model_code": opt.get("model", self.cfg["models"]["combiner"][0]),
                "media_urls": media_urls,
                "extra_params": {},
            }

            if opt.get("prompt"):
                payload["user_prompt"] = opt["prompt"]
            if opt.get("style"):
                payload["style"] = opt["style"]
            if opt.get("ratio"):
                payload["aspect_ratio"] = opt["ratio"]

            print(f"🚀 Task: {payload['app_code']} ({payload['model_code']})")

            task = self._request("/aigc/task/create", payload)
            cid = task.get("data", {}).get("creation_id")

            if not cid:
                raise Exception("No creation_id received")

            self.token = ""  # reset?

            result = self.poll(cid)

            return {
                "success": True,
                **result,
                "creation_id": cid,
                "app": payload["app_code"],
                "model": payload["model_code"],
                "style": opt.get("style"),
                "warnings": validation["warnings"],
            }

        except Exception as e:
            print(f"💀 Error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # ------------------------
    # Fash AI Convenience Method
    # ------------------------

    def fash_ai(
        self,
        image: Union[str, bytes],
        outfit: str,
        occasion: Optional[str] = None,
        fit: Optional[str] = None,
        color: Optional[str] = None,
        accessories: Optional[List[str]] = None,
        vibe: Optional[str] = None,
        variation: bool = False,
        ratio: str = "4:5",
    ) -> Dict[str, Any]:
        """
        High-level helper specialized for the Fash AI product:
        takes a single image + styling preferences and routes it
        through the generic `generate()` pipeline.
        """
        accessories_text = ", ".join(accessories) if accessories else "none"

        variation_line = ""
        if variation:
            variation_line = "Create a slightly different variation with unique fabric detailing."

        prompt = f"""
Transform the uploaded person into a high-resolution realistic fashion photoshoot.

Outfit type: {outfit}.
Occasion: {occasion or "modern setting"}.
Fit style: {fit or "natural fit"}.
Primary colors: {color or "balanced tones"}.
Accessories: {accessories_text}.
Fashion vibe: {vibe or "modern fashion aesthetic"}.

Keep the person's face unchanged.
Preserve identity and facial structure.
Maintain realistic body proportions.
Professional fashion lighting.
Ultra-detailed fabric textures.
Editorial quality image.
{variation_line}
"""

        # Delegate to the verbose, validated pipeline
        return self.generate(
            {
                "app": self.cfg["apps"]["COMBINER"],
                "model": self.cfg["models"]["combiner"][0],
                "prompt": prompt.strip(),
                "image": image,
                "ratio": ratio,
            }
        )


__all__ = ["HeadshotMaster"]


# ------------------------
# Example CLI Usage (generic)
# ------------------------

if __name__ == "__main__":
    api = HeadshotMaster()

    result = api.generate(
        {
            "app": "image_combiner",
            "model": "nano_banana",
            "prompt": "make his shirt color to white, no visual changes on the face, keep the same expression",
            "image": "https://example.com/person.jpg",
            # "ratio": "1:1",
        }
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


