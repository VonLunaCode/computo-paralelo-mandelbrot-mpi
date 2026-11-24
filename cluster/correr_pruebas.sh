#!/usr/bin/env bash
# correr_pruebas.sh — Ejecuta las pruebas del cluster y recopila datos automaticamente.
# Se corre EN EL MAESTRO (Vivobook), dentro de ~/cluster:   ./correr_pruebas.sh
#
# Variables opcionales (ejemplos):
#   ITER=5000 REPS=3 ./correr_pruebas.sh
#   TESTS="1920 1080" ./correr_pruebas.sh            # solo prueba 1
#   PLIST="2 4 8 12" ./correr_pruebas.sh             # valores de P a barrer
#   SUBNET=192.168.50.0/24 HOSTFILE=hosts ./correr_pruebas.sh
set -euo pipefail
cd "$(dirname "$0")"

HOSTFILE=${HOSTFILE:-hosts}
SUBNET=${SUBNET:-192.168.50.0/24}
ITER=${ITER:-1000}
BLOQUE=${BLOQUE:-32}
REPS=${REPS:-3}
TESTS=${TESTS:-"1920 1080;3840 2160;7680 4320"}
ETIQUETA=${ETIQUETA:-red}          # ej: cable, wifi  (para comparar en el reporte)
DIR="$HOME/cluster"
OUT="resultados/$(date +%Y%m%d_%H%M%S)_${ETIQUETA}_${ITER}it_b${BLOQUE}"
mkdir -p "$OUT/logs" "$OUT/img"

MCA="--mca btl_tcp_if_include $SUBNET --mca oob_tcp_if_include $SUBNET"
ENVX="-x HWLOC_COMPONENTS=-gl"
export HWLOC_COMPONENTS=-gl
unset DISPLAY || true

[ -f "$HOSTFILE" ] || { echo "No existe $HOSTFILE (copia hosts.example a hosts)"; exit 1; }
mapfile -t NODOS < <(awk '!/^#/ && NF {print $1}' "$HOSTFILE")
TOTAL=$(awk '!/^#/ && NF {for(i=2;i<=NF;i++) if($i ~ /^slots=/){split($i,a,"=");s+=a[2]}} END{print s}' "$HOSTFILE")

es_local() { [ "$1" = "127.0.0.1" ] || [ "$1" = "localhost" ] || hostname -I | tr ' ' '\n' | grep -qx "$1"; }
en_nodo() { local ip=$1; shift; if es_local "$ip"; then bash -c "$*"; else ssh -o BatchMode=yes -o ConnectTimeout=8 "$ip" "$*"; fi; }

echo "== Nodos: ${NODOS[*]} | slots totales: $TOTAL | salida: $OUT"

# 1) Distribuir y compilar en cada nodo (mismo usuario y misma ruta ~/cluster en todos)
for ip in "${NODOS[@]}"; do
  echo "-- Compilando en $ip"
  if ! es_local "$ip"; then
    ssh -o BatchMode=yes "$ip" "mkdir -p $DIR" && scp -q mandelbrot_mpi.c "$ip:$DIR/"
  fi
  en_nodo "$ip" "cd $DIR && mpicc -O3 -std=c99 -Wall -o mandelbrot_mpi mandelbrot_mpi.c -lm"
done

# 2) Metadatos: hardware, versiones y latencia de red
{
  echo "fecha: $(date -Is)"; echo "etiqueta: $ETIQUETA  iter=$ITER bloque=$BLOQUE reps=$REPS subnet=$SUBNET"
  echo "mpirun: $(mpirun --version | head -1)"
  for ip in "${NODOS[@]}"; do
    echo; echo "=== $ip ==="
    en_nodo "$ip" "hostname; nproc; lscpu | grep -E 'Model name|^CPU\(s\)|Thread|Core|MHz|L3'; free -m | sed -n 2p; uname -r"
  done
  echo; echo "=== Latencia desde el maestro (ping x20) ==="
  for ip in "${NODOS[@]}"; do es_local "$ip" || { echo "-> $ip"; ping -c 20 -q "$ip" | tail -2; }; done
} > "$OUT/info_cluster.txt" 2>&1
echo "-- Metadatos en $OUT/info_cluster.txt"

CAB="prueba,rep,P,W,H,iter,bloque,tareas,T_total,T_calc_prom,T_espera_prom,pct_espera"
echo "$CAB" > "$OUT/resultados.csv"
echo "prueba,P,rep,rank,t_calc,t_espera,tareas,host" > "$OUT/por_proceso.csv"
echo "nodo,$CAB" > "$OUT/baseline_T1_por_nodo.csv"

