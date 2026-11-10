# Verification report: <tabla destino>

- **Resultado:** PASA | NO PASA (<n> de <m> escenarios)
- **Fecha de la verificación:** <AAAA-MM-DD HH:MM>
- **Ejecutó:** <usuario>
- **Spec:** `<ruta>/spec.md` (estado <estado>)
- **Plan:** `<ruta>/plan.md`

## 1. Archivos verificados
El hash permite saber después si alguien o un despliegue cambió el archivo.

| Archivo | sha256 (12) | Líneas |
|---|---|---|
| `PARAMETROS/config_par_<proceso>.conf` | `<hash>` | <n> |

## 2. Linter
Comando: `conf_linter.py --carpeta <ruta> --spec <ruta>/spec.md [--explain]`

| Severidad | Regla | Archivo | Detalle |
|---|---|---|---|
| - | - | - | Sin hallazgos |

## 3. Ejecución
- **Notebook:** `DLKH_01_<NOMBRE>`
- **Parámetros:** `g_fecha = <AAAAMMDD>`, `id_pipeline = <id>`
- **Resultado del exit:** `<OK - tabla - segundos>`

## 4. Aceptación
- **Fecha de corte:** tabla `<AAAAMMDD>`, esperado `<AAAAMMDD>`. Si no coinciden, la comparación no se hace.
- **Filas:** tabla <n>, esperado <m>, solo en tabla <a>, solo en esperado <b>

| Escenario | Resultado | Evidencia |
|---|---|---|
| mismas fechas en los dos lados | PASA | |
| mismas llaves | PASA | |
| mismos totales | PASA | suma obtenida / suma esperada = 1.0000 |
| mismos valores por llave | PASA | 100 % dentro de tolerancia |

## 5. Lo que NO se verificó
- <todo lo que la aceptación no cubre: otras fechas, archivos de exportación, rendimiento>

## 6. Cambios desde la verificación anterior
| Archivo | Cambio | Escenario que lo cubre |
|---|---|---|
