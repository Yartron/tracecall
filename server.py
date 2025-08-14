import socket
import sys

SERVER_IP = '147.185.221.30'
SERVER_PORT = 3944
BUFFER_SIZE = 4096

class UDPServer:
    def __init__(self):
        self.clients = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((SERVER_IP, SERVER_PORT))
        print(f"Сервер запущен на {SERVER_IP}:{SERVER_PORT}")

    def run(self):
        try:
            while True:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                
                if addr not in self.clients:
                    print(f"Новый клиент: {addr}")
                    self.clients.append(addr)
                    
                if len(self.clients) == 2:
                    for client in self.clients:
                        if client != addr:
                            self.sock.sendto(data, client)
        except KeyboardInterrupt:
            print("\nСервер остановлен")
            self.sock.close()
            sys.exit(0)

if __name__ == "__main__":
    server = UDPServer()
    server.run()