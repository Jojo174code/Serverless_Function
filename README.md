# Serverless_Function

Python FaaS (Serverless) Simulator

    --A lightweight simulator for a Function-as-a-Service (FaaS) platform, inspired by AWS Lambda. This project provides an HTTP API to remotely execute Python code, track its performance, and calculate simulated costs.


Core Features

    --Remote Code Execution: Securely run user-submitted Python code via an HTTP POST request.

    --Asynchronous API: Built with FastAPI to handle many concurrent connections without blocking, using an async event loop.

    --Concurrent Execution: Uses asyncio.to_thread to run blocking subprocess calls in a separate thread pool, preventing the server from freezing.

    --Sandboxed Environment: Provides basic isolation by executing code in a separate process using subprocess.run(). This prevents user code from accessing server memory or variables.

    --Cost Simulation: Implements a Lambda-like pricing model, charging a base fee per invocation plus a fee for every 100ms of execution time.

    --Strict Timeouts: Enforces a 10-minute (600-second) execution limit. Functions exceeding this limit are terminated, logged, and billed for the full 10 minutes.

    --Persistent Logging: Creates a faas_simulator.log file to log all invocations, durations, costs, and stderr output from failed runs.

How it Works: Architecture

This simulator uses a simple but powerful architecture to handle concurrent requests safely.

    --A Client (e.g., client_example.py) sends an HTTP request to the POST /run endpoint with Python code in the JSON body.

    --The FastAPI Server (main.py) receives the request. Because the endpoint is async def, FastAPI can handle thousands of these connections at once.

    --The server cannot run the code directly, as subprocess.run() is a blocking operation that would freeze the entire server.

    --Instead, it uses await asyncio.to_thread(...) to delegate the blocking run_code_in_sandbox function to a separate worker thread.

    --The Worker Thread executes the user's code in a new, isolated subprocess. It captures all stdout, stderr, and the precise execution time.

    --The worker thread finishes and returns the results to the main FastAPI event loop.

    --FastAPI calculates the cost, logs the event, and returns the final JSON response to the client.

This async + threading + subprocess model allows the server to remain highly responsive while safely executing multiple long-running jobs in parallel.

Getting Started

1. Installation
--Ensure you have Python 3.8+ installed.

2. Run the Server
--In your first terminal, start the uvicorn server:

--You will see the server start up and listen on port 8000:

3. Run the Test Client
Open a second terminal and run the client_example.py script:

This client script will send three different payloads to your server and print their JSON responses:

    1) Test 1: Successful Run: A simple script that sleeps for 1.2 seconds.

    2) Test 2: Failing Run (Exception): A script that intentionally raises a ZeroDivisionError.

    3) Test 3: Long-running job: A script that sleeps for 2 seconds.

While this runs, you will see the detailed logs (including costs and errors) appear in your server terminal.

--Project Files--

API Endpoint Reference
POST /run

The main endpoint for submitting and executing code.

Request Body (application/json):

Response (200 OK) The server always returns 200 OK if the request is valid. The status field in the JSON response indicates the function's outcome.

    --On Success:

    --On User Code Error:

    --On Timeout (Exceeding 10 minutes):

GET /stats

Retrieves the total aggregate cost of all function runs since the server was last started. This endpoint is thread-safe.

Response (200 OK):


📄 License
This project is open-source and available under the .
