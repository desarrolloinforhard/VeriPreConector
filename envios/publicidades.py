import tkinter as tk
from tkinter import filedialog, messagebox
import requests
import json
import os

def seleccionar_archivo():
    global file_path
    file_path = filedialog.askopenfilename(filetypes=[("Archivos multimedia", "*.png;*.jpg;*.jpeg;*.webp;*.gif;*.mp4;*.avi;*.mov;*.mkv;*.webm")])
    if file_path:
        lbl_archivo.config(text=f"Seleccionado: {os.path.basename(file_path)}")

def enviar_archivo():
    global file_path
    if not file_path:
        messagebox.showerror("Error", "Selecciona un archivo primero")
        return
    
    url_images = "http://192.168.1.150:8080/api/veri/ad_medias_images"
    url_videos = "http://192.168.1.150:8080/api/veri/ad_medias_videos"
    
    ext = file_path.split(".")[-1].lower()
    nombre_archivo = os.path.splitext(os.path.basename(file_path))[0]
    
    if ext in ["png", "jpg", "jpeg", "webp", "gif"]:
        url = url_images
    elif ext in ["mp4", "avi", "mov", "mkv", "webm"]:
        url = url_videos
    else:
        messagebox.showerror("Error", "Formato de archivo no soportado")
        return
    
    try:
        files = {"file": open(file_path, "rb")}
        data = {"json": json.dumps({
            "nro_posicion": int(entry_nro_posicion.get()),
            "nombre_media": nombre_archivo,
            "formato_media": ext
        })}
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            messagebox.showinfo("Éxito", "Archivo subido correctamente")
        else:
            messagebox.showerror("Error", f"Error al subir archivo: {response.text}")
    except Exception as e:
        messagebox.showerror("Error", f"Error al conectar con el servidor: {str(e)}")

# Interfaz con tkinter
root = tk.Tk()
root.title("Subir Archivos a API")
root.geometry("400x250")

lbl_archivo = tk.Label(root, text="No se ha seleccionado ningún archivo", wraplength=350)
lbl_archivo.pack(pady=5)

btn_seleccionar = tk.Button(root, text="Seleccionar Archivo", command=seleccionar_archivo)
btn_seleccionar.pack(pady=5)

lbl_nro_posicion = tk.Label(root, text="Número de Posición:")
lbl_nro_posicion.pack()
entry_nro_posicion = tk.Entry(root)
entry_nro_posicion.pack(pady=5)

btn_enviar = tk.Button(root, text="Enviar Archivo", command=enviar_archivo)
btn_enviar.pack(pady=10)

root.mainloop()