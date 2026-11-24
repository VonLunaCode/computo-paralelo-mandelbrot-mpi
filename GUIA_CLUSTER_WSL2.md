# Guía: cluster MPI de 3 laptops con WSL2

**Roles:** Vivobook = maestro (rank 0, solo reparte) · Laptop con GPU = trabajador · Tercera laptop = trabajador.
Todo corre en **Ubuntu 24.04 dentro de WSL2** en las 3, con la **misma versión de OpenMPI** y el **mismo nombre de usuario Linux**.

> La GPU no se usa: el programa es solo CPU (MPI). Participa con sus núcleos.

---

## 0. Qué comprar / conseguir (red por cable)

| Cosa | Cantidad | Nota |
|---|---|---|
| **Switch gigabit sin administrar** de 5 puertos (TP-Link TL-SG105, D-Link DGS-1005, etc.) | 1 | ~$300–450 MXN. Sin configuración: enchufar y listo. |
| Cables de red Cat5e/Cat6 cortos | 3 | |
| **Adaptador USB-Ethernet gigabit** (USB 3.0 o USB-C) | 1 por laptop *sin* puerto RJ45 | Muchas Vivobook y ultrabooks ya no traen RJ45. Revisen las 3. |

**Atajo sin comprar switch:** un router de casa ya es un switch (puertos LAN amarillos). Conecten las 3 laptops por cable a esos puertos. No necesita internet, solo funciona como switch.

**¿Y por WiFi?** Funciona (el tráfico es poco: el 8K son ~66 MB en total), pero la latencia varía y ensucia las mediciones. Recomendación: **medir con cable** y, si hay tiempo, repetir una vez por WiFi y **comparar en el reporte** (`ETIQUETA=wifi`). Es un experimento gratis y se ve bien.

Antes de medir, en **las 3 laptops**:
- Conectadas a la corriente, plan de energía **"Mejor rendimiento"**, sin suspensión.
- Cerrar navegadores y todo lo pesado. Los tiempos dependen de eso.

---

## 1. Red por cable con IP fija (en Windows, las 3)

Subred sin gateway: `192.168.50.0/24`. Mantengan el WiFi encendido si quieren internet; el cluster usa solo la subred del cable.

| Laptop | IP |
|---|---|
| Vivobook (maestro) | 192.168.50.11 |
| Laptop con GPU | 192.168.50.12 |
| Tercera laptop | 192.168.50.13 |

PowerShell **como administrador** (cambia `Ethernet` por el nombre real del adaptador, míralo con `Get-NetAdapter`):

```powershell
Get-NetAdapter
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.50.11 -PrefixLength 24   # .12 / .13 en las otras
Set-NetConnectionProfile -InterfaceAlias "Ethernet" -NetworkCategory Private
```

Prueba desde cualquiera: `ping 192.168.50.12`. Si no responde, revisa cable, IP y que el perfil sea *Private*.

---

## 2. WSL2 + Ubuntu 24.04 (en las 3)

```powershell
wsl --install -d Ubuntu-24.04
wsl --update
```
Reinicia si lo pide y crea el usuario Linux. **Usen el mismo nombre de usuario en las 3** (ej. `cluster`).

### Red en modo espejo
Crea/edita `C:\Users\<tu usuario>\.wslconfig`:

```ini
[wsl2]
networkingMode=mirrored
```

Y abre el firewall de Hyper-V hacia WSL (PowerShell administrador):

```powershell
Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction Allow
wsl --shutdown
```

> Requiere Windows 11 22H2 o superior. Si alguna laptop no lo soporta, avisen y vemos plan B (mismo plan con *port proxy*).

En Windows Defender, la regla más simple: permitir entrada desde `192.168.50.0/24` (los puertos de OpenMPI son dinámicos):

```powershell
New-NetFirewallRule -DisplayName "Cluster MPI" -Direction Inbound -Action Allow -RemoteAddress 192.168.50.0/24
```

Dentro de WSL (`wsl`), comprueba que ves la IP del cable: `ip -4 addr` debe mostrar `192.168.50.x`.

---

## 3. Preparar cada nodo (dentro de WSL, en las 3)

Copia la carpeta `cluster/` a `~/cluster` (puedes hacerlo desde Windows: `\\wsl$\Ubuntu-24.04\home\<usuario>\cluster`).

```bash
cd ~/cluster
bash setup_nodo.sh
```
Instala OpenMPI + SSH (puerto **2222**) y genera la llave. Al final imprime tu llave pública.

