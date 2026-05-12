"""
MinerU Extractor

Takes PDF URLs from scrapers, sends them to the MinerU task extraction API,
and extracts structured data from the PDFs.
"""

import requests
import time
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from loguru import logger as log

# ── Constants ──────────────────────────────────────────────────────────────────

MINERU_API_URL = "https://mineru.net/api/v4/extract/task"
MINERU_MODEL_VERSION = "vlm"

# ── Helper Functions ──────────────────────────────────────────────────────────


def parse_by_url(pdf_url: str, api_key: str):
    """
    Create a MinerU extraction task for the given PDF URL.

    Args:
        pdf_url: URL of the PDF to extract
        api_key: MinerU API key for authentication

    Returns:
        Task ID string for polling status
    """
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = {
        "url": pdf_url,
        "model_version": MINERU_MODEL_VERSION,
        # "language": "en",
        "enable_table": True,
    }

    res = requests.post(MINERU_API_URL, headers=headers, json=data, timeout=30)
    res.raise_for_status()

    task_id = res.json()["data"]["task_id"]
    msg = res.json()["msg"]

    log.info(f"MinerU task created: {task_id}. Message: {msg}")

    return task_id


def get_task_status(
    task_id: str, api_key: str, max_wait: int = 300, poll_interval: int = 5
):
    """
    Poll MinerU task status until completion or timeout.

    Args:
        task_id: MinerU task ID to check
        api_key: MinerU API key for authentication
        max_wait: Maximum wait time in seconds (default 300)
        poll_interval: Polling interval in seconds (default 5)

    Returns:
        Final task status string, or None if timeout
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{MINERU_API_URL}/{task_id}"
    start_time = time.time()

    while time.time() - start_time < max_wait:
        res = requests.get(url, headers=headers, timeout=30)
        res.raise_for_status()

        status = res.json()["data"]["state"]

        if status in (
            "pending",
            "queued",
            "running",
            "parsing",
            "converting",
            "format conversion in progress",
        ):
            log.info(f"MinerU task {task_id} status: {status}")

        elif status == "failed":
            error_msg = res.json()["data"].get("err_msg", "Unknown error")
            log.warning(f"MinerU task {task_id} failed: {error_msg}")
            return None

        else:
            log.info(f"MinerU task {task_id} completed with status: {status}")
            return status

        time.sleep(poll_interval)

    log.warning(f"MinerU task {task_id} timeout after {max_wait}s")
    return None


def get_parsed_zip(task_id: str, api_key: str, extract_to: str):
    """
    Download and optionally extract the parsed ZIP file from MinerU.

    Args:
        task_id: MinerU task ID
        api_key: MinerU API key for authentication
        extract_to: Optional directory path to extract files

    Returns:
        Dictionary with file_list, zip_buffer, and extraction status
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{MINERU_API_URL}/{task_id}"

    res = requests.get(url, headers=headers, timeout=30)
    res.raise_for_status()

    data = res.json()["data"]
    full_zip_url = data["full_zip_url"]

    log.info(f"Downloaded MinerU ZIP URL: {full_zip_url}")

    # Download ZIP in memory
    log.info("Downloading MinerU parsed ZIP...")
    zip_response = requests.get(full_zip_url, headers=headers, stream=True, timeout=120)
    zip_response.raise_for_status()

    zip_buffer = BytesIO()
    for chunk in zip_response.iter_content(chunk_size=8192):
        zip_buffer.write(chunk)

    zip_buffer.seek(0)

    with ZipFile(zip_buffer, "r") as zip_file:
        file_list = zip_file.namelist()
        log.info(f"MinerU ZIP contains {len(file_list)} files")

        # Extract if directory provided
        if extract_to:
            import os

            os.makedirs(extract_to, exist_ok=True)
            resolved_base = Path(extract_to).resolve()
            for member in zip_file.infolist():
                member_path = (resolved_base / member.filename).resolve()
                if not member_path.is_relative_to(resolved_base):
                    raise ValueError(
                        f"Path traversal detected in ZIP: {member.filename}"
                    )
            zip_file.extractall(extract_to)
            log.info(f"MinerU files extracted to: {extract_to}")

        return {
            "file_list": file_list,
            "zip_buffer": zip_buffer,
            "extract_dir": extract_to,
        }


# ── Core Functions ────────────────────────────────────────────────────────────


def mineru_workflow(pdf_url: str, api_key: str, extract_dir: str):
    """
    Complete MinerU workflow: create task → wait for completion → download.

    Args:
        pdf_url: URL of PDF to extract
        api_key: MinerU API key for authentication
        extract_dir: Optional directory to extract files

    Returns:
        Dictionary with extraction results, or None if failed
    """
    try:
        # Create extraction task
        task_id = parse_by_url(pdf_url, api_key)

        # Wait for completion
        task_status = get_task_status(task_id, api_key)

        if not task_status:
            log.error(f"MinerU task {task_id} failed or timed out")
            return None

        # Download and extract results
        result = get_parsed_zip(task_id, api_key, extract_dir)
        return result

    except requests.exceptions.RequestException as e:
        log.error(f"MinerU API request failed: {e}")
        return None
    except Exception as e:
        log.error(f"MinerU workflow failed: {e}")
        return None
