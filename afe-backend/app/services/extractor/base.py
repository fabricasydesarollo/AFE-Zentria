# app/services/extractor/base.py
from abc import ABC, abstractmethod
from typing import Iterable
from app.schemas.factura import FacturaCreate

class IInvoiceExtractor(ABC):
    @abstractmethod
    def extract(self, batch_size: int = 100) -> Iterable[FacturaCreate]:
        """
        Extrae facturas crudas en batches. Debe retornar objetos FacturaCreate (o dicts que se puedan transformar).
        """
        raise NotImplementedError
