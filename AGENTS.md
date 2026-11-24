# Instrucciones para el agente (cualquier herramienta) — cluster MPI (Mandelbrot)

Este repo arma un cluster de 3 laptops Windows con WSL2 + OpenMPI. **Tu primera acción:** pregunta al usuario qué rol tiene esta laptop y no sigas hasta saberlo:

- **MAESTRA** (Asus Vivobook, IP 192.168.50.11) → sigue `GUIA_LAPTOP_MAESTRO.md`
- **TRABAJADORA** (IP 192.168.50.13) → sigue `GUIA_LAPTOP_TRABAJADORA.md`
- (La tercera, laptop de Christian con GPU, es la 192.168.50.12.)

La guía del rol es la fuente de verdad: ejecuta sus pasos **en orden**. `GUIA_CLUSTER_WSL2.md` es el contexto y la solución de problemas.

## Alcance
Solo el bloque **"HOY (sin cables)"**: diagnóstico, WSL2, modo espejo/firewall, clonar, `setup_nodo.sh` y la prueba local. El bloque "MAÑANA" (IP fija, SSH entre laptops, `hosts`, correr pruebas) **no lo hagas** salvo que el usuario lo pida y el cable ya esté conectado.

## Reglas
1. **Verifica antes de afirmar.** Tras cada paso comprueba su salida real. No digas "listo" sin que la prueba local del paso 5 imprima una línea de datos CSV y `# Imagen guardada`.
2. **Puntos donde debes parar y pedir al usuario** (no los saltes ni los simules):
   - Ventana de permisos de administrador (UAC) o abrir PowerShell como administrador.
   - **Reinicio de Windows** después de instalar WSL. No reinicies tú.
   - Crear el usuario de Linux: debe llamarse exactamente **`cluster`**. **La contraseña la escribe el usuario**; tú nunca la pides, la ves ni la guardas.
3. Solo toca lo que dicen las guías (WSL, `.wslconfig`, la regla de firewall `Cluster MPI` para `192.168.50.0/24`, la regla de Hyper-V). No cambies otras configuraciones de Windows, no abras puertos a internet, no desactives el antivirus.
4. No subas nada a internet ni al repo, y no guardes contraseñas ni llaves privadas en ningún archivo.
5. Si algo falla, muestra el error exacto, diagnostica la causa y propón el arreglo. No improvises comandos destructivos. Errores conocidos: `mpirun` colgado → exportar `HWLOC_COMPONENTS=-gl`; SSH en puerto 2222 (no 22).
6. Al terminar, resume al usuario en español qué quedó instalado y verificado, y qué falta para mañana. Pídele que le mande a Christian la salida del diagnóstico y de `mpirun --version`, `nproc`.

## Contexto técnico
- Código: `mandelbrot_mpi.c` (C + MPI). Rank 0 = maestro, resto = trabajadores. Compilar: `mpicc -O3 -std=c99 -o mandelbrot_mpi mandelbrot_mpi.c -lm`.
- Scripts en `cluster/`: `setup_nodo.sh`, `correr_pruebas.sh`, `diagnostico.ps1`, `hosts.example`.
- Mismo usuario (`cluster`) y misma ruta (`~/cluster`) en las 3 laptops.
- Responde siempre en español.
