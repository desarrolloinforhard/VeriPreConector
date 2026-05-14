class DispositivosDAO:
    def __init__(self, db):
        self.db = db

    def listar(self):
        sql = """
        SELECT nombre, direccion_conexion, puerto, comentarios
        FROM VERIPRE_EQUIPOS
        ORDER BY nombre
        """
        return self.db.ejecutar_consulta(sql) or []

    def listar_dict(self):
        dispositivos = {}
        for nombre, direccion, puerto, comentario in self.listar():
            dispositivos[nombre] = {
                "direccion_ip": direccion,
                "puerto": puerto,
                "comentario": comentario,
            }
        return dispositivos

    def crear(self, nombre, direccion_ip, puerto, comentario):
        sql = """
        INSERT INTO VERIPRE_EQUIPOS (nombre, direccion_conexion, puerto, comentarios)
        VALUES (?, ?, ?, ?)
        """
        return self.db.ejecutar_consulta(sql, (nombre, direccion_ip, puerto, comentario))

    def actualizar_por_nombre(self, nombre_actual, nombre, direccion_ip, puerto, comentario):
        sql = """
        UPDATE VERIPRE_EQUIPOS
        SET nombre = ?, direccion_conexion = ?, puerto = ?, comentarios = ?
        WHERE nombre = ?
        """
        return self.db.ejecutar_consulta(
            sql,
            (nombre, direccion_ip, puerto, comentario, nombre_actual),
        )

    def eliminar_por_nombre(self, nombre):
        sql = "DELETE FROM VERIPRE_EQUIPOS WHERE nombre = ?"
        return self.db.ejecutar_consulta(sql, (nombre,))
