# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Image generation tools using Gemini 3.1 Flash Lite Image model and Cloud Storage."""

import inspect
import logging
import re
import time
from typing import Any, Dict

from google import genai
from google.adk.tools import ToolContext
from google.cloud import storage
from google.genai import types

PROJECT_ID = "qwiklabs-gcp-04-e94f2d8b9281"
BUCKET_NAME = "realmcrafter-assets-qwiklabs-gcp-04-e94f2d8b9281"
MODEL_NAME = "gemini-3.1-flash-lite-image"
LOCATION = "global"


async def generate_item_image(
    item_name: str,
    visual_description: str,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """Generate a fantasy illustration for an item or magical artifact using Gemini, save it as a session artifact, and upload it to public Cloud Storage.

    Args:
        item_name: Name of the item, weapon, armor, potion, or artifact (e.g. 'Sunfire Blade', 'Elixir of Healing').
        visual_description: Detailed visual description of the item appearance, materials, lighting, magical glow, and fantasy aesthetic.
        tool_context: ADK ToolContext injected automatically by the runtime for artifact storage.

    Returns:
        A dictionary containing the item name, artifact filename, and public https URL (https://storage.googleapis.com/<bucket>/<object>).
    """
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=LOCATION,
    )

    prompt = (
        f"Fantasy RPG item illustration: {item_name}. "
        f"{visual_description}. "
        "Detailed digital fantasy game concept art, high quality, vibrant lighting, isolated subject."
    )

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return {
                "status": "error",
                "message": f"Model {MODEL_NAME} did not return image data for '{item_name}'.",
            }

        ext = "jpg" if "jpeg" in mime_type.lower() else "png"
        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", item_name.strip().lower()).strip("_") or "item"
        timestamp = int(time.time())
        filename = f"{safe_name}_{timestamp}.{ext}"

        # 1. Save with tool_context.save_artifact so it shows up in Playground Artifacts panel
        if tool_context is not None:
            try:
                artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                save_call = tool_context.save_artifact(filename=filename, artifact=artifact_part)
                if inspect.isawaitable(save_call):
                    await save_call
            except Exception as art_err:
                logging.warning("Failed to save artifact in tool_context: %s", art_err)

        # 2. Upload same bytes directly to public Cloud Storage bucket without local file writes
        object_path = f"items/{filename}"
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(object_path)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{object_path}"

        return {
            "status": "success",
            "item_name": item_name,
            "artifact_filename": filename,
            "public_url": public_url,
            "message": f"Generated image for '{item_name}' and published to {public_url}",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Image generation failed: {str(e)}",
        }
