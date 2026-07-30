class ApiKeyDAO:
    def __init__(self, db):
        self.db = db

    def asegurar_tabla(self):
        sql = """
        CREATE TABLE IF NOT EXISTS api_key (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL
        )
        """
        return self.db.ejecutar_consulta(sql)

    def obtener_ultima(self):
        self.asegurar_tabla()
        rows = self.db.ejecutar_consulta(
            "SELECT api_key FROM api_key ORDER BY id DESC LIMIT 1"
        ) or []
        if rows and rows[0] and rows[0][0]:
            return str(rows[0][0]).strip()
        return None

    def reemplazar(self, api_key):
        self.asegurar_tabla()
        self.db.ejecutar_consulta("DELETE FROM api_key")
        return self.db.ejecutar_consulta(
            "INSERT INTO api_key (api_key) VALUES (?)",
            (api_key,),
        )
