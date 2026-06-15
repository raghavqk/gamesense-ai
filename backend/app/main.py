"""
GameSense AI - Hardened Backend API
Multi-Signal Pipeline with Validation Engine
"""
import os
import sys
import json
import asyncio
import tempfile
import logging
import traceback
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

from app.coach.groq_coach import ask_groq, test_groq_connection

# Configuration
MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1GB max upload (gameplay videos can be large)
REQUEST_TIMEOUT = 600  # 10 minutes for large file processing


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("[GameSense AI] Starting up...")
    # Verify API keys
    if not os.environ.get("GROQ_API_KEY"):
        logger.warning("[WARN] GROQ_API_KEY not set - vision analysis will fail")
    yield
    logger.info("[GameSense AI] Shutting down...")


app = FastAPI(
    title="GameSense AI v4",
    description="Multi-Signal Gameplay Video Analytics with Validation Engine",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if os.environ.get("DEBUG") else "An unexpected error occurred",
        }
    )


def safe_json_response(data: dict, status_code: int = 200) -> JSONResponse:
    """Safely create JSON response with proper serialization"""
    try:
        # Test serialization
        json.dumps(data)
        return JSONResponse(content=data, status_code=status_code)
    except (TypeError, ValueError) as e:
        logger.error(f"JSON serialization error: {e}")
        # Convert to serializable format
        sanitized = json.loads(json.dumps(data, default=str))
        return JSONResponse(content=sanitized, status_code=status_code)


@app.post("/api/chat")
async def chat(body: dict):
    """AI coach chat endpoint — Groq-powered"""
    try:
        question = body.get("question", "").strip()
        context  = body.get("analysis_context", {})
        # Runtime API key passed from frontend (overrides env var)
        api_key  = body.get("api_key", "").strip() or None

        if not question:
            return safe_json_response({
                "success": False,
                "error": "No question provided",
            }, 400)

        answer = ask_groq(question, context, api_key=api_key)

        return safe_json_response({
            "success": True,
            "data": {"answer": answer},
        })

    except Exception as e:
        logger.error(f"Chat failed: {e}", exc_info=True)
        return safe_json_response({
            "success": False,
            "error": f"Chat failed: {str(e)}",
        }, 500)


@app.post("/api/coach/test")
async def test_coach_connection(body: dict):
    """Test Groq API key validity without storing it server-side."""
    try:
        api_key = body.get("api_key", "").strip()
        result  = test_groq_connection(api_key)
        return safe_json_response({
            "success": result["success"],
            "data":    result,
        }, 200 if result["success"] else 400)
    except Exception as e:
        logger.error(f"Coach test failed: {e}", exc_info=True)
        return safe_json_response({
            "success": False,
            "error": f"Test failed: {str(e)}",
        }, 500)


@app.post("/api/pipeline/analyze-local")
async def analyze_local(
    file: UploadFile = File(...),
    game_title: str = Form("CS2"),
):
    """
    Local ML pipeline endpoint - No API calls required
    Uses YOLOv8 + EasyOCR for completely offline processing
    """
    import tempfile
    from app.pipeline_local.orchestrator_local import LocalPipelineOrchestrator
    
    request_id = id(file)
    tmp_path = None
    
    try:
        logger.info(f"[{request_id}] Local ML analysis request: game={game_title}, file={file.filename}")
        
        # Save uploaded file
        suffix = Path(file.filename).suffix or ".mp4"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        file_size_mb = len(content) / 1024 / 1024
        logger.info(f"[{request_id}] File size: {file_size_mb:.1f}MB")
        
        if file_size_mb > (MAX_FILE_SIZE / 1024 / 1024):
            return safe_json_response({
                "success": False,
                "error": f"File too large ({file_size_mb:.1f}MB > {MAX_FILE_SIZE/1024/1024:.0f}MB limit)",
            }, 413)
        
        # Run local pipeline
        logger.info(f"[{request_id}] Starting local ML pipeline...")
        orchestrator = LocalPipelineOrchestrator()
        
        result = await orchestrator.process_video(tmp_path, game_title)
        
        if result.get('success'):
            logger.info(f"[{request_id}] Local analysis complete: {result['data'].get('kills', 0)} kills")
            return safe_json_response({
                "success": True,
                "data": result['data'],
                "confidence": result['data'].get('detection_confidence', 0),
                "pipeline": "local_ml_v1",
            })
        else:
            logger.error(f"[{request_id}] Local analysis failed: {result.get('error')}")
            return safe_json_response({
                "success": False,
                "error": result.get('error', 'Local analysis failed'),
            }, 500)
        
    except Exception as e:
        logger.error(f"[{request_id}] Local analysis error: {e}", exc_info=True)
        return safe_json_response({
            "success": False,
            "error": f"Analysis failed: {str(e)}",
        }, 500)
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"[{request_id}] Cleanup failed: {e}")


@app.post("/api/analysis/compare")
async def compare_with_ground_truth(body: dict):
    """
    Compare detected stats with ground truth and return accuracy metrics
    """
    try:
        detected = body.get("detected_stats", {})
        ground_truth = body.get("ground_truth", {})
        
        if not detected or not ground_truth:
            return safe_json_response({
                "success": False,
                "error": "Both detected_stats and ground_truth required",
            }, 400)
        
        from app.pipeline_local.stats_aggregator import AccuracyEvaluator
        
        evaluator = AccuracyEvaluator()
        report = evaluator.evaluate(detected, ground_truth)
        
        return safe_json_response({
            "success": True,
            "data": {
                "detected_kills": report.detected_kills,
                "ground_truth_kills": report.ground_truth_kills,
                "kill_error": report.kill_error,
                "precision": round(report.precision, 3),
                "recall": round(report.recall, 3),
                "f1_score": round(report.f1_score, 3),
                "kill_accuracy_pct": round(report.kill_accuracy_pct, 1),
                "overall_score": round(report.overall_score, 1),
                "summary": evaluator.generate_summary(detected, ground_truth, report),
            }
        })
        
    except Exception as e:
        logger.error(f"Comparison failed: {e}", exc_info=True)
        return safe_json_response({
            "success": False,
            "error": f"Comparison failed: {str(e)}",
        }, 500)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return safe_json_response({
        "success": True,
        "status": "healthy",
        "version": "4.0.0",
        "pipeline": "multi-signal-v2",
    })


@app.get("/api/status")
async def status():
    """Detailed status endpoint"""
    return safe_json_response({
        "success": True,
        "version": "4.0.0",
        "pipeline_version": "multi-signal-v2",
        "features": [
            "multi_frame_validation",
            "kill_feed_ocr",
            "temporal_consistency",
            "stats_reconciliation",
            "auto_correction",
            "local_ml_pipeline",
            "ground_truth_comparison",
        ],
        "pipeline": {
            "endpoint": "/api/pipeline/analyze-local",
            "type": "local_ml",
            "description": "YOLOv8 + EasyOCR - No API calls",
        },
        "config": {
            "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
            "request_timeout_sec": REQUEST_TIMEOUT,
        },
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
