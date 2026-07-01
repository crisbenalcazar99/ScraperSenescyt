# redis_client.py — Constantes específicas del pipeline de scraping.
#
# get_redis()  →  zaly_toolkits/common/redis_db.py
# Claves y estados  →  scraper_senescyt/utils/redis_keys.py

# Tamaño del buffer antes de hacer flush a PostgreSQL
BUFFER_SIZE = 20

# Script Lua — flush atómico del buffer.
# Garantiza que solo un worker hace el flush aunque varios vean LLEN >= 50.
LUA_FLUSH_BUFFER = """
local count = redis.call('LLEN', KEYS[1])
if count < tonumber(ARGV[1]) then return {} end
local items = redis.call('LRANGE', KEYS[1], 0, tonumber(ARGV[1]) - 1)
redis.call('LTRIM', KEYS[1], tonumber(ARGV[1]), -1)
return items
"""