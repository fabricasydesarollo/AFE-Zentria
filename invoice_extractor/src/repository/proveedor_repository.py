from sqlalchemy import text

class ProveedorRepository:
    def __init__(self, session):
        self.session = session

    def proveedor_existe(self, nit):
        check_sql = text("SELECT nit FROM proveedores WHERE nit = :nit")
        result = self.session.execute(check_sql, {'nit': nit})
        return result.scalar() is not None

    def insert_proveedor(self, proveedor):
        insert_sql = text("""
            INSERT INTO proveedores (nit, razon_social)
            VALUES (:nit, :razon_social)
        """)
        self.session.execute(insert_sql, proveedor.dict())
