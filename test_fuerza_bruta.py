"""
Prueba de fuerza bruta sobre una cédula conocida con títulos.
Detecta si el servicio devuelve vacío en algún intento.
"""
from scraper_senescyt.Scrapper.scraper_senescyt import ScraperSenescyt

CEDULA      = "0904358256"
URL         = "https://www.senescyt.gob.ec/web/guest/consultas"
ITERACIONES = 50

scraper = ScraperSenescyt()
scraper.get_page(URL)
scraper.cerrar_dialogo()

resultados = {"con_titulo": 0, "sin_titulo": 0, "error": 0}

for i in range(1, ITERACIONES + 1):
    try:
        resultado = scraper.consultar_cedula(CEDULA, max_intentos=1)
        tiene = bool(resultado.get("persona"))
        estado = "con_titulo" if tiene else "sin_titulo"
        resultados[estado] += 1
        if not tiene:
            scraper.guardar_estado(f"falso_negativo_{CEDULA}_{i}")
        print(f"[{i:>3}/{ITERACIONES}] {'✅ CON TÍTULO' if tiene else f'❌ SIN TÍTULO — guardado en /tmp/falso_negativo_{CEDULA}_{i}.html'}")
    except Exception as e:
        resultados["error"] += 1
        print(f"[{i:>3}/{ITERACIONES}] ⚠️  ERROR: {e}")

scraper.close()

print("\n── Resumen ──────────────────────────────")
print(f"  Con título     : {resultados['con_titulo']}")
print(f"  Sin título     : {resultados['sin_titulo']}  ← falsos negativos")
print(f"  Errores        : {resultados['error']}")
print(f"  Total intentos : {ITERACIONES}")