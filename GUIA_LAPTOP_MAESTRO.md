# Guía — Laptop MAESTRA (Asus Vivobook)

Tu laptop será el **maestro** del cluster: reparte las tareas y arma la imagen final. No hace falta que sepas Linux: copia y pega los comandos en orden.
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
```
Mándale a Christian: la salida del diagnóstico + esta.

✅ **Listo por hoy.** Deja la laptop cargada para mañana.

---

## MAÑANA (con el cable/switch conectado)

### 7. IP fija (PowerShell como administrador)
Mira el nombre del adaptador cableado con `Get-NetAdapter` (suele llamarse `Ethernet`):

```powershell
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.50.11 -PrefixLength 24
Set-NetConnectionProfile -InterfaceAlias "Ethernet" -NetworkCategory Private
ping 192.168.50.12
```
(`.12` es la laptop de Christian, `.13` la trabajadora.)

### 8. Llaves SSH (dentro de Ubuntu — solo la maestra)
Pide la contraseña de `cluster` de cada laptop **una sola vez**:

```bash
ssh-copy-id -p 2222 cluster@192.168.50.11
ssh-copy-id -p 2222 cluster@192.168.50.12
ssh-copy-id -p 2222 cluster@192.168.50.13
ssh 192.168.50.12 hostname     # debe contestar SIN pedir contraseña
```

### 9. Archivo hosts y prueba
```bash
cd ~/cluster
cp hosts.example hosts
nano hosts            # ajusta slots (núcleos físicos) de cada trabajadora; Ctrl+O, Enter, Ctrl+X
export HWLOC_COMPONENTS=-gl
mpirun --hostfile hosts --mca btl_tcp_if_include 192.168.50.0/24 --mca oob_tcp_if_include 192.168.50.0/24 -np 3 hostname
```
Debe imprimir el nombre de las laptops. Si sale, corremos todo:

```bash
ETIQUETA=cable ./correr_pruebas.sh
```
Los resultados quedan en `~/cluster/resultados/`.

### Consejos para medir bien
- Todas **conectadas a la corriente**, plan de energía **"Mejor rendimiento"**, sin suspensión, y sin programas pesados abiertos.
- Mantén **una ventana de Ubuntu abierta** durante las pruebas (si WSL se apaga, el nodo desaparece).

Guía completa y solución de problemas: `GUIA_CLUSTER_WSL2.md`.
