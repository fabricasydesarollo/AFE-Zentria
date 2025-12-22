"""
Servicio de procesamiento de facturas.

Este módulo se encarga de procesar facturas extraídas del XML DIAN,
guardando tanto la cabecera como los items en sus respectivas tablas.

Autor: Sistema AFE
Fecha: 2025-10-10
"""
import hashlib
import re
import unicodedata

from sqlalchemy import text

from src.models.factura import Factura
from src.models.proveedor import Proveedor
from src.models.cliente import Cliente
from src.repository.factura_repository import FacturaRepository
from src.repository.factura_item_repository import FacturaItemRepository
from src.repository.proveedor_repository import ProveedorRepository
from src.utils.logger import get_logger

class FacturaService:
    def __init__(self, session):
        self.factura_repo = FacturaRepository(session)
        self.proveedor_repo = ProveedorRepository(session)
        self.logger = get_logger("FacturaService")

    def procesar_factura(self, factura_data, cuenta_correo_id=None):
        """
        Procesa una factura completa: guarda cabecera + items.

        Args:
            factura_data: Diccionario con datos extraídos del XML
            cuenta_correo_id: ID de la cuenta de correo de donde llegó (REQUERIDO para multi-tenant)

        Estructura esperada:
            - Campos de cabecera: numero_factura, cufe, fechas, montos, etc.
            - items_resumen: Lista de items/líneas de la factura

        Raises:
            Exception: Si hay error al procesar
        """
        try:
            factura = Factura(**factura_data)

            # Validar que tengamos NIT del proveedor (obligatorio para procesamiento)
            if not factura.nit_proveedor:
                raise ValueError(
                    f"Factura {factura.numero_factura} no tiene NIT de proveedor. "
                    "No se puede procesar sin esta información."
                )

            proveedor = Proveedor(
                nit=factura.nit_proveedor,
                razon_social=factura.razon_social_proveedor
            )

            # 🔒 SEGURIDAD 2025-12-15: Ya NO crea proveedores automáticamente
            # Buscar proveedor (retorna None si no existe)
            proveedor_id = self._get_or_create_proveedor(proveedor)

            # 🔒 VALIDACIÓN: Si no existe proveedor → CUARENTENA TOTAL
            if not proveedor_id:
                self.logger.warning(
                    f"⚠️ [CUARENTENA TOTAL] Factura {factura.numero_factura} "
                    f"con NIT no registrado: {factura.nit_proveedor}. "
                    f"Estado: en_cuarentena. Debe registrar el proveedor en /proveedores"
                )
                grupo_id = None
                estado_factura = "en_cuarentena"
            else:
                # ✨ Proveedor existe → Asignar grupo_id automáticamente desde cuenta correo
                grupo_id, estado_factura = self._asignar_grupo_id_automatico(
                    factura.nit_proveedor,
                    cuenta_correo_id
                )

            # ✨ NUEVA ESTRUCTURA CON RETENCIONES + MULTI-TENANT (14 campos esenciales)
            factura_dict = {
                # IDENTIFICACIÓN
                "numero_factura": factura.numero_factura,
                "cufe": factura.cufe,

                # RELACIONES
                "proveedor_id": proveedor_id,  # Puede ser None (cuarentena)

                # FECHAS
                "fecha_emision": factura.fecha_emision,
                # Convertir string vacío a None para MySQL DATE
                "fecha_vencimiento": factura.fecha_vencimiento if factura.fecha_vencimiento else None,

                # MONTOS
                "subtotal": factura.subtotal,
                "iva": factura.iva,
                "retenciones": factura.retenciones,  # Extraído del modelo Factura
                "total_a_pagar": factura.total_a_pagar,

                # MULTI-TENANT (2025-12-14)
                "grupo_id": grupo_id,  # NULL si proveedor no existe

                # WORKFLOW
                # Estado determinado por:
                # - Sin proveedor → "en_cuarentena" (requiere registro manual)
                # - Con proveedor + grupo → "en_revision" (flujo normal)
                # - Con proveedor sin grupo → "en_cuarentena" (requiere configuración)
                "estado": estado_factura,

                # AUTOMATIZACIÓN (opcionales)
                "confianza_automatica": factura_data.get('confianza_automatica'),
                "motivo_decision": factura_data.get('motivo_decision'),
            }

            # Insertar factura y obtener su ID
            factura_id = self.factura_repo.insert_factura(factura_dict)

            # ✨ NUEVO: Guardar items en tabla dedicada
            items = factura_data.get('items_resumen', [])
            if items and len(items) > 0:
                self._guardar_items_factura(factura_id, items)

            # Manejar caso donde items puede ser None
            num_items = len(items) if items else 0
            self.logger.info(
                f"Factura procesada: {factura.numero_factura} "
                f"(ID: {factura_id}, Items: {num_items})"
            )

        except Exception as e:
            numero = factura_data.get('numero_factura', 'N/A')
            self.logger.error(
                f"Error procesando factura {numero}: {e}",
                exc_info=True
            )
            raise

    def _asignar_grupo_id_automatico(self, nit_proveedor: str, cuenta_correo_id: int = None) -> tuple:
        """
        Asigna grupo_id basándose en cuenta de correo origen (PROFESIONAL 2025-12-19).

        ARQUITECTURA LIMPIA:
        - Si cuenta_correo_id proporcionado → Usar grupo de esa cuenta (FUENTE DE VERDAD)
        - Si no → Buscar NIT en nit_configuracion de esa cuenta
        - Si NO existe → NULL + estado "en_cuarentena"

        Args:
            nit_proveedor: NIT del emisor de la factura
            cuenta_correo_id: ID de la cuenta de correo de donde llegó la factura

        Returns:
            tuple: (grupo_id, estado_factura)
                - grupo_id: int | None
                - estado_factura: "en_revision" | "en_cuarentena"

        Ejemplos:
            ("800123456", 5) → (2, "en_revision")  # Cuenta 5 pertenece a grupo 2
            ("999888777", None) → (None, "en_cuarentena")  # Sin cuenta
        """
        try:
            # CASO 1: SI SE PROVEE CUENTA DE CORREO → Usar el grupo de esa cuenta
            if cuenta_correo_id:
                sql = text("""
                    SELECT cc.grupo_id
                    FROM cuentas_correo cc
                    WHERE cc.id = :cuenta_id
                    AND cc.activa = true
                """)

                result = self.proveedor_repo.session.execute(sql, {"cuenta_id": cuenta_correo_id})
                grupo_id = result.scalar()

                if grupo_id:
                    # Verificar que el NIT esté configurado en esa cuenta
                    sql_nit = text("""
                        SELECT 1
                        FROM nit_configuracion nc
                        WHERE nc.cuenta_correo_id = :cuenta_id
                        AND nc.nit = :nit
                        AND nc.activo = true
                    """)

                    nit_existe = self.proveedor_repo.session.execute(
                        sql_nit,
                        {"cuenta_id": cuenta_correo_id, "nit": nit_proveedor}
                    ).scalar()

                    if nit_existe:
                        self.logger.info(
                            f"✅ [MULTI-TENANT] Grupo asignado desde cuenta correo: "
                            f"cuenta_id={cuenta_correo_id}, grupo_id={grupo_id}, NIT={nit_proveedor}"
                        )
                        return (grupo_id, "en_revision")
                    else:
                        self.logger.warning(
                            f"⚠️ [CUARENTENA] NIT {nit_proveedor} NO configurado en cuenta {cuenta_correo_id}"
                        )
                        return (None, "en_cuarentena")

            # CASO 2: SIN CUENTA DE CORREO → Cuarentena (no podemos determinar grupo)
            self.logger.warning(
                f"⚠️ [CUARENTENA] Factura sin cuenta_correo_id. "
                f"No se puede determinar grupo. NIT={nit_proveedor}"
            )
            return (None, "en_cuarentena")

        except Exception as e:
            # CASO 3: ERROR CRÍTICO → Fallback seguro (cuarentena)
            self.logger.error(
                f"🚨 [ERROR] Error crítico asignando grupo_id para NIT {nit_proveedor}: {e}",
                exc_info=True
            )
            return (None, "en_cuarentena")

    def _buscar_por_nit_flexible(self, tabla: str, nit: str) -> int:
        """
        Busca un registro por NIT, probando tanto con como sin dígito verificador.
        Esto permite la transición gradual hacia NITs con dígito verificador.
        """
        # Primero buscar con el NIT tal como viene (debería tener DV)
        sql = f"SELECT id FROM {tabla} WHERE nit = :nit"
        result = self.proveedor_repo.session.execute(text(sql), {"nit": nit})
        record_id = result.scalar()
        
        if record_id:
            return record_id
        
        # Si no se encuentra y el NIT tiene DV, buscar sin DV (para compatibilidad)
        if '-' in nit:
            nit_sin_dv = nit.split('-')[0]
            result = self.proveedor_repo.session.execute(text(sql), {"nit": nit_sin_dv})
            record_id = result.scalar()
            
            if record_id:
                # Actualizar el registro para incluir el DV
                update_sql = f"UPDATE {tabla} SET nit = :nit_completo WHERE id = :id"
                self.proveedor_repo.session.execute(text(update_sql), {
                    "nit_completo": nit, 
                    "id": record_id
                })
                self.logger.info(f"Actualizado NIT en {tabla}: {nit_sin_dv} -> {nit}")
                return record_id
        
        return None

    def _get_or_create_proveedor(self, proveedor: Proveedor) -> int | None:
        """
        Busca proveedor por NIT.

        🔒 SEGURIDAD 2025-12-15:
        Ya NO crea proveedores automáticamente por razones de seguridad.
        Si el proveedor no existe, retorna None para enviar factura a cuarentena.

        Args:
            proveedor: Objeto Proveedor con nit y razon_social

        Returns:
            int | None: ID del proveedor si existe, None si no existe
        """
        # Buscar proveedor por NIT de manera flexible
        proveedor_id = self._buscar_por_nit_flexible("proveedores", proveedor.nit)

        if proveedor_id:
            return proveedor_id

        # 🔒 NO AUTO-CREAR: Retornar None si no existe
        self.logger.warning(
            f"⚠️ [CUARENTENA] Proveedor NO encontrado: NIT={proveedor.nit}. "
            f"La factura será enviada a cuarentena. "
            f"Debe registrar el proveedor manualmente en /proveedores"
        )
        return None

    def _guardar_items_factura(self, factura_id: int, items: list):
        """
        Guarda los items/líneas de una factura en tabla factura_items.

        Args:
            factura_id: ID de la factura padre
            items: Lista de diccionarios con datos de items del XML

        Estructura esperada por item:
            - descripcion: Descripción del producto/servicio
            - cantidad: Cantidad facturada
            - precio_unitario: Precio por unidad
            - subtotal: Subtotal del item
            - total_impuestos: IVA u otros impuestos
            - total: Total del item
            - codigo_producto: Código del proveedor (opcional)
            - unidad_medida: Unidad (opcional)
            - descuentos: Descuentos aplicados (opcional)
        """
        if not items:
            return

        item_repo = FacturaItemRepository(self.proveedor_repo.session)

        # SEGURIDAD CORPORATIVA: Verificar estado de la factura antes de modificar items
        estado_sql = text("SELECT estado FROM facturas WHERE id = :factura_id")
        result = self.proveedor_repo.session.execute(estado_sql, {"factura_id": factura_id})
        estado = result.scalar()

        # Verificar si ya existen items
        items_existentes = item_repo.get_items_by_factura(factura_id)

        if items_existentes:
            if estado and estado != 'pendiente':
                # PROTECCIÓN: No modificar facturas que ya fueron procesadas/aprobadas
                self.logger.warning(
                    f"Factura {factura_id} en estado '{estado}' ya tiene items. "
                    f"No se actualizarán los items para preservar la integridad de datos auditados."
                )
                return
            else:
                # Solo eliminar si está pendiente
                items_eliminados = item_repo.delete_items_by_factura(factura_id)
                self.logger.info(
                    f"Factura {factura_id} en estado 'pendiente': "
                    f"Actualizando {items_eliminados} items existentes"
                )

        for idx, item in enumerate(items, 1):
            descripcion = item.get('descripcion', '')

            # SCHEMA v2.0.0 (2025-12-02): Eliminadas codigo_estandar, descuento_porcentaje, notas
            item_dict = {
                # OBLIGATORIOS
                "factura_id": factura_id,
                "numero_linea": idx,
                "descripcion": descripcion,
                "cantidad": item.get('cantidad', 1),
                "precio_unitario": item.get('precio_unitario', 0),
                # NOTA: subtotal y total son columnas GENERATED en MySQL
                # Se calculan automáticamente, NO se deben incluir en INSERT
                "total_impuestos": item.get('total_impuestos', 0),

                # OPCIONALES (pero importantes para comparación)
                "codigo_producto": item.get('codigo_producto'),
                "unidad_medida": item.get('unidad_medida', 'unidad'),
                "descuento_valor": item.get('descuento_valor'),

                # NORMALIZACIÓN (para matching automático)
                "descripcion_normalizada": self._normalizar_texto(descripcion),
                "item_hash": self._calcular_hash(descripcion),

                # CLASIFICACIÓN (para análisis)
                "categoria": item.get('categoria'),
                "es_recurrente": 0,  # Se calcula después en backend
            }

            item_repo.insert_item(item_dict)

        self.logger.info(f"Guardados {len(items)} items para factura {factura_id}")

    def _normalizar_texto(self, texto: str) -> str:
        """
        Normaliza un texto para facilitar comparaciones.

        Transformaciones:
            - Lowercase
            - Sin acentos
            - Sin caracteres especiales (solo alfanuméricos y espacios)
            - Espacios múltiples → espacio simple
            - Sin espacios al inicio/fin

        Args:
            texto: Texto a normalizar

        Returns:
            str: Texto normalizado
        """
        if not texto:
            return ""

        # Lowercase
        texto = texto.lower()

        # Remover acentos
        texto = ''.join(
            c for c in unicodedata.normalize('NFD', texto)
            if unicodedata.category(c) != 'Mn'
        )

        # Solo alfanuméricos y espacios
        texto = re.sub(r'[^a-z0-9\s]', ' ', texto)

        # Espacios múltiples → uno solo
        texto = re.sub(r'\s+', ' ', texto)

        # Trim
        return texto.strip()

    def _calcular_hash(self, texto: str) -> str:
        """
        Calcula hash MD5 del texto normalizado.

        Útil para comparaciones rápidas de items.

        Args:
            texto: Texto a hashear

        Returns:
            str: Hash MD5 (32 caracteres hex)
        """
        if not texto:
            return ""

        texto_normalizado = self._normalizar_texto(texto)
        return hashlib.md5(texto_normalizado.encode('utf-8')).hexdigest()

    def _get_or_create_cliente(self, cliente: Cliente) -> int:
        # Buscar cliente por NIT de manera flexible
        cliente_id = self._buscar_por_nit_flexible("clientes", cliente.nit)
        if cliente_id:
            return cliente_id

        # Insertar cliente si no existe
        self.logger.info(
            f"Insertando cliente nuevo: {cliente.nit} - {cliente.razon_social}"
        )
        insert_sql = text(
            "INSERT INTO clientes (nit, razon_social) "
            "VALUES (:nit, :razon_social)"
        )
        self.proveedor_repo.session.execute(insert_sql, cliente.dict())

        # Buscar el ID del cliente recién insertado
        sql = "SELECT id FROM clientes WHERE nit = :nit"
        result = self.proveedor_repo.session.execute(text(sql), {"nit": cliente.nit})
        return result.scalar()
