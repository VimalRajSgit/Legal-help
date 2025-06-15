
import os
import subprocess
import sys
import time


def run_server(folder_path, venv_name="venv", script_name="app.py", port="5000"):
    """Run a server from a folder with its virtual environment."""
    # Construct paths
    venv_activate = os.path.join(folder_path, venv_name, "Scripts" if os.name == "nt" else "bin", "activate")
    script_path = os.path.join(folder_path, script_name)

    # Check if paths exist
    if not os.path.exists(script_path):
        print(f"Error: {script_path} not found")
        return None
    if not os.path.exists(venv_activate):
        print(f"Warning: Virtual environment {venv_activate} not found, trying to run without it")
        cmd = f"python {script_path}"
    else:
        # Command to activate venv and run the script (Windows)
        cmd = f'"{venv_activate}" && python {script_path}'

    # Start the server as a subprocess
    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=folder_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Check if the process started successfully
        time.sleep(2)  # Give it a moment to start
        if process.poll() is not None:
            print(f"Error: Server in {folder_path} failed to start (exit code {process.poll()})")
            stderr_output = process.stderr.read()
            if stderr_output:
                print(f"Error details: {stderr_output}")
            return None
        print(f"Started server in {folder_path} on port {port}")
        return process
    except Exception as e:
        print(f"Failed to start server in {folder_path}: {e}")
        return None


def main():
    # Configuration: Update these paths and settings based on your project
    servers = [
        {"folder": "PythonProject4", "venv_name": "venv", "script_name": "app.py", "port": "5000"},
        {"folder": "PythonProject6", "venv_name": "venv", "script_name": "app.py", "port": "5001"},
        {"folder": "PythonProject7", "venv_name": "venv", "script_name": "app.py", "port": "5002"},
    ]

    processes = []

    # Start all servers
    for server in servers:
        folder_path = os.path.join(os.getcwd(), server["folder"])
        process = run_server(
            folder_path=folder_path,
            venv_name=server["venv_name"],
            script_name=server["script_name"],
            port=server["port"]
        )
        if process:
            processes.append(process)

    if not processes:
        print("No servers started. Exiting.")
        sys.exit(1)

    print("All servers running. Press Ctrl+C to stop.")

    # Keep the script running and monitor processes
    try:
        while True:
            for process in processes:
                if process.poll() is not None:  # Check if process has terminated
                    stderr_output = process.stderr.read()
                    print(f"Server process {process.pid} terminated with exit code {process.poll()}")
                    if stderr_output:
                        print(f"Error details: {stderr_output}")
                    sys.exit(1)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down all servers...")
        for process in processes:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("All servers stopped.")


if __name__ == "__main__":
    main()