import subprocess
import os
import sys
import time
import webbrowser
import threading

# Add parent directory to import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gui_backend import app

def open_browser():
    """Open the browser after a short delay to allow the server to start"""
    time.sleep(1.5)
    webbrowser.open('http://localhost:3000')

def start_api_server():
    """Start the FastAPI server using uvicorn"""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

def start_react_dev_server():
    """Start the React development server"""
    subprocess.Popen(
        ["npm", "start"], 
        cwd=os.path.abspath(os.path.dirname(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

def run_app():
    """
    Run the Notion Explorer GUI application.
    
    This starts both the FastAPI backend server and the React frontend,
    then opens a browser window to the React app.
    """
    print("Starting Notion Explorer GUI...")
    
    # Check if npm is installed
    try:
        subprocess.run(["npm", "--version"], 
                      check=True, 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: npm is not installed or not in PATH. Please install Node.js and npm.")
        return
    
    # Start the API server in a separate thread
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    
    # Start the React development server
    start_react_dev_server()
    
    # Open the browser
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.start()
    
    print("GUI started! Browser window should open automatically.")
    print("Backend API: http://localhost:8000")
    print("Frontend: http://localhost:3000")
    print("Press Ctrl+C to stop the servers.")
    
    # Keep the main thread running to allow the API server to continue
    try:
        while api_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Notion Explorer GUI...")

if __name__ == "__main__":
    run_app()