# Valores de P: potencias de 2 menores que el total, y el total
if [ -z "${PLIST:-}" ]; then
  PLIST=""; p=2; while [ $p -lt "$TOTAL" ]; do PLIST="$PLIST $p"; p=$((p*2)); done; PLIST="$PLIST $TOTAL"
fi
echo "-- P a barrer:$PLIST"

IFS=';' read -ra LISTA <<< "$TESTS"

ejecutar() {   # ejecutar <etiqueta_prueba> <rep> <args mpirun...> -- <W> <H> [imagen]
  local prueba=$1 rep=$2; shift 2
  local mpiargs=(); while [ "$1" != "--" ]; do mpiargs+=("$1"); shift; done; shift
  local W=$1 H=$2 img=${3:-}
  local log="$OUT/logs/${prueba}_$(echo "${mpiargs[*]}" | tr -c 'A-Za-z0-9\n' '_')_r${rep}"
  mpirun "${mpiargs[@]}" "$DIR/mandelbrot_mpi" "$W" "$H" "$ITER" "$BLOQUE" $img >"$log.out" 2>"$log.err" </dev/null
  tail -1 "$log.out"
}

# 3) Linea base T1: el programa secuencial en CADA nodo por separado (para el speedup)
n=0
for t in "${LISTA[@]}"; do
  n=$((n+1)); read -r W H <<< "$t"
  for ip in "${NODOS[@]}"; do
    for rep in $(seq 1 "$REPS"); do
      echo "-- T1 prueba$n en $ip (rep $rep)"
      linea=$(ejecutar "T1_p${n}_$ip" "$rep" --host "$ip:1" -np 1 $MCA $ENVX -- "$W" "$H")
      echo "$ip,p$n,$rep,$linea" >> "$OUT/baseline_T1_por_nodo.csv"
    done
  done
done

# 4) Barrido de P sobre el cluster completo (rank 0 = maestro en la primera linea del hostfile)
n=0
for t in "${LISTA[@]}"; do
  n=$((n+1)); read -r W H <<< "$t"
  for P in $PLIST; do
    for rep in $(seq 1 "$REPS"); do
      img=""; [ "$rep" = 1 ] && [ "$P" = "$TOTAL" ] && img="$OUT/img/prueba${n}_${W}x${H}.png"
      echo "-- prueba$n  P=$P  rep=$rep"
      linea=$(ejecutar "p${n}_P${P}" "$rep" --hostfile "$HOSTFILE" --map-by slot -np "$P" $MCA $ENVX -- "$W" "$H" $img)
      echo "p$n,$rep,$linea" >> "$OUT/resultados.csv"
      # estadisticas por proceso (stderr del maestro)
      lg=$(ls -t "$OUT"/logs/p${n}_P${P}_*_r${rep}.err | head -1)
      grep -E '^#  [0-9]+,' "$lg" | sed 's/^#  //' | awk -F', *' -v pr="p$n" -v P="$P" -v rep="$rep" \
        '{print pr","P","rep","$1","$2","$3","$4","$5}' >> "$OUT/por_proceso.csv"
    done
  done
done

# 5) Resumen: promedio por (prueba,P), speedup y eficiencia contra el T1 del nodo maestro
python3 - "$OUT" <<'PY' || echo "(sin python3: omito resumen, los CSV crudos estan completos)"
import csv, sys, collections
out = sys.argv[1]
res = collections.defaultdict(list)
for r in csv.DictReader(open(f"{out}/resultados.csv")):
    res[(r["prueba"], int(r["P"]))].append(r)
t1 = collections.defaultdict(list)
for r in csv.DictReader(open(f"{out}/baseline_T1_por_nodo.csv")):
    t1[(r["nodo"], r["prueba"])].append(float(r["T_total"]))
nodos = sorted({k[0] for k in t1})
def m(x): return sum(x)/len(x)
with open(f"{out}/resumen.csv", "w") as f:
    f.write("prueba,P,T_total_prom,pct_espera_prom," + ",".join(f"speedup_vs_{n}" for n in nodos) + ",eficiencia_vs_mejor_T1\n")
    for (pr, P), rows in sorted(res.items()):
        T = m([float(r["T_total"]) for r in rows]); esp = m([float(r["pct_espera"]) for r in rows])
        sp = [m(t1[(n, pr)]) / T for n in nodos]
        mejor = min(m(t1[(n, pr)]) for n in nodos)
        trab = max(P - 1, 1)
        f.write(f"{pr},{P},{T:.4f},{esp:.2f}," + ",".join(f"{s:.3f}" for s in sp) + f",{mejor/T/trab:.3f}\n")
print(open(f"{out}/resumen.csv").read())
PY

echo; echo "Listo. Todo en: $OUT"
echo "Archivos: resultados.csv  baseline_T1_por_nodo.csv  por_proceso.csv  resumen.csv  info_cluster.txt  img/  logs/"
