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

"""Video generation tools using Google Omni model (gemini-omni-flash-preview) and Cloud Storage."""

import base64
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
MODEL_NAME = "gemini-omni-flash-preview"
LOCATION = "global"


async def generate_item_video(
    item_name: str,
    visual_description: str,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """Generate a short video animation for a fantasy RPG item or magical artifact using Google's Omni model (gemini-omni-flash-preview), save it as a session artifact, and upload it to public Cloud Storage.

    Args:
        item_name: Name of the item, weapon, armor, potion, or artifact (e.g. 'Sunfire Blade', 'Orb of Dragonkind').
        visual_description: Detailed visual description of the item appearance, motion, magical glow, rotating angles, or spell effects.
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
        f"Fantasy RPG magical item showcase: {item_name}. "
        f"{visual_description}. "
        "Cinematic 3D render, smooth rotation, glowing particles, detailed fantasy aesthetic, clean background."
    )

    try:
        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=prompt,
        )

        video_bytes = None
        mime_type = "video/mp4"

        if hasattr(interaction, "output_video") and interaction.output_video is not None:
            vid = interaction.output_video
            if hasattr(vid, "mime_type") and vid.mime_type:
                mime_type = vid.mime_type
            if hasattr(vid, "data") and vid.data:
                if isinstance(vid.data, str):
                    video_bytes = base64.b64decode(vid.data)
                elif isinstance(vid.data, bytes):
                    video_bytes = vid.data
            elif hasattr(vid, "uri") and vid.uri and vid.uri.startswith("gs://"):
                storage_client = storage.Client(project=PROJECT_ID)
                parts = vid.uri[5:].split("/", 1)
                src_bucket = storage_client.bucket(parts[0])
                src_blob = src_bucket.blob(parts[1])
                video_bytes = src_blob.download_as_bytes()

        if not video_bytes:
            return {
                "status": "error",
                "message": f"Model {MODEL_NAME} did not return video data for '{item_name}'.",
            }

        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", item_name.strip().lower()).strip("_") or "item"
        timestamp = int(time.time())
        filename = f"{safe_name}_{timestamp}.mp4"

        # 1. Save with tool_context.save_artifact so it shows up in Playground's Artifacts panel
        if tool_context is not None:
            try:
                artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
                save_call = tool_context.save_artifact(filename=filename, artifact=artifact_part)
                if inspect.isawaitable(save_call):
                    await save_call
            except Exception as art_err:
                logging.warning("Failed to save artifact in tool_context: %s", art_err)

        # 2. Upload same bytes directly to public Cloud Storage bucket without local file writes
        object_path = f"videos/{filename}"
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(object_path)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{object_path}"

        return {
            "status": "success",
            "item_name": item_name,
            "artifact_filename": filename,
            "public_url": public_url,
            "message": f"Generated video for '{item_name}' and published to {public_url}",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate video for '{item_name}': {str(e)}",
        }
