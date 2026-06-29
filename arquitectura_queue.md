# Arquitectura Queue — Scraper SENESCYT (10M registros)

## 1. Estrategia de reanudación e idempotencia

Para 10M de cédulas el proceso va a correr días. Ante un crash, la reanudación debe ser automática y sin re-procesar lo ya hecho.

### Opción elegida: Cursor por ID + Redis

```sql
SELECT id_user, cedula
FROM tabla_transaccional
WHERE id_user > :last_id
ORDER BY id_user
LIMIT 10000
```

El cursor `last_id` se guarda en Redis como `refiller:cursor`. Es O(log n) usando el índice del PK — no se degrada con el tiempo ni con el tamaño de la tabla de resultados.

**Por qué no `NOT IN / NOT EXISTS`:** a 10M filas se convierte en un full scan de ambas tablas. El costo crece con el tiempo.

### Buffer de 50 registros por worker

Sin buffer, cada cédula genera una transacción individual a PostgreSQL:
- 10M × ~2ms = ~5.5 horas solo en overhead de transacciones

Con buffer de 50:
- 200K transacciones × ~2ms = ~7 minutos de overhead total

**Tradeoff:** ante un crash se pierden máximo 50 registros por worker. Al tener la cola en Redis, esas cédulas simplemente se re-procesan.

### Proyección de tiempos (10M cédulas, ~2s/cédula)

| Workers | Tiempo estimado |
|---------|----------------|
| 1       | ~231 días       |
| 5       | ~46 días        |
| 10      | ~23 días        |
| 20      | ~12 días        |
| 50      | ~5 días         |

El límite real es el rate limiting del servidor SENESCYT, no la capacidad local.

---

## 2. Redis vs PostgreSQL para cola y estado

### Rendimiento comparado

| Operación         | Redis   | PostgreSQL |
|-------------------|---------|------------|
| Latencia por op   | ~0.1ms  | ~3-5ms     |
| 40M ops de estado | ~1.1h   | ~33h       |
| A 2 ops/seg       | trivial | trivial    |

**La diferencia de rendimiento no es el motivo de elegir Redis.** Con 10 workers scrapeando a 2s/cédula, el ritmo de actualizaciones de estado es ~2/seg — ambos motores lo manejan sin esfuerzo.

### Por qué Redis para la cola

- **BLPOP** bloquea al worker hasta que hay trabajo, atómicamente, sin polling. PostgreSQL requiere `SELECT FOR UPDATE SKIP LOCKED` dentro de un loop con sleep.
- El estado de la cola es **efímero** — no necesita ACID, journaling ni backups.
- **Separación de responsabilidades**: Redis maneja estado operacional temporal, PostgreSQL guarda resultados permanentes queryables.

### Distribución de responsabilidades

| Qué               | Dónde      | Por qué                              |
|-------------------|------------|--------------------------------------|
| Cola de trabajo   | Redis LIST | BLPOP atómico, multi-worker nativo   |
| Estado por cédula | Redis HASH | O(1), efímero, no necesita ACID      |
| Cursor del refill | Redis STR  | Un solo valor, recovery simple        |
| Resultados finales| PostgreSQL | Persistente, queryable, ya montado   |

---

## 3. Arquitectura completa

### Estructuras Redis

```
queue:pendientes         LIST    → RPUSH para agregar, BLPOP para consumir
hash:estado              HASH    → {cedula: "pendiente|consultando|consultada|subida|error"}
buffer:resultados        LIST    → JSON por cédula, flush cada 50
refiller:cursor          STRING  → último id_user cargado
refiller:total_cargadas  STRING  → contador para monitoreo (opcional)
```

### Flujo completo

