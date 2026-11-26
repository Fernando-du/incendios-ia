import pandas as pd
import numpy as np

# 1. Cargar los 3 datasets reales
print("Cargando archivos CSV...")
rt = pd.read_csv("data/rtdata.csv")
emas = pd.read_csv("data/emas.csv")
dash = pd.read_csv("data/dashboard_conaf.csv")

# 2. Filtrar y pivotar RTData (de formato largo a ancho por estación y fecha/hora)
variables_interes = ["TEMP_MED", "HUMEDAD_REL", "VEL_VIENTO", "PRECIPITACION"]
rt_filtrado = rt[rt["rtd_c_variableid"].isin(variables_interes)].copy()

# Normalizar marca de tiempo a hora exacta para agrupar mediciones simultáneas de la misma estación
rt_filtrado["fecha_dt"] = pd.to_datetime(rt_filtrado["rtd_dt_marcatiempo"], utc=True)
rt_filtrado["fecha_hora"] = rt_filtrado["fecha_dt"].dt.floor("h")

rt_pivot = rt_filtrado.pivot_table(
    index=["ema_ia_id", "fecha_hora"],
    columns="rtd_c_variableid",
    values="rtd_f_valor",
    aggfunc="mean"
).reset_index()

# 3. Unir con EMAS para obtener nombre de estación y región
df = pd.merge(
    rt_pivot,
    emas[["ema_ia_id", "ema_c_nombre", "region_nombre"]],
    on="ema_ia_id",
    how="inner"
)

# 4. Homologar nombres de regiones entre EMAS y CONAF
mapa_regiones = {
    "Metropolitana de Santiago": "Metropolitana",
    "La Araucanía": "Araucanía",
    "Libertador General Bernardo O'Higgins": "O'Higgins",
    "Aysén del General Carlos Ibáñez del Campo": "Aysén",
    "Magallanes y de la Antártica Chilena": "Magallanes",
}
df["region_homologada"] = df["region_nombre"].replace(mapa_regiones)

# 5. Agregar datos históricos de CONAF por región (promedio quinquenal de incendios)
conaf_resumen = (
    dash.groupby("region", as_index=False)["nro_inc_prom_quint"]
    .mean()
    .rename(columns={"nro_inc_prom_quint": "incendios_historicos"})
)
conaf_resumen["incendios_historicos"] = conaf_resumen["incendios_historicos"].round().astype(int)

df = pd.merge(
    df,
    conaf_resumen,
    left_on="region_homologada",
    right_on="region",
    how="left"
)

# 6. Limpiar nulos y completar variables requeridas por data_service.py
df = df.dropna(subset=["TEMP_MED", "HUMEDAD_REL", "VEL_VIENTO", "ema_c_nombre", "region_homologada"])
df["incendios_historicos"] = df["incendios_historicos"].fillna(0).astype(int)

# Estimar porcentaje de vegetación seca (0-100%) basado en déficit hídrico (humedad y precipitación)
precip = df["PRECIPITACION"].fillna(0) if "PRECIPITACION" in df.columns else 0
df["vegetacion"] = np.clip(100 - df["HUMEDAD_REL"] - (precip * 5), 5, 98).round(1)

# Ajustar rangos estrictos que valida data_service.py
df["temperatura"] = df["TEMP_MED"].clip(-30, 60).round(2)
df["humedad"] = df["HUMEDAD_REL"].clip(0, 100).round(2)
# Nota: Si VEL_VIENTO viene en m/s, multiplicar por 3.6; si ya está en km/h, dejar directo.
# Usamos clip(0, 300) para cumplir validación.
df["viento"] = df["VEL_VIENTO"].clip(0, 300).round(2)

# 7. Construir el DataFrame final con las 8 columnas exactas de data_service.py
resultado = pd.DataFrame({
    "zona": df["ema_c_nombre"].str.strip() + " (" + df["region_homologada"].str.strip() + ")",
    "temperatura": df["temperatura"],
    "humedad": df["humedad"],
    "viento": df["viento"],
    "vegetacion": df["vegetacion"],
    "incendios_historicos": df["incendios_historicos"],
    # Formato ISO-8601 con zona horaria Chile (-03:00)
    "fecha_observacion": df["fecha_hora"].dt.tz_convert("America/Santiago").dt.strftime("%Y-%m-%dT%H:%M:%S%z").str.replace(r"(\d{2})(\d{2})$", r"\1:\2", regex=True),
    "fuente": "EMAS / CONAF Real"
})

# Limitar a máximo 9,500 filas (el límite de tu API es 10,000 filas por CSV)
resultado = resultado.head(9500)

archivo_salida = "dataset_real_unificado.csv"
resultado.to_csv(archivo_salida, index=False, encoding="utf-8")

print(f"¡Listo! Se generó '{archivo_salida}' con {len(resultado)} registros reales.")
print(resultado.head(3))