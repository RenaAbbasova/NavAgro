# Fuentes de datos — descarga manual

## Estrategia de almacenamiento

Los archivos crudos grandes (shapefiles del MCA, ~500-700 MB cada uno) **no se
guardan de forma permanente** en este repositorio ni en la nube — se
descargan, se procesan, y se borran localmente cuando ya no se necesitan.
Motivo: sin cuenta de facturación de Google Cloud activa, no hay Cloud
Storage disponible, y estos archivos son demasiado grandes para GitHub.

Patrón de trabajo:
1. Descargar el archivo crudo con el comando `curl` correspondiente (abajo).
2. Procesarlo con el script correspondiente (ej. `src/analysis/land_use_trend.py`).
3. Guardar solo el resultado procesado (pequeño, en CSV) en `outputs/`.
4. Subir ese resultado procesado a Google Drive (`NavAgro/datos_procesados/`)
   y/o a GitHub — ambos aceptan archivos de ese tamaño sin problema.
5. Borrar el archivo crudo local si hace falta espacio:
   `rm -rf data/mca_AAAA/`
6. Si se necesita de nuevo, re-descargar con el mismo comando — todos están
   documentados abajo, así que esto es siempre reproducible.

## Comarcas agrarias
```bash
curl -o data/comarcas_agrarias.zip https://idena.navarra.es/descargas/AGRICU_Pol_ComAgrarias.zip
unzip data/comarcas_agrarias.zip -d data/comarcas_agrarias
```
Tamaño: ~1.4 MB — este sí se conserva de forma permanente en el repo.

## Mapa de Cultivos y Aprovechamientos (MCA)

### 2019
```bash
curl -o data/mca_2019.zip https://idena.navarra.es/descargas/OCUPAC_Pol_MCA_VE2019.zip
unzip data/mca_2019.zip -d data/mca_2019
rm data/mca_2019.zip
```

### 2021
```bash
curl -o data/mca_2021.zip https://idena.navarra.es/descargas/OCUPAC_Pol_MCA_VE2021.zip
unzip data/mca_2021.zip -d data/mca_2021
rm data/mca_2021.zip
```

### 2023 (más reciente confirmado; no existe 2025 todavía)
```bash
curl -o data/mca_2023.zip https://idena.navarra.es/descargas/OCUPAC_Pol_MCA_VE2023.zip
unzip data/mca_2023.zip -d data/mca_2023
rm data/mca_2023.zip
```

Tamaño aproximado: 500-700 MB cada uno, sin comprimir. **No se sube a git**
(protegido por `.gitignore`), y se borra localmente tras procesar.

## Producciones anuales de los cultivos (Nastat)
Estadística oficial 2200133, disponible desde el año 2000, distingue
secano/regadío. Portal bloquea acceso automatizado — descarga manual desde:
- https://nastat.navarra.es/es/operacion-estadistica/-/tag/produccion-anual-cultivos
- https://datosabiertos.navarra.es/es/dataset/producciones-anuales-de-los-cultivos

Pendiente: confirmar formato de exportación exacto (tabla dinámica, sin
botón de descarga directa visible).