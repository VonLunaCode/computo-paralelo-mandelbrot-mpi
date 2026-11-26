#!/usr/bin/env python3
"""Genera report.tex (LNCS) a partir de los CSV reales de las corridas."""
import csv, os, sys, collections

def leer(p):
    return list(csv.DictReader(open(p)))

def cargar(d):
    res = leer(f"{d}/resumen.csv")
    t1 = leer(f"{d}/baseline_T1_por_nodo.csv")
    raw = leer(f"{d}/resultados.csv")
    return res, t1, raw

NODOS = {"192.168.50.11": "N1 (maestro)", "192.168.50.12": "N2", "192.168.50.13": "N3"}
TAM = {"p1": ("1920", "1080"), "p2": ("3840", "2160"), "p3": ("7680", "4320")}

def tabla_t1(t1, it):
    filas = []
    for pr in ("p1", "p2", "p3"):
        celdas = []
        for ip in NODOS:
            v = [float(r["T_total"]) for r in t1 if r["nodo"] == ip and r["prueba"] == pr]
            celdas.append(f"{sum(v)/len(v):.2f}" if v else "--")
        if all(c == "--" for c in celdas):
            continue
        w, h = TAM[pr]
        filas.append(f"{w}$\\times${h} & " + " & ".join(celdas) + r" \\ \hline")
    return "\n".join(filas)

def tabla_prueba(res, raw, pr):
    ntar = next(r["tareas"] for r in raw if r["prueba"] == pr)
    filas = []
    for r in res:
        if r["prueba"] != pr:
            continue
        filas.append(
            f"{r['P']} & {float(r['T_total_prom']):.3f} & {float(r['speedup_vs_192.168.50.11']):.2f} & "
            f"{float(r['eficiencia_vs_mejor_T1'])*100:.1f}\\,\\% & {float(r['pct_espera_prom']):.1f}\\,\\% \\\\ \\hline")
    return "\n".join(filas), ntar

def grafica(res, pr, campo, ymax, etiqueta, escala=1.0):
    pts = [(r["P"], float(r[campo]) * escala) for r in res if r["prueba"] == pr]
    coords = " ".join(f"({i},{v:.3f})" for i, (_, v) in enumerate(pts))
    ticks = "".join(f"\\draw (%d,0)--(%d,-0.06) node[below,font=\\scriptsize]{{%s}};" % (i, i, P) for i, (P, _) in enumerate(pts))
    return coords, ticks

