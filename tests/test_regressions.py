import importlib.util
from pathlib import Path
import numpy as np
import cv2

def load_service():
    path=Path(__file__).resolve().parents[1]/"python-microservice"/"app.py"
    spec=importlib.util.spec_from_file_location("flowforge_service",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_import_does_not_start_network_services():
    service=load_service()
    assert service.ch_client is None
    assert service.rtsp_processor is None

def test_broken_images_count_as_errors(tmp_path):
    service=load_service()
    (tmp_path/"broken.jpg").write_bytes(b"broken")
    processor=service.ImageBatchProcessor()
    processor.process_directory(str(tmp_path))
    assert processor.get_stats()=={"images_processed":0,"processing_errors":1}
