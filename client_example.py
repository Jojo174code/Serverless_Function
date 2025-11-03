import requests
import json
import time

# URL of your running FaaS server
URL = "http://127.0.0.1:8000/run"

# --- Example 1: Successful "Hello World" ---
print("--- Test 1: Successful Run ---")
success_code = """
import time
print("Hello from the FaaS simulator!")
time.sleep(1.2) # Sleep for 1.2 seconds
print("Function finished.")
"""

try:
    response = requests.post(URL, json={"code": success_code})
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error connecting to server: {e}")

print("\n" + "="*30 + "\n")

# --- Example 2: Code that fails (Error) ---
print("--- Test 2: Failing Run (Exception) ---")
error_code = """
x = 10
y = 0
print(x / y) # This will raise a ZeroDivisionError
"""

try:
    response = requests.post(URL, json={"code": error_code})
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error connecting to server: {e}")

print("\n" + "="*30 + "\n")

# --- Example 3: Timeout Test (shortened for demo) ---
# NOTE: The server is set to a 10-min (600s) timeout.
# This test will just run for 2s. To test the *actual* timeout,
# you would need to change `time.sleep(2)` to `time.sleep(601)`
# or temporarily change TIME_LIMIT_SECONDS in main.py to 1.
print("--- Test 3: Long-running job (will not time out) ---")
long_code = "import time; time.sleep(2); print('Slow job done.')"

try:
    response = requests.post(URL, json={"code": long_code})
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error connecting to server: {e}")