import socket
import sys
import threading
import sounddevice as sd
import numpy as np

SERVER_IP = 'actually-vocal.gl.at.ply.gg'  # Замените на IP сервера
SERVER_PORT = 3944
BUFFER_SIZE = 4096
SAMPLE_RATE = 44100
CHANNELS = 1
DTYPE = 'int16'
CHUNK_SIZE = 1024

class VoiceClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('127.0.0.1', 0))
        self.local_ip, self.local_port = self.sock.getsockname()
        print(f"Клиент запущен на {self.local_ip}:{self.local_port}")
        
        self.audio_queue = []
        self.running = True
        self.lock = threading.Lock()

    def send_audio(self):
        def callback(indata, frames, time, status):
            self.sock.sendto(indata.tobytes(), (SERVER_IP, SERVER_PORT))
        
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=CHUNK_SIZE,
            callback=callback
        ):
            print("Запись начата...")
            while self.running:
                sd.sleep(1000)

    def receive_audio(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(BUFFER_SIZE)
                audio = np.frombuffer(data, dtype=np.int16)
                with self.lock:
                    self.audio_queue.append(audio)
            except socket.error:
                pass

    def play_audio(self):
        def callback(outdata, frames, time, status):
            with self.lock:
                if self.audio_queue:
                    chunk = self.audio_queue.pop(0)
                    outdata[:] = chunk.reshape(outdata.shape)
                else:
                    outdata.fill(0)
        
        with sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=CHUNK_SIZE,
            callback=callback
        ):
            print("Воспроизведение начато...")
            while self.running:
                sd.sleep(1000)

    def start(self):
        send_thread = threading.Thread(target=self.send_audio, daemon=True)
        recv_thread = threading.Thread(target=self.receive_audio, daemon=True)
        play_thread = threading.Thread(target=self.play_audio, daemon=True)
        
        send_thread.start()
        recv_thread.start()
        play_thread.start()
        
        try:
            while True:
                input("Нажмите Enter для выхода...\n")
                break
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            self.sock.close()
            print("Клиент остановлен")

if __name__ == "__main__":
    client = VoiceClient()
    client.start()