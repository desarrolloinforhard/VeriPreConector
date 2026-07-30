class VentanaManager:
    ventanas_abiertas = {}

    @classmethod
    def abrir_ventana(cls, nombre, constructor, *args, **kwargs):
        """Abre una ventana si no está ya abierta"""
        if nombre in cls.ventanas_abiertas and cls.ventanas_abiertas[nombre].winfo_exists():
            cls.ventanas_abiertas[nombre].focus_set()
        else:
            try:
                ventana = constructor(*args, **kwargs)  # Aquí se instancia la clase correctamente
            except PermissionError:
                return None
            cls.ventanas_abiertas[nombre] = ventana.top_level_configuracion  # Guarda la referencia de la ventana
            ventana.top_level_configuracion.protocol("WM_DELETE_WINDOW", lambda: cls.cerrar_ventana(nombre))
            return ventana


    @classmethod
    def cerrar_ventana(cls, nombre):
        """Cierra la ventana y la elimina de la lista"""
        if nombre in cls.ventanas_abiertas:
            ventana = cls.ventanas_abiertas[nombre]
            if ventana and ventana.winfo_exists():
                ventana.destroy()
            del cls.ventanas_abiertas[nombre]  # Eliminamos la referencia

