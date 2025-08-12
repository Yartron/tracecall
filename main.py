import socket
import threading
import time
import struct
import os
import queue
import numpy as np
import sounddevice as sd
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

# Конфигурация
SAMPLE_RATE = 44100
BLOCK_SIZE = 1024
FORMAT = np.int16
CHANNELS = 1
AUDIO_TIMEOUT = 0.1
STATS_INTERVAL = 5
ENCRYPT_HEADER_SIZE = 16

class VoiceChat:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.remote_addr = None
        self.running = False
        self.audio_queue = queue.Queue(maxsize=20)
        self.stats = {
            'sent': 0, 'received': 0, 'lost': 0, 
            'last_seq': 0, 'start_time': time.time()
        }
        self.key = None
        self.lock = threading.Lock()
        
    def start(self, key, listen_port, remote_ip=None, remote_port=None):
        self.key = key
        self.sock.bind(('0.0.0.0', listen_port))
        
        if remote_ip and remote_port:
            self.remote_addr = (remote_ip, remote_port)
        
        self.running = True
        threading.Thread(target=self._receive_thread, daemon=True).start()
        threading.Thread(target=self._stats_thread, daemon=True).start()
        
        with sd.InputStream(
            callback=self._mic_callback,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            dtype=FORMAT,
            channels=CHANNELS
        ):
            with sd.OutputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                dtype=FORMAT,
                channels=CHANNELS,
                callback=self._speaker_callback
            ):
                print("Голосовой чат запущен! Нажмите Ctrl+C для выхода.")
                while self.running:
                    time.sleep(1)
    
    def _encrypt(self, data):
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return iv + cipher.encrypt(pad(data, AES.block_size))
    
    def _decrypt(self, data):
        iv = data[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(data[16:]), AES.block_size)
    
    def _mic_callback(self, indata, frames, time_info, status):
        if not self.remote_addr:
            return
            
        timestamp = time.time()
        seq = self.stats['sent']
        header = struct.pack('!Id', seq, timestamp)
        encrypted = self._encrypt(header + indata.tobytes())
        self.sock.sendto(encrypted, self.remote_addr)
        
        with self.lock:
            self.stats['sent'] += 1
    
    def _speaker_callback(self, outdata, frames, time_info, status):
        try:
            data = self.audio_queue.get(timeout=AUDIO_TIMEOUT)
            outdata[:] = np.frombuffer(data, dtype=FORMAT).reshape(-1, 1)
        except queue.Empty:
            outdata.fill(0)
    
    def _receive_thread(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                if not self.remote_addr:
                    self.remote_addr = addr
                
                decrypted = self._decrypt(data)[0]
                header = decrypted[:12]
                audio_data = decrypted[12:]
                
                seq, timestamp = struct.unpack('!Id', header)
                current_seq = self.stats['received']
                
                with self.lock:
                    self.stats['received'] += 1
                    if current_seq > 0 and seq > self.stats['last_seq'] + 1:
                        self.stats['lost'] += seq - self.stats['last_seq'] - 1
                    self.stats['last_seq'] = seq
                    self.stats['delay'] = time.time() - timestamp
                
                self.audio_queue.put(audio_data)
            except Exception as e:
                print(f"Ошибка приема: {str(e)}")
    
    def _stats_thread(self):
        while self.running:
            time.sleep(STATS_INTERVAL)
            with self.lock:
                uptime = time.time() - self.stats['start_time']
                loss_rate = (self.stats['lost'] / max(1, self.stats['received'])) * 100
                print(
                    f"Пакеты: отправлено={self.stats['sent']}, "
                    f"получено={self.stats['received']}, "
                    f"потеряно={self.stats['lost']} ({loss_rate:.1f}%), "
                    f"задержка={self.stats.get('delay', 0):.3f}сек, "
                    f"время={uptime:.0f}сек"
                )

def main():
    print("==== Безопасный голосовой чат ====")
    print("1. Создать сервер")
    print("2. Подключиться к серверу")
    choice = input("Выберите действие: ")
    
    key = get_random_bytes(16)
    listen_port = int(input("Ваш порт для приема: "))
    
    if choice == '1':
        print(f"Ваш ключ: {key.hex()}")
        chat = VoiceChat()
        chat.start(key, listen_port)
    elif choice == '2':
        remote_ip = input("IP адрес сервера: ")
        remote_port = int(input("Порт сервера: "))
        server_key = bytes.fromhex(input("Ключ сервера: "))
        chat = VoiceChat()
        chat.start(server_key, listen_port, remote_ip, remote_port)
    else:
        print("Неверный выбор")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nПрограмма завершена")
    except Exception as e:
        print(f"Ошибка: {str(e)}")