import tkinter as tk
from tkinter import filedialog, messagebox
import requests
import os

def seleccionar_logo():
    global logo_path
    logo_path = filedialog.askopenfilename(filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.webp")])
    if logo_path:
        lbl_logo.config(text=f"Seleccionado: {os.path.basename(logo_path)}")

def enviar_logo():
    global logo_path
    if not logo_path:
        messagebox.showerror("Error", "Selecciona un archivo primero")
        return

    url = "http://192.168.1.161:8080/api/veri/LOGO_PRINCIPAL"

    try:
        with open(logo_path, "rb") as file:
            files = {"file": file}
            response = requests.post(url, files=files, timeout=10)

        if response.status_code == 200:
            messagebox.showinfo("Éxito", "Logo subido correctamente")
        else:
            messagebox.showerror("Error", f"Error al subir logo: {response.status_code}")
            print(response.json())  # Imprimir la respuesta exacta del servidor

    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Error de conexión: {e}")
        print(str(e))


# Interfaz con tkinter
root = tk.Tk()
root.title("Subir Logo Principal")
root.geometry("400x200")

lbl_logo = tk.Label(root, text="No se ha seleccionado ningún archivo", wraplength=350)
lbl_logo.pack(pady=10)

btn_seleccionar = tk.Button(root, text="Seleccionar Logo", command=seleccionar_logo)
btn_seleccionar.pack(pady=5)

btn_enviar = tk.Button(root, text="Enviar Logo", command=enviar_logo)
btn_enviar.pack(pady=10)

root.mainloop()
