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
