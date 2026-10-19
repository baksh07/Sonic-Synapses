from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import json
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
app = FastAPI(
    title="FIR JSON Service",
    description="Service to retrieve FIR JSON data by unique ID",
    version="1.0.0"
)

# Configuration
FIR_REPORTS_DIR = "/mnt/data/DUMP/pipecat_latest/pipecat_version_2/pipecat/examples/websocket/Shakti_cop/fir_reports"  # Change this to match your directory


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "FIR JSON Service"}



@app.get("/fir/latest")
async def get_latest_fir():
    """
    Get the latest FIR report based on timestamp
    
    Returns:
        Dict: The JSON data from the latest file
        
    Raises:
        HTTPException: If no files found or cannot be read
    """
    try:
        print("inside latest endpoint")
        reports_dir = Path(FIR_REPORTS_DIR)
        print(reports_dir)
        json_files = [
        f for f in os.listdir(reports_dir)
            if f.endswith('.json') and len(f) >= 19  # format: 20250804_193343.json
        ]

        if not json_files:
            raise FileNotFoundError("No JSON files found in the specified folder.")

        # Sort files by datetime parsed from filename
        json_files.sort(
            key=lambda f: datetime.strptime(f[:15], "%Y%m%d_%H%M%S"),
            reverse=True
        )

        latest_file = json_files[0]
        latest_file_path = os.path.join(reports_dir, latest_file)

        with open(latest_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid JSON format in latest file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving latest FIR: {str(e)}"
        )
    

if __name__ == "__main__":
    import uvicorn
    
    # Create reports directory if it doesn't exist
    os.makedirs(FIR_REPORTS_DIR, exist_ok=True)
    
    # Run the server
    uvicorn.run(
        "get_fir_Details:app",  # Import string format
        host="0.0.0.0", 
        port=7879,
        reload=True
    )