# backend/tests/test_transcribe.py

import os
import pytest
from app import transcribe_video

@pytest.fixture
def test_video(tmp_path):
    """
    Kopieer een klein samplebestand uit uploads/ naar een tijdelijke map.
    """
    sample = os.path.join(os.path.dirname(__file__), os.pardir, "uploads", "sample.mp4")
    dest = tmp_path / "test.mp4"
    dest.write_bytes(open(sample, "rb").read())
    return str(dest)

def test_transcribe_basic(test_video):
    """
    Controleert dat transcriptie een niet-lege string oplevert.
    """
    text = transcribe_video(test_video)
    assert isinstance(text, str)
    assert len(text) > 0