```
DB Transaccional
      │  cursor avanza por id_user
      ▼
┌─────────────┐     RPUSH                ┌──────────────┐
│   Refiller  │ ────────────────────────► │   Worker 1   │──┐
│  (1 proceso)│                           └──────────────┘  │ RPUSH resultado
└─────────────┘ ────────────────────────► │   Worker 2   │──┤
      ▲                     BLPOP         └──────────────┘  │
      │                  (bloquea si       │   Worker N   │──┤
      │                   vacío)           └──────────────┘  │
      │                                                       ▼
      │                                          ┌──────────────────┐
      │                                          │ buffer:resultados │
      │                                          └────────┬─────────┘
      │                                                   │ LLEN >= 50
      │                                                   ▼ (Lua atómico)
      │                                          ┌──────────────────┐
      └── borra "subidas", agrega nuevas ◄────── │   PostgreSQL     │
                                                  │  (resultados)    │
                                                  └──────────────────┘
```

### Estados por cédula

```
pendiente ──BLPOP──► consultando ──scrape OK──► consultada ──flush──► subida
               │                                                          │
               └──todos los intentos fallidos──► error ──reencola────────┘
                                                          (Refiller)
```

### Race condition en el buffer — solución con Lua

Dos workers pueden ver `LLEN >= 50` simultáneamente. El script Lua garantiza que solo uno hace el flush:

```lua
local count = redis.call('LLEN', 'buffer:resultados')
if count < 50 then return {} end
local items = redis.call('LRANGE', 'buffer:resultados', 0, 49)
redis.call('LTRIM', 'buffer:resultados', 50, -1)
return items
```

Si retorna vacío, otro worker ya hizo el flush. Si retorna 50 items, ese worker escribe a PostgreSQL.

### Crash recovery del worker

Cédulas que quedan en `consultando` por más de N minutos se recuperan en cada ciclo del Refiller:

```python
for cedula, estado in redis.hgetall('hash:estado').items():
    if estado == 'consultando' y lleva > 5 minutos:
        redis.hset('hash:estado', cedula, 'pendiente')
        redis.rpush('queue:pendientes', cedula)
```

---

## 4. Autonomía y estructura del proyecto

### Cómo se logra la autonomía

Los dos procesos nunca se llaman directamente. Solo hablan con Redis:

```
Refiller ──RPUSH──► Redis ◄──BLPOP── Worker
```

- **Si el Refiller se cae:** el Worker sigue procesando la cola. Cuando se vacía, `BLPOP` bloquea y espera. No crashea, solo pausa.
- **Si el Worker se cae:** el Refiller sigue llenando la cola. Los datos se acumulan hasta que el Worker vuelve.
- **Si ambos se caen:** Redis mantiene el estado. Al volver, cada uno retoma desde donde estaba.

### Mismo proyecto, entry points separados

Comparten configuración, modelos, cliente Redis y conexión a base — separarlos en proyectos distintos agrega complejidad sin beneficio.

```
ScraperSenescyt/
├── scraper_senescyt/
│   ├── Scrapper/              ← ya existe
│   ├── common/                ← ya existe
│   ├── config/                ← ya existe
│   └── queue/                 ← nuevo
│       ├── redis_client.py    → conexión compartida
│       ├── worker.py          → lógica del Worker
│       └── refiller.py        → lógica del Refiller
├── run_worker.py              ← python run_worker.py
└── run_refiller.py            ← python run_refiller.py
```

```bash
# Se corren de forma independiente
python run_worker.py    # puede haber N instancias
python run_refiller.py  # una sola instancia
```

### Ciclo de vida

```
Refiller (loop cada 30s)              Worker (loop infinito)
─────────────────────────             ──────────────────────────
si queue < 5000:                      cedula = BLPOP (bloquea si vacío)
  carga 10000 del DB                  marca "consultando"
  avanza cursor en Redis              scrape + reintentos con backoff
reencola cédulas en "error"           marca "consultada"
borra estados "subida"                RPUSH resultado al buffer
                                      si buffer >= 50 (Lua):
                                        flush a PostgreSQL
                                        marca "subida"
```

Redis es el único punto de sincronización. Ningún proceso sabe si el otro está corriendo.