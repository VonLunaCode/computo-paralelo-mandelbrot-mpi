# Mandelbrot distribuido con MPI (Maestro-Trabajador)

Proyecto final de Cómputo Paralelo: renderizador distribuido del conjunto de Mandelbrot en un cluster heterogéneo de laptops.

- `mandelbrot_mpi.c` — programa MPI en C (rank 0 = maestro, resto = trabajadores, bloques NxN, cola de tareas dinámica, salida PNG).
- `GUIA_LAPTOP_MAESTRO.md` / `GUIA_LAPTOP_TRABAJADORA.md` — pasos para pasar a cada integrante (instalar hoy, conectar mañana).
- `GUIA_CLUSTER_WSL2.md` — cómo armar el cluster de 3 laptops con WSL2 + red por cable.
- `cluster/` — scripts: `setup_nodo.sh` (prepara cada nodo), `correr_pruebas.sh` (corre las pruebas y recopila datos), `diagnostico.ps1` (solo lectura, Windows), `hosts.example`.
- `resultados_sv/` — resultados de referencia en una sola máquina (1000 iteraciones, bloque 32).

## Uso rápido
```bash
mpicc -O3 -std=c99 -o mandelbrot_mpi mandelbrot_mpi.c -lm
export HWLOC_COMPONENTS=-gl
mpiexec -n 4 ./mandelbrot_mpi 1920 1080 1000 32 salida.png   # W H iter bloque [png]
```
Con P=1 corre en modo secuencial (línea base del speedup).

> **Si usas otro agente (Antigravity, Cursor, Copilot, etc.):** dile *"Lee AGENTS.md y sigue sus instrucciones. Soy la maestra / la trabajadora."*

## Resultados del clúster y reporte (26-nov-2026)

Corridas reales en las 3 laptops (WSL2, Ethernet `192.168.50.0/24`), maestro en la `.11`, 40 slots, bloques de 32×32,
**una repetición por configuración**.

- `resultados_cluster/1000it/` y `resultados_cluster/5000it/` — `resumen.csv`, `resultados.csv`, `baseline_T1_por_nodo.csv`,
  `por_proceso.csv`, `info_cluster.txt` y la salida de `correr_pruebas.sh`. Los nombres de las máquinas se reemplazaron por N1 (maestro), N2 y N3.
- `reporte/` — reporte en LaTeX formato LNCS: `report.tex`, `gen.py` (lo genera desde los CSV), figuras y el PDF.

| | Speedup máx. vs. nodo maestro | Espera de trabajadores con P=40 |
|---|---|---|
| 1000 it (3 pruebas) | 10.8 (7680×4320, P=32) | 61–62 % |
| 5000 it (pruebas 1 y 2) | 14.8 (3840×2160, P=40) | 22–31 % |

Con `--map-by slot` y slots 16/16/8, los procesos con P ≤ 16 caen todos en el nodo maestro; el segundo nodo entra con P=32
y el tercero con P=40. Las explicaciones del estancamiento entre nodos son **hipótesis**, no se aislaron con experimentos
(ver limitaciones en el reporte). La prueba 3 (7680×4320) no se repitió con 5000 iteraciones.

Para compilar el reporte hacen falta `llncs.cls` y `splncs04.bst` de Springer (paquete `llncs` en CTAN; no se incluyen) y `pdflatex`.
Las tablas y figuras se regeneran con `python3 reporte/gen.py resultados_cluster/1000it resultados_cluster/5000it` (requiere Pillow).
