from app import app, get_available_port
import sys

if __name__ == "__main__":
    try:
        # Try to use port 5000 first
        port = get_available_port(5000)
        if port is None:
            print("Error: Port 5000 and subsequent ports are not available")
            sys.exit(1)
            
        if port != 5000:
            print(f"Warning: Port 5000 was not available, using port {port}")
            
        app.run(host="0.0.0.0", port=port, debug=True)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)
