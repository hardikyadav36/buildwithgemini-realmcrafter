import pytest
from unittest.mock import MagicMock, patch
from app.video_tools import generate_item_video, BUCKET_NAME, MODEL_NAME, LOCATION

@pytest.mark.asyncio
async def test_generate_item_video_success():
    mock_genai_client = MagicMock()
    mock_interaction = MagicMock()
    mock_output_video = MagicMock()
    mock_output_video.data = "dGVzdF92aWRlb19ieXRlcw==" # base64 of b"test_video_bytes"
    mock_output_video.mime_type = "video/mp4"
    mock_interaction.output_video = mock_output_video
    mock_genai_client.interactions.create.return_value = mock_interaction

    mock_storage_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    mock_tool_context = MagicMock()

    with patch("app.video_tools.genai.Client", return_value=mock_genai_client), \
         patch("app.video_tools.storage.Client", return_value=mock_storage_client):
        result = await generate_item_video(
            item_name="Frostfang Bow",
            visual_description="A crystalline recurve bow dripping with mist and glowing with azure frost.",
            tool_context=mock_tool_context,
        )

    assert result["status"] == "success"
    assert result["item_name"] == "Frostfang Bow"
    assert result["public_url"].startswith(f"https://storage.googleapis.com/{BUCKET_NAME}/videos/frostfang_bow_")
    assert result["public_url"].endswith(".mp4")
    mock_blob.upload_from_string.assert_called_once_with(b"test_video_bytes", content_type="video/mp4")
    mock_tool_context.save_artifact.assert_called_once()
