# src/utils/deduplication.py
from __future__ import annotations
import hashlib
import json
from decimal import Decimal
from typing import Dict, Any, Iterable, List


def _normalize_value(v):
    if v is None:
        return ""
    if isinstance(v, Decimal):
        return format(v.quantize(Decimal("0.001")), "f")
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return v.strip()
    try:
        return json.dumps(v, sort_keys=True, default=str, ensure_ascii=False)
    except Exception:
        return str(v)




def make_factura_key(factura: dict, keys=None) -> str:
    keys = keys or ["nit", "numero_factura", "fecha_emision", "total_a_pagar"]
    payload = {k: _normalize_value(factura.get(k)) for k in keys}
    s = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def deduplicate_facturas(facturas: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Devuelve una lista sin duplicados preservando la primera ocurrencia.
    Dedupe por make_factura_key.
    """
    seen_cufe = set()
    seen_numero = set()
    out: List[Dict[str, Any]] = []
    conflictos = []
    for f in facturas:
        cufe = f.get("cufe")
        numero = f.get("numero_factura")
        key = make_factura_key(f)
        # Prioridad: deduplicar por CUFE si existe
        if cufe:
            if cufe in seen_cufe:
                conflictos.append(f)
                continue
            seen_cufe.add(cufe)
        # Si no hay CUFE, deduplicar por numero_factura
        elif numero:
            if numero in seen_numero:
                conflictos.append(f)
                continue
            seen_numero.add(numero)
        else:
            # Si no hay CUFE ni numero, deduplicar por huella
            if key in seen_cufe:
                conflictos.append(f)
                continue
            seen_cufe.add(key)
        out.append(f)
    if conflictos:
        print(f"[deduplication] Facturas duplicadas detectadas: {len(conflictos)}. Solo se guarda la primera ocurrencia por CUFE o número.")
    return out


def load_index_from_file(path) -> Dict[str, str]:
    """
    Carga índice JSON {key: filename} si existe, sino {}.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}
    except Exception:
        # en caso de corrupcion devolvemos dict vacio (se puede mejorar con backup)
        return {}
