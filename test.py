from zaly_toolkits.common.redis_db import get_redis
from scraper_senescyt.utils.redis_keys import RedisKey, CedulaEstado

r = get_redis()
estados = r.hgetall(RedisKey.HASH_ESTADO)
consultando = {c: e for c, e in estados.items() if e == CedulaEstado.CONSULTANDO}
print(f"Cédulas en proceso ahora: {len(consultando)}")
print(consultando)