def figura(res, campo, titulo, ymax, ylab, escala=1.0):
    colores = {"p1": "blue", "p2": "red", "p3": "black"}
    nombres = {"p1": "1080p", "p2": "4K", "p3": "8K"}
    sx = 0.9
    sy = 3.0 / ymax
    s = ["\\begin{tikzpicture}[x=%.2fcm,y=%.3fcm]" % (sx, sy),
         f"\\draw[->] (0,0)--(5.6,0); \\draw[->] (0,0)--(0,{ymax*1.02:.2f});",
         f"\\node[font=\\scriptsize,rotate=90] at (-0.9,{ymax/2:.1f}) {{{ylab}}};",
         "\\node[font=\\scriptsize] at (2.8,-%.2f) {Procesos MPI ($P$)};" % (0.55/ sy * 1.0)]
    n = 6
    for pr in ("p1", "p2", "p3"):
        pts = [float(r[campo]) * escala for r in res if r["prueba"] == pr]
        if not pts:
            continue
        coords = " ".join(f"({i},{v:.3f})" for i, v in enumerate(pts))
        s.append(f"\\draw[{colores[pr]},thick] plot[mark=*,mark size=1pt] coordinates {{{coords}}};")
    Ps = [r["P"] for r in res if r["prueba"] == "p1"]
    for i, P in enumerate(Ps):
        s.append(f"\\draw ({i},0)--({i},-%.2f) node[below,font=\\scriptsize]{{{P}}};" % (0.08 / sy))
    for v in range(0, int(ymax) + 1, max(1, int(ymax // 4))):
        s.append(f"\\draw (0,{v})--(-0.07,{v}) node[left,font=\\scriptsize]{{{v}}};")
    ly = ymax * 0.97
    for k, pr in enumerate(("p1", "p2", "p3")):
        s.append(f"\\draw[{colores[pr]},thick] (0.3,{ly - k*ymax*0.1:.2f})--(0.8,{ly - k*ymax*0.1:.2f}) node[right,font=\\scriptsize,black]{{{nombres[pr]}}};")
    s.append("\\end{tikzpicture}")
    return "\n".join(s)

d1000 = sys.argv[1]
d5000 = sys.argv[2] if len(sys.argv) > 2 and os.path.exists(sys.argv[2] + "/resumen.csv") else None
res, t1, raw = cargar(d1000)
t1tab = tabla_t1(t1, 1000)
tabs = {pr: tabla_prueba(res, raw, pr) for pr in ("p1", "p2", "p3")}
from PIL import Image, ImageDraw

def png(res, campo, ymax, ylab, path):
    W, H, L, B, T, R = 900, 560, 90, 70, 30, 30
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    d.line([(L, T), (L, H - B), (W - R, H - B)], fill="black", width=2)
    Ps = [r["P"] for r in res if r["prueba"] == "p1"]
    gx = lambda i: L + 40 + i * (W - L - R - 80) / max(1, len(Ps) - 1)
    gy = lambda v: H - B - v * (H - B - T) / ymax
    for k in range(5):
        v = ymax * k / 4
        d.line([(L - 5, gy(v)), (L, gy(v))], fill="black"); d.text((L - 45, gy(v) - 6), f"{v:.0f}", fill="black")
        d.line([(L, gy(v)), (W - R, gy(v))], fill=(225, 225, 225))
    for i, P in enumerate(Ps):
        d.text((gx(i) - 6, H - B + 8), str(P), fill="black")
    d.text((W // 2 - 60, H - 28), "Procesos MPI (P)", fill="black"); d.text((8, T - 6), ylab, fill="black")
    col = {"p1": (30, 60, 220), "p2": (210, 40, 40), "p3": (20, 20, 20)}
    nom = {"p1": "1920x1080", "p2": "3840x2160", "p3": "7680x4320"}
    for n, pr in enumerate(("p1", "p2", "p3")):
        pts = [(gx(i), gy(float(r[campo]))) for i, r in enumerate([r for r in res if r["prueba"] == pr])]
        if len(pts) > 1: d.line(pts, fill=col[pr], width=3)
        for x, y in pts: d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=col[pr])
        d.line([(W - 230, T + 10 + n * 20), (W - 200, T + 10 + n * 20)], fill=col[pr], width=3)
        d.text((W - 192, T + 4 + n * 20), nom[pr], fill="black")
    im.save(path)

png(res, "speedup_vs_192.168.50.11", 12, "Speedup vs. N1", "fig_speedup.png")
png(res, "pct_espera_prom", 70, "Espera media de trabajadores (%)", "fig_espera.png")
fig_sp = "\\includegraphics[width=.9\\linewidth]{fig_speedup.png}"
fig_es = "\\includegraphics[width=.9\\linewidth]{fig_espera.png}"

extra5k = ""
if d5000:
    r5, t5, w5 = cargar(d5000)
    b5 = []
    for pr in ("p1", "p2"):
        if any(r["prueba"] == pr for r in r5):
            tb, nt = tabla_prueba(r5, w5, pr)
            w, h = TAM[pr]
            b5.append(f"\\multicolumn{{5}}{{|l|}}{{\\textit{{{w}$\\times${h}, {nt} tareas}}}} \\\\ \\hline\n{tb}")
    extra5k = r"""
\subsection{Prueba de sensibilidad con 5000 iteraciones}
Para cubrir el extremo superior del intervalo pedido (1k a 5k iteraciones) se repitió el barrido solo con las
pruebas 1 y 2, con una repetición. La Tabla~\ref{tab:5k} muestra los resultados; la prueba 3 no se repitió por
falta de tiempo.
\begin{table}[t]
\caption{Resultados con 5000 iteraciones (1 repetición). Mismo esquema que las tablas anteriores.}\label{tab:5k}
\centering\footnotesize
\begin{tabular}{|r|r|r|r|r|}\hline
$P$ & $T_P$ (s) & Speedup & Eficiencia & Espera \\ \hline
""" + "\n".join(b5) + r"""
\end{tabular}
\end{table}
"""

tex = r"""\documentclass[runningheads]{llncs}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\def\figurename{Figura}\def\tablename{Tabla}\def\abstractname{Resumen}\def\keywordname{{\bfseries Palabras clave:}}\def\refname{Referencias}\AtBeginDocument{\def\andname{y}}
\usepackage{graphicx}
\usepackage{amsmath}
\begin{document}
\title{Renderizador distribuido del conjunto de Mandelbrot con MPI en un cl\'uster heterog\'eneo de tres laptops}
\titlerunning{Mandelbrot distribuido con MPI}
\author{Christian Luna Ortiz, Misael Reynoso Aguayo, Camila Serrano Trinidad y Irais Gisela Macuil Chapuli}
\authorrunning{Luna Ortiz et al.}
\institute{Universidad del Valle de Puebla (UVP)}
\maketitle

\begin{abstract}
Se dise\~n\'o, implement\'o y evalu\'o un renderizador distribuido del conjunto de Mandelbrot con el modelo
maestro--trabajador sobre MPI (Open MPI 4.1.6), ejecutado en tres laptops heterog\'eneas conectadas por Ethernet
y corriendo Ubuntu 24.04 en WSL2. Se midieron tiempo de ejecuci\'on, speedup, eficiencia y porcentaje de espera de los
trabajadores en tres resoluciones (1920$\times$1080, 3840$\times$2160 y 7680$\times$4320) con 1000 iteraciones.
Con $P\le 16$ el programa escala bien dentro de un solo nodo (eficiencia de 83--95\,\% hasta $P=8$); al involucrar
los tres nodos ($P=32$ y $P=40$) el porcentaje de espera de los trabajadores sube a 46--64\,\% y la ganancia se
estanca; con 5000 iteraciones (pruebas 1 y 2) el speedup llega a 14.8. Se discuten las causas probables, que no fueron verificadas por separado.
\keywords{MPI \and maestro--trabajador \and Mandelbrot \and speedup \and cl\'uster heterog\'eneo}
\end{abstract}

\section{Introducci\'on}
El conjunto de Mandelbrot es un problema \emph{embarazosamente paralelo}: cada p\'ixel se calcula de forma
independiente iterando $z_{n+1}=z_n^2+c$ hasta que $|z|>2$ o se alcanza el m\'aximo de iteraciones~\cite{mandelbrot}.
Sin embargo, el costo por p\'ixel es muy desigual (los puntos del conjunto consumen todas las iteraciones), por lo que un
reparto est\'atico desbalancea la carga. Este trabajo implementa un esquema din\'amico maestro--trabajador con paso de
mensajes~\cite{gropp} y eval\'ua su comportamiento en un cl\'uster heterog\'eneo.

\section{Dise\~no}
La imagen de $W\times H$ p\'ixeles se divide en bloques de $32\times 32$. Para 1920$\times$1080 resultan
$60\times 34=2040$ tareas, para 3840$\times$2160 resultan %s y para 7680$\times$4320 resultan %s tareas. El plano complejo
se fija en $x\in[-2.0,\,0.5]$, $y\in[-1.25,\,1.25]$; el p\'ixel $(i,j)$ se convierte a $c=a+bi$ con
$a=x_{\min}+i\,\Delta x/W$ y $b=y_{\min}+j\,\Delta y/H$.

El proceso 0 (maestro) administra una cola de identificadores de bloque; cada trabajador solicita una tarea, la
calcula y devuelve la matriz del bloque; el maestro la coloca en la matriz final y, al agotarse la cola, indica a los
trabajadores que terminen. La imagen final se guarda en PNG. Cada trabajador reporta su tiempo de c\'alculo, su tiempo
de espera (bloqueado esperando una tarea) y las tareas atendidas.

\section{Entorno y metodolog\'ia}
\begin{table}[t]
\caption{Nodos del cl\'uster (red \texttt{192.168.50.0/24}, Ethernet; RTT medio desde el maestro: 2.97\,ms y 3.32\,ms).}
\centering\footnotesize
\begin{tabular}{|l|l|r|r|}\hline
Nodo & CPU & Hilos & RAM (MB)\\ \hline
N1 (maestro) & AMD Ryzen 7 5700U & 16 & 7612 \\ \hline
N2 & AMD Ryzen 9 9955HX & 32 & 15573 \\ \hline
N3 & Intel Core i5-1035G1 & 8 & 3787 \\ \hline
\end{tabular}
\end{table}
Se usaron 40 \emph{slots} en total (16 en N1, 16 en N2 y 8 en N3) y la pol\'itica \texttt{--map-by slot}, de modo que los
primeros 16 procesos caen en N1, los siguientes 16 en N2 y el resto en N3. En consecuencia, con $P\le16$ \emph{todos}
los procesos corren en el nodo maestro; N2 se incorpora con $P=32$ y N3 con $P=40$.

Las m\'etricas son: $T_P$ (tiempo total, s); speedup $S_P=T_1/T_P$, con $T_1$ la ejecuci\'on secuencial en N1, que fue el
nodo m\'as r\'apido en una sola hebra; eficiencia $E_P=T_1/(T_P\,(P-1))$, contando $P-1$ trabajadores porque el maestro
no calcula; y porcentaje de espera, el cociente entre el tiempo medio de espera de los trabajadores y $T_P$.
Cada configuraci\'on se midi\'o \textbf{una sola vez} con 1000 iteraciones, as\'i que no hay barras de error.
\begin{table}[t]
\caption{Tiempo secuencial $T_1$ (s) en cada nodo, 1000 iteraciones.}
\centering\footnotesize
\begin{tabular}{|l|r|r|r|}\hline
Prueba & N1 & N2 & N3 \\ \hline
@@T1TAB@@
\end{tabular}
\end{table}

\section{Resultados}
Las Tablas~\ref{tab:p1}--\ref{tab:p3} resumen las tres pruebas y las Figuras~\ref{fig:sp} y~\ref{fig:es} muestran el speedup y la
espera. La Figura~\ref{fig:img} es la imagen generada en la prueba 1.
""".replace("@@NP2@@", tabs["p2"][1]).replace("@@NP3@@", tabs["p3"][1]).replace("@@T1TAB@@", t1tab)

for pr, lab in (("p1", "tab:p1"), ("p2", "tab:p2"), ("p3", "tab:p3")):
    w, h = TAM[pr]
    body, nt = tabs[pr]
    tex += r"""
\begin{table}[t]
\caption{Prueba %s: %s$\times$%s p\'ixeles, %s tareas, 1000 iteraciones.}\label{%s}
\centering\footnotesize
\begin{tabular}{|r|r|r|r|r|}\hline
$P$ & $T_P$ (s) & Speedup & Eficiencia & Espera \\ \hline
%s
\end{tabular}
\end{table}
""" % (pr[1], w, h, nt, lab, body)

tex += r"""
\begin{figure}[t]
\centering
@@FSP@@
\caption{Speedup respecto a $T_1$ de N1 en funci\'on de $P$ (1 repetici\'on).}\label{fig:sp}
\end{figure}
\begin{figure}[t]
\centering
@@FES@@
\caption{Porcentaje medio de espera de los trabajadores en funci\'on de $P$.}\label{fig:es}
\end{figure}
\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{prueba1_1920x1080.png}
\caption{Imagen 1920$\times$1080 generada por el cl\'uster (ejecuci\'on con $P=40$).}\label{fig:img}
\end{figure}
@@EXTRA@@

\section{Discusi\'on}
\textbf{Dentro de un nodo.} Hasta $P=8$ la eficiencia se mantiene entre 83\,\% y 95\,\% y la espera es menor a 2.1\,\%: el
maestro alcanza a alimentar a los trabajadores. Con $P=16$ la eficiencia baja a 64--67\,\% y el speedup se queda cerca de 10,
lo cual es consistente con que los 16 hilos de N1 son SMT sobre 8 n\'ucleos f\'isicos (el Ryzen 7 5700U tiene 8 n\'ucleos);
esta explicaci\'on no se verific\'o midiendo con SMT apagado.

\textbf{Entre nodos.} Al pasar a $P=32$ y $P=40$ la espera salta a 45--62\,\% en la prueba 3 y a 47--64\,\% en las
pruebas 1 y 2, y el tiempo deja de mejorar (en la prueba 3 empeora de 1.88\,s a 2.48\,s entre $P=32$ y $P=40$). Las causas
plausibles son (i) que el maestro, que recibe cada bloque por la red (RTT de 3\,ms) y atiende una cola de miles de tareas
peque\~nas, se convierte en cuello de botella, y (ii) que los trabajadores de N3, el nodo m\'as lento (su $T_1$ es de 1.9 a
2.4 veces el de N1), terminan tarde y dejan esperar al resto. Ninguna de las dos se aisl\'o con un experimento; son hip\'otesis.

\textbf{Efecto de las iteraciones.} Con 5000 iteraciones (Tabla~\ref{tab:5k}) el speedup con $P=40$ sube a 14.0 en 1080p y 14.8 en 4K,
y la espera baja a 31\,\% y 22\,\%, frente a 61\,\% y 58\,\% con 1000 iteraciones. Es consistente con que m\'as c\'omputo por tarea
amortiza el costo de repartir y recibir bloques; no se prob\'o ninguna otra causa.

\textbf{Resoluci\'on.} La prueba 1 (1080p) tiene pocas tareas y $T_P$ ya es de 0.12\,s con $P=16$, por lo que el
sobrecosto de comunicaci\'on pesa m\'as; las pruebas 2 y 3 retrasan la saturaci\'on, como se espera de un problema
con m\'as trabajo por proceso.

\section{Limitaciones}
\begin{itemize}
\item Una repetici\'on por configuraci\'on; las diferencias peque\~nas entre filas pueden ser ruido.
\item Entorno virtualizado (WSL2 en modo de red espejo) y laptops con planes de energ\'ia y t\'ermica distintos; el $T_1$ de
N2 (Ryzen 9) result\'o mayor que el de N1 pese a ser un CPU m\'as potente, sin que se haya investigado la causa.
\item El barrido llena N1 antes que N2 y N3 (\texttt{--map-by slot}), por lo que no se compar\'o un mismo $P$
repartido entre nodos con $P$ concentrado en uno.
\item Los \emph{slots} se fijaron al n\'umero de hilos l\'ogicos; no se prob\'o con n\'ucleos f\'isicos.
\end{itemize}

\section{Conclusiones}
El esquema maestro--trabajador con cola din\'amica de bloques de $32\times32$ produce la imagen correcta en las tres
resoluciones pedidas y escala con eficiencia alta dentro de un nodo. En este cl\'uster de tres laptops por Ethernet la
ganancia se estanca al cruzar nodos y el tiempo de espera de los trabajadores domina, por lo que, con estas mediciones,
el speedup m\'aximo respecto al nodo maestro fue de 10.8 con 1000 iteraciones y de 14.8 con 5000 iteraciones (prueba 2). Mejorar el reparto (tareas m\'as grandes, pre-asignaci\'on
ponderada por velocidad de nodo) y repetir las mediciones quedan como trabajo futuro.

\begin{thebibliography}{8}
\bibitem{mandelbrot} Mandelbrot, B.B.: Fractal aspects of the iteration of $z\mapsto\lambda z(1-z)$ for complex
$\lambda$ and $z$. Annals of the New York Academy of Sciences \textbf{357}, 249--259 (1980)
\bibitem{gropp} Gropp, W., Lusk, E., Skjellum, A.: Using MPI: Portable Parallel Programming with the
Message-Passing Interface. MIT Press (1999)
\end{thebibliography}
\end{document}
""".replace("@@FSP@@", fig_sp).replace("@@FES@@", fig_es).replace("@@EXTRA@@", extra5k)

open("report.tex", "w").write(tex)
print("report.tex generado", len(tex), "bytes; 5k:", bool(d5000))
