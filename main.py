import socket
import threading
import pyaudio
import time
from cryptography.fernet import Fernet
import argparse
import struct

class VoiceChat:
    def __init__(self, local_port, remote_host, remote_port, key):
        # Настройки аудио
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.CHUNK = 1024
        
        # Сетевые настройки
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', local_port))
        
        # Шифрование
        self.cipher = Fernet(key)
        
        # Статистика
        self.sent_packets = 0
        self.received_packets = 0
        self.lost_packets = 0
        self.last_sequence = 0
        
        # Флаги управления
        self.running = False
        self.audio = pyaudio.PyAudio()
        
    def start(self):
        self.running = True
        # Поток для отправки аудио
        send_thread = threading.Thread(target=self.send_audio)
        send_thread.daemon = True
        send_thread.start()
        
        # Поток для приема аудио
        receive_thread = threading.Thread(target=self.receive_audio)
        receive_thread.daemon = True
        receive_thread.start()
        
        # Поток для статистики
        stats_thread = threading.Thread(target=self.show_stats)
        stats_thread.daemon = True
        stats_thread.start()
        
        send_thread.join()
        receive_thread.join()
        stats_thread.join()

    def send_audio(self):
        stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        sequence = 0
        while self.running:
            try:
                data = stream.read(self.CHUNK)
                # Добавляем порядковый номер
                packet = struct.pack('!I', sequence) + data
                # Шифруем данные
                encrypted = self.cipher.encrypt(packet)
                self.sock.sendto(encrypted, (self.remote_host, self.remote_port))
                self.sent_packets += 1
                sequence += 1
            except Exception as e:
                print(f"Send error: {e}")
        
        stream.stop_stream()
        stream.close()

    def receive_audio(self):
        stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True,
            frames_per_buffer=self.CHUNK
        )
        
        while self.running:
            try:
                data, _ = self.sock.recvfrom(4096)
                # Расшифровываем данные
                decrypted = self.cipher.decrypt(data)
                # Извлекаем порядковый номер
                sequence = struct.unpack('!I', decrypted[:4])[0]
                audio_data = decrypted[4:]
                
                # Проверяем потерю пакетов
                if sequence > self.last_sequence + 1:
                    self.lost_packets += sequence - self.last_sequence - 1
                self.last_sequence = sequence
                
                stream.write(audio_data)
                self.received_packets += 1
            except Exception as e:
                print(f"Receive error: {e}")
        
        stream.stop_stream()
        stream.close()

    def show_stats(self):
        while self.running:
            time.sleep(5)
            print("\n--- Статистика ---")
            print(f"Отправлено пакетов: {self.sent_packets}")
            print(f"Получено пакетов: {self.received_packets}")
            print(f"Потеряно пакетов: {self.lost_packets}")
            print(f"Текущая потеря: {self.lost_packets / max(1, self.received_packets) * 100:.2f}%")
            print("-----------------\n")

    def stop(self):
        self.running = False
        self.sock.close()
        self.audio.terminate()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Secure UDP Voice Chat')
    parser.add_argument('--local_port', type=int, required=True, help='Local UDP port')
    parser.add_argument('--remote_host', required=True, help='Remote host IP')
    parser.add_argument('--remote_port', type=int, required=True, help='Remote UDP port')
    parser.add_argument('--key', help='Encryption key (base64)')
    
    args = parser.parse_args()
    
    # Генерация ключа если не предоставлен
    key = args.key or Fernet.generate_key().decode()
    
    if not args.key:
        print(f"Сгенерированный ключ: {key}")
        print("Передайте этот ключ собеседнику!")
    
    chat = VoiceChat(
        local_port=args.local_port,
        remote_host=args.remote_host,
        remote_port=args.remote_port,
        key=key.encode()
    )
    
    try:
        print("Запуск голосового чата... (Ctrl+C для остановки)")
        chat.start()
    except KeyboardInterrupt:
        chat.stop()
        print("\nЧат остановлен")