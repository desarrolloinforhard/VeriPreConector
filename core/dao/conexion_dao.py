class ConexionDAO:
    def __init__(self, db):
        self.db = db

    def obtener_todas(self):
        sql = """
        SELECT dsn, user, password, activo
        FROM VERIPRE_CONEXION
        """
        return self.db.ejecutar_consulta(sql) or []

    def obtener_primera(self):
        rows = self.obtener_todas()
        return rows[0] if rows else None

    def crear(self, dsn, usuario, password, activo):
        sql = """
        INSERT INTO VERIPRE_CONEXION (dsn, user, password, activo)
        VALUES (?, ?, ?, ?)
        """
        return self.db.ejecutar_consulta(sql, (dsn, usuario, password, int(bool(activo))))

    def actualizar_por_dsn(self, dsn_actual, dsn, usuario, password, activo):
        sql = """
        UPDATE VERIPRE_CONEXION
        SET dsn = ?, user = ?, password = ?, activo = ?
        WHERE dsn = ?
        """
        return self.db.ejecutar_consulta(
            sql,
            (dsn, usuario, password, int(bool(activo)), dsn_actual),
        )