### SSH sin contraseña
Cada laptop debe poder entrar a las otras. Lo mínimo: el **maestro** debe entrar a las 3 (incluida sí misma). Desde la Vivobook:

```bash
ssh-copy-id -p 2222 cluster@192.168.50.12
ssh-copy-id -p 2222 cluster@192.168.50.13
ssh-copy-id -p 2222 cluster@192.168.50.11
```
Comprueba: `ssh 192.168.50.12 hostname` debe responder **sin pedir contraseña**. (Los trabajadores también conviene que se vean entre sí: haz lo mismo desde cada uno.)

---

## 4. Archivo `hosts` (solo en el maestro)

```bash
cd ~/cluster
cp hosts.example hosts
nano hosts        # ajusta slots = núcleos FÍSICOS de cada trabajador
```
Cuenta núcleos con `lscpu` (`Core(s) per socket` × `Socket(s)`). **La primera línea (maestro) siempre `slots=1`.**

---

## 5. Prueba rápida del cluster

```bash
cd ~/cluster
export HWLOC_COMPONENTS=-gl
mpirun --hostfile hosts --mca btl_tcp_if_include 192.168.50.0/24 --mca oob_tcp_if_include 192.168.50.0/24 \
       -np 3 hostname
```
Debe imprimir los nombres de las 3 laptops. Si funciona, el cluster está vivo.

---

## 6. Correr todo y recopilar datos automáticamente

En el **maestro**:

```bash
cd ~/cluster
chmod +x correr_pruebas.sh
ETIQUETA=cable ./correr_pruebas.sh
```

El script, solo, hace todo esto:
1. Compila el programa en cada nodo (misma ruta `~/cluster`).
2. Guarda hardware, versiones y **latencia de red** (`ping`) en `info_cluster.txt`.
3. Mide **T₁ (secuencial) en cada laptop por separado** → `baseline_T1_por_nodo.csv`.
4. Barre **P = 2, 4, 8, … hasta el total de slots** para las 3 pruebas, con **3 repeticiones** cada una.
5. Guarda por cada corrida el tiempo de cálculo, la espera y las **tareas por proceso y por laptop** → `por_proceso.csv`.
6. Genera `resumen.csv` (promedios, speedup y eficiencia) y las imágenes en `img/`.

Todo queda en `resultados/<fecha>_cable_1000it_b32/`.

Variantes útiles:
```bash
ITER=5000 ETIQUETA=cable ./correr_pruebas.sh          # carga alta (rango 1k–5k de la diapositiva)
BLOQUE=64 ETIQUETA=cable ./correr_pruebas.sh          # bloque 64x64
TESTS="1920 1080" REPS=1 ./correr_pruebas.sh          # humo rápido, solo prueba 1
ETIQUETA=wifi ./correr_pruebas.sh                     # misma prueba por WiFi, para comparar
```

### Qué datos salen y para qué sirven en el reporte
| Archivo | Métrica de la diapositiva |
|---|---|
| `resultados.csv` | Tiempo de ejecución de las 3 pruebas |
| `resumen.csv` | Speedup y eficiencia del cluster |
| `por_proceso.csv` | % / tiempo de espera de los trabajadores y reparto de tareas por laptop (la heterogeneidad) |
| `info_cluster.txt` | Descripción del hardware y la red |

**Nota para el reporte (definiciones):** speedup = T₁ / T_P, con T₁ medido en cada laptop; el resumen lo da contra cada una. La eficiencia se calcula contra el mejor T₁ y el número de trabajadores (P−1). En un cluster heterogéneo esto es una aproximación: dilo explícitamente.

---

## 7. Problemas típicos

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| `mpirun` se queda colgado sin salida | hwloc intenta hablar con un servidor X | Ya va `HWLOC_COMPONENTS=-gl` en el script; si lo corres a mano, expórtalo. |
| `Permission denied (publickey)` | Falta `ssh-copy-id` | Repite el paso de SSH. |
| `mpirun` se cuelga en el arranque entre laptops | Firewall o perfil de red *Public* | Revisa §1 y §2 (regla de firewall + `Private`). |
| Intenta usar la IP del WiFi | Más de una interfaz | Ya se fija con `btl_tcp_if_include` a la subred del cable. |
| `ssh` pide confirmación de host | Primera conexión | `setup_nodo.sh` usa `accept-new`; o conecta una vez a mano. |
| Usuarios distintos entre laptops | Rutas `~/cluster` no coinciden | Mismo usuario en las 3. |

Si algo falla, no improvisen: manden la salida exacta del error.
