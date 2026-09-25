# NavAgro — Resumen Ejecutivo

Analítica de IA para Uso de Suelo y Rendimiento de Cultivos en Navarra
Septiembre 2026

🌾 **[Ver el dashboard interactivo en vivo →](https://renaabbasova.github.io/NavAgro/)**

---

## 1. Contexto

NavAgro combina imágenes satelitales (Sentinel-2), estadísticas oficiales de producción agrícola (Nastat) y cartografía de uso de suelo (IDENA/Gobierno de Navarra) para analizar tendencias agrícolas reales en las 7 comarcas de Navarra. El proyecto sigue una metodología de 2 líneas de trabajo paralelas.

## 2. Hallazgo Principal: El Caso de Nordoccidental

Entre 2021 y 2023, la comarca Nordoccidental muestra el cambio más dramático de todo el proyecto:

| Indicador | 2021 | 2023 |
|---|---|---|
| Parcelas cultivo secano | 1,740 | 386 (−77.8%) |
| Parcelas forestal no arbolado | 2,595 | 4,099 (+58.0%) |
| Producción cebada (t) | 2,116 | 1,854 (−12.4%) |
| Producción trigo blando (t) | 4,130 | 4,495 (+8.8%) |
| NDVI medio anual | 0.576 | 0.650 (+12.9%) |

**Interpretación (verificada con fuentes periodísticas, no solo inferida de los datos):** 2023 fue "la peor campaña cerealista en 20 años" en Navarra, causada por sequía severa en invierno-primavera (INTIA, Instituto Navarro de Tecnologías e Infraestructuras Agroalimentarias). La zona noroeste/Baja Montaña, donde se ubica Nordoccidental, registró rendimientos altos gracias a temperaturas más frescas que el resto de la región — explicando por qué el trigo blando sube en esta comarca específica mientras Navarra en general sufría pérdidas de cereal. La caída de parcelas de secano es consistente con abandono por sequía en las zonas más expuestas, no necesariamente una tendencia estructural permanente — se requieren más años de datos para distinguir entre un evento climático puntual y un cambio de uso de suelo duradero.

*Fuente: INTIA, vía orain.eus, agosto 2023*

## 3. Track A — Predicción de Rendimiento

Primer benchmark de modelos base, evaluado con división temporal honesta (entrena 2019+2021, evalúa 2023 — nunca un split aleatorio, para respetar la independencia temporal):

| Modelo | MAE (t) | RMSE (t) | R² |
|---|---|---|---|
| Media Histórica | 11,321 | 14,421 | **0.585** |
| Regresión Lineal (NDVI) | 20,311 | 24,419 | −0.189 |
| Regresión Lineal (NDVI+NDWI+NDBI) | 38,020 | 43,172 | −2.718 |

Con solo 28 filas de entrenamiento (7 comarcas × 2 cultivos × 2 años), ninguna combinación de features satelitales probada supera a la línea base más simple — y agregar más variables (NDVI+NDWI+NDBI) empeora el resultado significativamente, confirmando sobreajuste real con este tamaño de muestra. La Media Histórica ya explica el 58.5% de la varianza: un piso sólido sobre el cual construir con más años de datos.

## 4. Track B — Tendencia de Uso de Suelo

A diferencia de un enfoque de "cambio binario", este proyecto mide tendencia gradual comarca por comarca, comparando 3 años (2019, 2021, 2023). Hallazgos principales:

- **Nordoccidental y Pirineos:** mayor pérdida de cultivo herbáceo de secano (−77.8% y −38.8% respectivamente), con avance correspondiente de terreno forestal.
- **Ribera Alta-Aragón:** única comarca con crecimiento consistente en cultivos herbáceos de secano (+6.8%) y leñosos de regadío (+8.5%).
- **Patrón general:** los cultivos leñosos de regadío (frutales, viñedos) crecen en 5 de las 7 comarcas, consistente con las cifras oficiales de Nastat.

**Señal cuantificada de cambio (2019-2023):** usando una puntuación tipo z-score sobre la magnitud combinada de pérdida de secano y ganancia forestal, Nordoccidental es la única comarca que supera el umbral de anomalía (z=2.10), con más del doble de puntuación que la segunda comarca (Pirineos, z=0.48). Las 5 comarcas restantes muestran cambio dentro del rango esperado.

## 5. Rigor Metodológico Aplicado

Decisiones de ingeniería tomadas desde el diseño inicial, no corregidas después de encontrar errores:

- Manifiesto de datos con checksum SHA-256, fuente y fecha para cada archivo, desde el primer script de ingesta.
- Nunca se fabrican valores faltantes: comarcas/ventanas sin datos satelitales válidos se omiten explícitamente.
- `cloud_cover_pct` siempre calculado del metadato real de cada escena, nunca un valor fijo.
- Índices espectrales diseñados con protección de denominador desde el inicio.
- División temporal honesta para evaluación de modelos (leave-most-recent-year-out), no un split aleatorio.
- Discrepancias de nomenclatura entre fuentes oficiales ("Noroccidental" vs. "Nordoccidental") identificadas y documentadas explícitamente.

## 6. Próximos Pasos

- Investigar modelos no lineales (Random Forest) solo una vez que haya más años de datos disponibles.
- Extender la cobertura satelital a 2015, 2017 y 2025 (pendiente de renovación de cuota de cómputo mensual).
- Dashboard de visualización — **ya publicado** ([ver aquí](https://renaabbasova.github.io/NavAgro/)).

---

*Proyecto personal de investigación. Todas las fuentes de datos son públicas y oficiales (Nastat, IDENA/Gobierno de Navarra, ESA Copernicus). Contexto de sequía 2023 verificado vía INTIA (orain.eus, agosto 2023). Repositorio: [github.com/RenaAbbasova/NavAgro](https://github.com/RenaAbbasova/NavAgro)*
