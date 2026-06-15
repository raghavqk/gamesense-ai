#!/usr/bin/env python3
"""
Setup script for Local ML Pipeline
Downloads required models and verifies installation
"""
import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_python_version():
    """Check Python version >= 3.8"""
    if sys.version_info < (3, 8):
        logger.error("Python 3.8+ required")
        return False
    logger.info(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    return True


def install_dependencies():
    """Install required packages"""
    packages = [
        "ultralytics>=8.0.0",
        "easyocr>=1.7.0",
        "torch>=2.0.0",
        "opencv-python-headless",
        "numpy",
        "Pillow",
    ]
    
    logger.info("Installing dependencies...")
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            logger.info(f"✓ {package}")
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Failed to install {package}: {e}")
            return False
    
    return True


def download_yolo_model():
    """Download YOLOv8n model"""
    try:
        from ultralytics import YOLO
        logger.info("Downloading YOLOv8n model...")
        model = YOLO('yolov8n.pt')
        logger.info("✓ YOLOv8n model downloaded")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to download YOLO model: {e}")
        return False


def test_easyocr():
    """Test EasyOCR installation"""
    try:
        import easyocr
        logger.info("Initializing EasyOCR (this may take a minute)...")
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        logger.info("✓ EasyOCR initialized")
        return True
    except Exception as e:
        logger.error(f"✗ EasyOCR test failed: {e}")
        return False


def verify_pipeline():
    """Verify the local pipeline can be imported"""
    try:
        sys.path.insert(0, 'backend')
        from app.pipeline_local import LocalPipelineOrchestrator
        logger.info("✓ Local pipeline module importable")
        return True
    except Exception as e:
        logger.error(f"✗ Pipeline import failed: {e}")
        return False


def main():
    """Main setup function"""
    logger.info("=" * 60)
    logger.info("GameSense AI - Local ML Pipeline Setup")
    logger.info("=" * 60)
    
    steps = [
        ("Python version", check_python_version),
        ("Dependencies", install_dependencies),
        ("YOLO model", download_yolo_model),
        ("EasyOCR", test_easyocr),
        ("Pipeline module", verify_pipeline),
    ]
    
    results = []
    for name, func in steps:
        logger.info(f"\n{'='*40}")
        logger.info(f"Step: {name}")
        logger.info('='*40)
        success = func()
        results.append((name, success))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SETUP SUMMARY")
    logger.info("=" * 60)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status}: {name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        logger.info("\n✅ All checks passed! Local ML pipeline is ready.")
        logger.info("\nNext steps:")
        logger.info("1. Start the backend: uvicorn app.main:app --reload --port 8000")
        logger.info("2. Open frontend and select 'Local ML' mode")
        logger.info("3. Upload a gameplay video")
        return 0
    else:
        logger.error("\n❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
