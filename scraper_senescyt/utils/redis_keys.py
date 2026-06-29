# redis_keys.py — Constantes Redis del scraper Senescyt como Enums.
#
# Centraliza las claves de Redis y los estados posibles de una cédula.
# Al heredar de str cada valor funciona directamente como string en
# los comandos Redis sin necesidad de llamar .value.

from enum import Enum


class RedisKey(str, Enum):
    """Claves usadas en Redis para la cola y el seguimiento de estado."""
    QUEUE_PENDIENTES  = 'queue:pendientes'
    HASH_ESTADO       = 'hash:estado'
    BUFFER_RESULTADOS = 'buffer:resultado'
    REFILLER_CURSOR   = 'refiller:cursor'


class CedulaEstado(str, Enum):
    """Estados posibles de una cédula a lo largo del pipeline."""
    PENDIENTE   = 'pendiente'    # en cola, esperando ser procesada
    CONSULTANDO = 'consultando'  # tomada por un worker, en proceso
    CONSULTADA  = 'consultada'   # scraper terminó, en buffer RAM
    SUBIDA      = 'subida'       # persistida en PostgreSQL
    ERROR       = 'error'        # falló y debe reintentarse