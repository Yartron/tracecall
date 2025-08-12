import io
import pyaudio
import soundfile as sf
import sys

import socket
import numpy as np

from threading import Thread
import gradio as gr

def RAW_2_OGG(raw_chunk):
  byte_io = io.BytesIO()
  signal = np.frombuffer(raw_chunk,dtype=np.float32)
  old=sys.getsizeof(raw_chunk)

  sf.write(byte_io, signal, RATE,format='OGG') 
  b=bytes(byte_io.getbuffer( ))
  n=sys.getsizeof(b)
  print(n/old)
  return b


def OGG_2_RAW(ogg_chunk):
  byte_io = io.BytesIO()
  byte_io.write(ogg_chunk)
  byte_io.seek(0)
  
  data, samplerate = sf.read(byte_io)
  
  return np.float32(data)


CHUNK=4096
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 16000
p = pyaudio.PyAudio()

stream=p.open(format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            output=True,
            frames_per_buffer=CHUNK)




black,clients=[],[]

def set_black(s):
    global black
    black=s

def get_black():
    global black
    return black

def set_clients(s):
    global clients
    clients=s

def get_clients():
    global clients
    return clients

def Sender():
    UDP_PORT = 6006

    sock = socket.socket(socket.AF_INET,
                        socket.SOCK_DGRAM)
    while True:
        clients=get_clients()
        data = stream.read(CHUNK, exception_on_overflow = False)
        data=RAW_2_OGG(data)
        print(len(data))
        for addr in clients:
            sock.sendto(data, (addr, UDP_PORT))



def Receiver():
    me = "127.0.0.1"
    UDP_PORT = 3944

    sock = socket.socket(socket.AF_INET,
                        socket.SOCK_DGRAM)
    sock.setblocking(0)
    sock.bind((me, UDP_PORT))


    while True:
        c=0
        first=True
        while True:
            blacklist=get_black()
            try:
                d,addr=sock.recvfrom(CHUNK*10)
                if addr[0] in blacklist:
                    continue
                new=OGG_2_RAW(d)
                #new=np.frombuffer(d,dtype=np.uint16) # buffer size is 1024 bytes
                c+=1
                if first:
                    data=new.copy()
                    first=False
                else:
                    data+=new
            except:
                break
        if not first:
            #print(c)
            stream.write(data.tobytes())




def variable_outputs(k):
    k = int(k)
    return [gr.Textbox.update(visible=True)]*k + [gr.Textbox.update(visible=False)]*(max_textboxes-k)


max_textboxes=10
with gr.Blocks() as demo:
    gr.Markdown("# PyCord")
    with gr.Tab("Отправлять"):
        snd = gr.Slider(0, max_textboxes, value=10, step=1, label="Адреса получателей")
        textboxes = []
        for i in range(max_textboxes):
            t = gr.Textbox(f"127.0.0.1")
            textboxes.append(t)
        snd.change(variable_outputs, snd, textboxes)
        button = gr.Button("Начать отправку")
        button.click(lambda *s:set_clients(s[:s[-1]]),textboxes+[snd])

    with gr.Tab("Чёрный список"):
        snd2 = gr.Slider(0, max_textboxes, value=10, step=1, label="Блокировать входящие с адресов")
        textboxes2 = []
        for i in range(max_textboxes):
            t = gr.Textbox(f"127.0.0.1")
            textboxes2.append(t)
        snd2.change(variable_outputs, snd2, textboxes2)
        button2 = gr.Button("БАН")
        button2.click(lambda *s:set_black(s[:s[-1]]),textboxes2+[snd2])
    


sender = Thread(target=Sender, args=())
sender.start()

recv = Thread(target=Receiver, args=())
recv.start()

demo.launch(share=True, server_port=3944)