import os
from PIL import Image, ImageTk  # Para manejar imágenes más complejas
path_script = os.path.dirname(os.path.abspath(__file__))

def ICON():
    return os.path.join(path_script, 'Ico_VeriPre.png')

def ICON_ico():
    return os.path.join(path_script, 'Ico_VeriPre.ico')

def Logo_info():
    return os.path.join(path_script, 'Logo_cuadrado_W.png')

def PNG_Productos():
    return os.path.join(path_script, 'productos.png')

def PNG_Publicidad():
    return os.path.join(path_script, 'publicidad.png')

def PNG_Settings():
    return os.path.join(path_script, 'settings.png')

def PNG_Back():
    return os.path.join(path_script, 'back.png')

def PNG_Save():
    return os.path.join(path_script, 'guardar.png')

def PNG_Delete():
    return os.path.join(path_script, 'eliminar.png')

def PNG_Edit():
    return os.path.join(path_script, 'editar.png')

def PNG_Add():
    return os.path.join(path_script, 'agregar.png')

def PNG_Info():
    return os.path.join(path_script, 'info.png')

def PNG_No_Foto():
    return os.path.join(path_script, 'producto_.png')

def PNG_Check():
    return os.path.join(path_script, 'check.png')
def PNG_LOGO_PRINCIPAL():
    return os.path.join(path_script, '!!!LOGO_PRINCIPAL!!!.png')

def PNG_LOGO_DISPOSITIVO():
    return os.path.join(path_script, '!!!LOGO_DISPOSITIVO!!!.png')

def PNG_LOGO_SECUNDARIO():
    return os.path.join(path_script, 'INFORHARD_HORIZONTAL.png')

def READ_IMG(path, widht, height):
    image_logo = Image.open(path)
    image_logo = image_logo.resize((widht, height), Image.Resampling.LANCZOS)  # Redimensionar
    #image_logo.show()
    photo_logo = ImageTk.PhotoImage(image_logo)  # Guardar como atributo
    return photo_logo
