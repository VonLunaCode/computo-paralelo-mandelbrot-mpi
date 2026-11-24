# Guía — Laptop TRABAJADORA

Tu laptop será un **trabajador** del cluster: recibe bloques de la imagen, los calcula y los devuelve al maestro (la Vivobook). No hace falta que sepas Linux: copia y pega los comandos en orden.
**Meta de hoy:** dejar todo instalado y probado **sin necesitar cables ni a las otras laptops**. Mañana solo conectamos la red.

- Necesitas: Windows 11 (22H2 o más nuevo), internet, ~10 GB libres, conectada a la corriente.
- Usuario de Linux: **`cluster`** (obligatorio, igual en las 3 laptops).
- Contraseña de Linux: la eliges tú; **anótala**, mañana la piden una vez.

---

## HOY (sin cables)

### 1. Diagnóstico (30 segundos)
Abre **PowerShell** (normal) y pega:

```powershell
cd $env:USERPROFILE\Downloads
iwr https://raw.githubusercontent.com/VonLunaCode/computo-paralelo-mandelbrot-mpi/main/cluster/diagnostico.ps1 -OutFile diagnostico.ps1
powershell -ExecutionPolicy Bypass -File .\diagnostico.ps1
```
**Mándale la salida completa a Christian.** (Solo lee datos, no cambia nada.)

### 2. Instalar WSL2 (PowerShell como administrador)
Clic derecho en PowerShell → *Ejecutar como administrador*:

```powershell
wsl --install -d Ubuntu-24.04
```
Cuando termine, **reinicia Windows**. Al volver, se abre sola una ventana de Ubuntu: te pide crear usuario → escribe **`cluster`** y una contraseña (no se ve al teclear, es normal).

### 3. Modo de red espejo + firewall (PowerShell como administrador)
```powershell
@"
[wsl2]
networkingMode=mirrored
"@ | Set-Content -Encoding ascii "$env:USERPROFILE\.wslconfig"

Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction Allow
New-NetFirewallRule -DisplayName "Cluster MPI" -Direction Inbound -Action Allow -RemoteAddress 192.168.50.0/24
wsl --shutdown
```

### 4. Descargar el proyecto e instalar (dentro de Ubuntu)
Abre **Ubuntu** desde el menú Inicio y pega **línea por línea**:

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/VonLunaCode/computo-paralelo-mandelbrot-mpi.git ~/mandelbrot-mpi
cp -r ~/mandelbrot-mpi/cluster ~/cluster
cd ~/cluster && bash setup_nodo.sh
```
Tarda unos minutos (instala OpenMPI y SSH). Pide tu contraseña de Linux.

### 5. Prueba local (debe funcionar sola, sin red)
```bash
cd ~/cluster
export HWLOC_COMPONENTS=-gl
mpicc -O3 -std=c99 -o mandelbrot_mpi mandelbrot_mpi.c -lm
mpirun --oversubscribe -n 4 ./mandelbrot_mpi 640 360 200 32 /tmp/prueba.png
```
**Está bien si** imprime una línea con números (`4,640,360,200,32,...`) y `# Imagen guardada: /tmp/prueba.png`.
Si algo falla, **copia el error tal cual** y mándaselo a Christian.

### 6. Verifica y manda captura
```bash
mpirun --version | head -1; nproc; lscpu | grep -E "Model name|Core\(s\) per socket"
sudo systemctl status ssh --no-pager | head -5
```
Mándale a Christian esa salida. `ssh` debe decir **active (running)**.

✅ **Listo por hoy.** Deja la laptop cargada para mañana.

---

## MAÑANA (con el cable/switch conectado)

### 7. IP fija (PowerShell como administrador)
Mira el nombre del adaptador cableado con `Get-NetAdapter` (suele llamarse `Ethernet`).
**Pon la IP que te toque** (pregunta a Christian; por defecto la trabajadora es `.13`):

```powershell
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.50.13 -PrefixLength 24
Set-NetConnectionProfile -InterfaceAlias "Ethernet" -NetworkCategory Private
ping 192.168.50.11
```
(`.11` es la Vivobook maestra, `.12` la laptop de Christian.)

### 8. Dejar el nodo disponible
- **Abre Ubuntu y déjalo abierto** durante todas las pruebas (si WSL se apaga, tu laptop desaparece del cluster).
- La maestra se conectará sola por SSH; solo te pedirá tu contraseña de `cluster` **una vez** en su pantalla.
- Cuando la maestra corra las pruebas, **no uses la laptop**: cierra navegadores y programas pesados.

### Consejos para medir bien
- **Conectada a la corriente**, plan de energía **"Mejor rendimiento"**, sin suspensión.
- Si algo no conecta, ejecuta en Ubuntu `ip -4 addr` y manda captura a Christian.

Guía completa y solución de problemas: `GUIA_CLUSTER_WSL2.md`.
