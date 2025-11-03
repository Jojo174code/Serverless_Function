import uvicorn
import asyncio
import subprocess
import time
import math
import logging
import threading
import tempfile
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# --- 1. Configuration and Constants ---

# AWS Lambda-like pricing model
BASE_COST_PER_INVOCATION = 0.0000002
COST_PER_100MS = 0.000000208
# 10-minute execution limit (in seconds)
TIME_LIMIT_SECONDS = 600

# --- 2. Global State and Logging ---

app = FastAPI(
    title="FaaS Simulator",
    description="A mock serverless platform like AWS Lambda."
)

# Global variable to track aggregate cost.
# We need a lock to safely update it from multiple concurrent requests.
total_aggregate_cost = 0.0
cost_lock = threading.Lock()

# Configure logging to write to a file
# This satisfies the "Create a Log file" requirement
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    handlers=[
        logging.FileHandler("faas_simulator.log"),
        logging.StreamHandler() # Also print to console
    ]
)
log = logging.getLogger()

# --- 3. Pydantic Models (for API request/response) ---

class FunctionRequest(BaseModel):
    """The JSON body we expect for a function execution request."""
    code: str

class FunctionResponse(BaseModel):
    """The JSON response we will send back."""
    status: str
    result: Optional[str] = None
    stderr: Optional[str] = None
    execution_time_ms: float
    cost: float

class StatsResponse(BaseModel):
    """The JSON response for our /stats endpoint."""
    total_aggregate_cost: float
    
# --- 4. Core Logic Functions ---

def calculate_cost(duration_ms: float) -> float:
    """
    Simulates the cost calculation.
    - Requirement 3: Cost Calculation
    """
    # Round up to the nearest 100ms interval
    rounded_intervals = math.ceil(duration_ms / 100)
    
    time_cost = rounded_intervals * COST_PER_100MS
    total_cost = BASE_COST_PER_INVOCATION + time_cost
    
    # Update the global aggregate cost safely
    global total_aggregate_cost
    with cost_lock:
        total_aggregate_cost += total_cost
        
    return total_cost

def run_code_in_sandbox(code: str) -> dict:
    """
    Executes the user's code in a sandboxed subprocess.
    This function is *blocking* and will be run in a separate thread.
    
    - Requirement 1: Launch Runner
    - Requirement 4: Time Limit
    """
    start_time = time.perf_counter()
    
    # Create a temporary file to write the code to.
    # This is safer than using exec() or eval().
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        filepath = f.name
        
    try:
        # Execute the Python script as a separate process
        # This provides a basic level of sandboxing.
        # `capture_output=True` gets stdout/stderr
        # `timeout=...` enforces the 10-minute limit
        result = subprocess.run(
            ['python3', filepath],
            capture_output=True,
            text=True,
            timeout=TIME_LIMIT_SECONDS
        )
        
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        
        if result.returncode == 0:
            # Success
            return {
                "status": "success",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration_ms": duration_ms
            }
        else:
            # The user's code crashed (e.g., SyntaxError, Exception)
            return {
                "status": "error",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration_ms": duration_ms
            }
            
    except subprocess.TimeoutExpired as e:
        # Requirement 4: Terminate and log timeout
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        
        log.warning(f"Function TIMED OUT after {duration_ms:.2f}ms. Limit was {TIME_LIMIT_SECONDS}s.")
        
        return {
            "status": "timeout",
            "stdout": e.stdout if e.stdout else "",
            "stderr": f"Execution failed: Timeout after {TIME_LIMIT_SECONDS} seconds.",
            "duration_ms": duration_ms
        }
        
    finally:
        # Clean up the temporary file
        os.remove(filepath)


# --- 5. API Endpoints ---

@app.post("/run", response_model=FunctionResponse)
async def execute_function(request: FunctionRequest):
    """
    The main endpoint to accept and run user code.
    - Requirement 1: Handles concurrent executions (FastAPI handles this)
    - Requirement 5: Access Anywhere (HTTP endpoint)
    """
    log.info(f"Received execution request. Code snippet: {request.code[:50]}...")
    
    # Requirement 2: Log start timestamp
    start_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    
    # Run the blocking subprocess in a separate thread pool
    # This prevents the server from freezing during long-running tasks
    # and allows FastAPI to handle multiple requests concurrently.
    try:
        exec_result = await asyncio.to_thread(run_code_in_sandbox, request.code)
    except Exception as e:
        # Catch unexpected errors in the runner itself
        log.error(f"An internal server error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

    # Requirement 2: Log end timestamp and duration
    end_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    duration_ms = exec_result["duration_ms"]
    
    # Requirement 3: Calculate cost
    # For timeouts, we charge for the full 10 minutes.
    if exec_result["status"] == "timeout":
        cost = calculate_cost(TIME_LIMIT_SECONDS * 1000)
    else:
        cost = calculate_cost(duration_ms)
    
    # Requirement 5: Create log file
    log.info(
        f"Execution {exec_result['status']}. "
        f"Start: {start_timestamp} UTC, End: {end_timestamp} UTC, "
        f"Duration: {duration_ms:.2f}ms, Cost: ${cost:.10f}"
    )
    if exec_result["status"] == "error":
        log.error(f"Function failed with stderr: {exec_result['stderr']}")

    # Requirement 5: Ensure response includes time, result, and cost
    return FunctionResponse(
        status=exec_result["status"],
        result=exec_result["stdout"],
        stderr=exec_result["stderr"],
        execution_time_ms=duration_ms,
        cost=cost
    )

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """A bonus endpoint to check the total cost aggregated."""
    log.info("Fetching global stats.")
    with cost_lock:
        current_total_cost = total_aggregate_cost
    return StatsResponse(total_aggregate_cost=current_total_cost)

# --- 6. Run the Server ---

if __name__ == "__main__":
    log.info("Starting FaaS Simulator on http://0.0.0.0:8000")
    # By binding to 0.0.0.0, this server is accessible from
    # anywhere on your network, satisfying "Access Anywhere".
    uvicorn.run(app, host="0.0.0.0", port=8000)