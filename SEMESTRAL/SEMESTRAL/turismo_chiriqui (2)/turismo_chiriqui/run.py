import socket
from app import create_app

app = create_app()

def local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80)); return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"

if __name__ == "__main__":
    print("\nTurismo Chiriquí disponible en:")
    print("  Esta computadora: http://127.0.0.1:5000")
    print(f"  Red Wi-Fi/LAN:    http://{local_ip()}:5000")
    print("Los dispositivos deben estar conectados a la misma red.\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
