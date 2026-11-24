/*
 * mandelbrot_mpi.c — Renderizador distribuido del conjunto de Mandelbrot
 * Arquitectura Maestro-Trabajador con MPI (asignacion dinamica de tareas).
 *
 * Compilar:  mpicc -O3 -std=c99 -o mandelbrot_mpi mandelbrot_mpi.c -lm
 * Ejecutar:  mpiexec -n <P> ./mandelbrot_mpi W H MAX_ITER BLOQUE [salida.png]
 *   P=1  -> modo secuencial (linea base T1 para el speedup)
 *   P>=2 -> rank 0 = maestro, ranks 1..P-1 = trabajadores
 *
 * Protocolo:
 *   trabajador -> maestro : int id_resultado (-1 = solo pide tarea) [+ datos uint16]
 *   maestro -> trabajador : int id_tarea (-1 = terminar)
 * Cada tarea es un bloque BxB (los bordes pueden ser menores).
 * Linea CSV final (stdout): P,W,H,iter,bloque,tareas,T_total,T_calc_prom,T_espera_prom,%espera
 */
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#define X_MIN (-2.0)
#define X_MAX (0.5)
#define Y_MIN (-1.25)
#define Y_MAX (1.25)

static int W, H, MAXIT, B, TX, TY;

/* Pixel (i=columna, j=fila) -> c = a + bi */
static inline void pixel_to_c(int i, int j, double *a, double *b) {
    *a = X_MIN + (X_MAX - X_MIN) * (double)i / (double)(W - 1);
    *b = Y_MIN + (Y_MAX - Y_MIN) * (double)j / (double)(H - 1);
}

/* z_{n+1} = z_n^2 + c ; devuelve iteraciones antes de escapar (|z|>2) */
static inline uint16_t mandel(double a, double b) {
    double x = 0.0, y = 0.0, x2 = 0.0, y2 = 0.0;
    int n = 0;
    while (n < MAXIT && x2 + y2 <= 4.0) {
        y = 2.0 * x * y + b;
        x = x2 - y2 + a;
        x2 = x * x;
        y2 = y * y;
        n++;
    }
    return (uint16_t)n;
}

/* Calcula el bloque 'id' en buf (bw*bh uint16). Devuelve dimensiones */
static void block_geom(int id, int *x0, int *y0, int *bw, int *bh) {
    int tx = id % TX, ty = id / TX;
    *x0 = tx * B;
    *y0 = ty * B;
    *bw = (*x0 + B > W) ? W - *x0 : B;
    *bh = (*y0 + B > H) ? H - *y0 : B;
}

static void compute_block(int id, uint16_t *buf) {
    int x0, y0, bw, bh;
    block_geom(id, &x0, &y0, &bw, &bh);
    for (int j = 0; j < bh; j++)
        for (int i = 0; i < bw; i++) {
            double a, b;
            pixel_to_c(x0 + i, y0 + j, &a, &b);
            buf[j * bw + i] = mandel(a, b);
        }
}

static void place_block(uint16_t *img, int id, const uint16_t *buf) {
    int x0, y0, bw, bh;
    block_geom(id, &x0, &y0, &bw, &bh);
    for (int j = 0; j < bh; j++)
        memcpy(&img[(size_t)(y0 + j) * W + x0], &buf[j * bw], (size_t)bw * sizeof(uint16_t));
}

/* ---------- Escritor PNG minimo (sin dependencias, deflate "stored") ---------- */
static uint32_t crc_table[256];
static void crc_init(void) {
    for (uint32_t n = 0; n < 256; n++) {
        uint32_t c = n;
        for (int k = 0; k < 8; k++) c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
        crc_table[n] = c;
    }
}
static uint32_t crc_update(uint32_t crc, const unsigned char *p, size_t n) {
    for (size_t i = 0; i < n; i++) crc = crc_table[(crc ^ p[i]) & 0xFF] ^ (crc >> 8);
    return crc;
}
static void put32(unsigned char *p, uint32_t v) {
    p[0] = v >> 24; p[1] = v >> 16; p[2] = v >> 8; p[3] = v;
}

typedef struct {
    FILE *f;
    uint32_t crc, s1, s2;
    unsigned char acc[65535];
    size_t nacc;
} PngW;

static void png_emit(PngW *w, const unsigned char *p, size_t n) {
    fwrite(p, 1, n, w->f);
    w->crc = crc_update(w->crc, p, n);
}
static void png_flush_block(PngW *w, int final) {
    unsigned char hdr[5];
    hdr[0] = final ? 1 : 0;
    hdr[1] = w->nacc & 0xFF; hdr[2] = (w->nacc >> 8) & 0xFF;
    hdr[3] = ~hdr[1]; hdr[4] = ~hdr[2];
    png_emit(w, hdr, 5);
    png_emit(w, w->acc, w->nacc);
    w->nacc = 0;
}
static void png_raw(PngW *w, const unsigned char *p, size_t n) {
    for (size_t i = 0; i < n; i++) {
        w->s1 = (w->s1 + p[i]) % 65521u;
        w->s2 = (w->s2 + w->s1) % 65521u;
        w->acc[w->nacc++] = p[i];
        if (w->nacc == 65535) png_flush_block(w, 0);
    }
}

static void color_of(uint16_t it, unsigned char *rgb) {
    if (it >= MAXIT) { rgb[0] = rgb[1] = rgb[2] = 0; return; }
    double t = (double)it / 64.0;
    rgb[0] = (unsigned char)(127.5 * (1.0 + sin(6.2831853 * (t + 0.00))));
    rgb[1] = (unsigned char)(127.5 * (1.0 + sin(6.2831853 * (t + 0.33))));
    rgb[2] = (unsigned char)(127.5 * (1.0 + sin(6.2831853 * (t + 0.67))));
}

static int write_png(const char *path, const uint16_t *img) {
    FILE *f = fopen(path, "wb");
    if (!f) return -1;
    crc_init();
    static const unsigned char sig[8] = {137, 80, 78, 71, 13, 10, 26, 10};
    fwrite(sig, 1, 8, f);
    unsigned char b4[4];
    /* IHDR */
    unsigned char ihdr[13];
    put32(ihdr, W); put32(ihdr + 4, H);
    ihdr[8] = 8; ihdr[9] = 2; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
    put32(b4, 13); fwrite(b4, 1, 4, f);
    uint32_t c = 0xFFFFFFFFu;
    c = crc_update(c, (const unsigned char *)"IHDR", 4);
    c = crc_update(c, ihdr, 13);
    fwrite("IHDR", 1, 4, f); fwrite(ihdr, 1, 13, f);
    put32(b4, c ^ 0xFFFFFFFFu); fwrite(b4, 1, 4, f);
    /* IDAT (zlib con bloques stored) */
    uint64_t rawlen = (uint64_t)H * (1 + 3 * (uint64_t)W);
    uint64_t nblk = (rawlen + 65534) / 65535; if (nblk == 0) nblk = 1;
    uint64_t idat_len = 2 + nblk * 5 + rawlen + 4;
    put32(b4, (uint32_t)idat_len); fwrite(b4, 1, 4, f);
    PngW *w = (PngW *)calloc(1, sizeof(PngW));
    w->f = f; w->crc = 0xFFFFFFFFu; w->s1 = 1; w->s2 = 0; w->nacc = 0;
    fwrite("IDAT", 1, 4, f);
    w->crc = crc_update(w->crc, (const unsigned char *)"IDAT", 4);
    unsigned char zh[2] = {0x78, 0x01};
    png_emit(w, zh, 2);
    unsigned char *row = (unsigned char *)malloc(1 + 3 * (size_t)W);
    for (int j = 0; j < H; j++) {
        row[0] = 0; /* filtro None */
        for (int i = 0; i < W; i++) color_of(img[(size_t)j * W + i], &row[1 + 3 * i]);
        png_raw(w, row, 1 + 3 * (size_t)W);
    }
    png_flush_block(w, 1);
    unsigned char ad[4];
    put32(ad, (w->s2 << 16) | w->s1);
    png_emit(w, ad, 4);
    put32(b4, w->crc ^ 0xFFFFFFFFu); fwrite(b4, 1, 4, f);
    /* IEND */
    put32(b4, 0); fwrite(b4, 1, 4, f);
    fwrite("IEND", 1, 4, f);
    put32(b4, 0xAE426082u); fwrite(b4, 1, 4, f);
    free(row); free(w); fclose(f);
    return 0;
}

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (argc < 5) {
        if (rank == 0) fprintf(stderr, "Uso: %s W H MAX_ITER BLOQUE [salida.png]\n", argv[0]);
        MPI_Finalize();
        return 1;
    }
    W = atoi(argv[1]); H = atoi(argv[2]); MAXIT = atoi(argv[3]); B = atoi(argv[4]);
    const char *out = (argc > 5) ? argv[5] : NULL;
    if (W < 2 || H < 2 || MAXIT < 1 || B < 1 || MAXIT > 65535) {
        if (rank == 0) fprintf(stderr, "Parametros invalidos\n");
        MPI_Finalize();
        return 1;
    }
    TX = (W + B - 1) / B;
    TY = (H + B - 1) / B;
    int ntasks = TX * TY;

    uint16_t *buf = (uint16_t *)malloc((size_t)B * B * sizeof(uint16_t));
    double t_calc = 0.0, t_wait = 0.0;
    int n_done = 0;

    MPI_Barrier(MPI_COMM_WORLD);
    double t0 = MPI_Wtime();

    uint16_t *img = NULL;
    if (rank == 0) {
        img = (uint16_t *)malloc((size_t)W * H * sizeof(uint16_t));
        if (!img) { fprintf(stderr, "Sin memoria para la imagen\n"); MPI_Abort(MPI_COMM_WORLD, 2); }
    }

    if (size == 1) {
        /* --- Modo secuencial: linea base --- */
        for (int id = 0; id < ntasks; id++) {
            double s = MPI_Wtime();
            compute_block(id, buf);
            t_calc += MPI_Wtime() - s;
            place_block(img, id, buf);
            n_done++;
        }
    } else if (rank == 0) {
        /* --- MAESTRO --- */
        int next = 0, active = size - 1;
        while (active > 0) {
            int rid;
            MPI_Status st;
            MPI_Recv(&rid, 1, MPI_INT, MPI_ANY_SOURCE, 1, MPI_COMM_WORLD, &st);
            int src = st.MPI_SOURCE;
            if (rid >= 0) {
                int x0, y0, bw, bh;
                block_geom(rid, &x0, &y0, &bw, &bh);
                MPI_Recv(buf, bw * bh, MPI_UINT16_T, src, 2, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                place_block(img, rid, buf);
                n_done++;
            }
            int give = (next < ntasks) ? next++ : -1;
            MPI_Send(&give, 1, MPI_INT, src, 3, MPI_COMM_WORLD);
            if (give < 0) active--;
        }
    } else {
        /* --- TRABAJADOR --- */
        int rid = -1;
        for (;;) {
            double s = MPI_Wtime();
            MPI_Send(&rid, 1, MPI_INT, 0, 1, MPI_COMM_WORLD);
            if (rid >= 0) {
                int x0, y0, bw, bh;
                block_geom(rid, &x0, &y0, &bw, &bh);
                MPI_Send(buf, bw * bh, MPI_UINT16_T, 0, 2, MPI_COMM_WORLD);
            }
            int id;
            MPI_Recv(&id, 1, MPI_INT, 0, 3, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            t_wait += MPI_Wtime() - s; /* envio + espera de la siguiente tarea */
            if (id < 0) break;
            s = MPI_Wtime();
            compute_block(id, buf);
            t_calc += MPI_Wtime() - s;
            n_done++;
            rid = id;
        }
    }

    MPI_Barrier(MPI_COMM_WORLD);
    double t_total = MPI_Wtime() - t0;

    /* Estadisticas por proceso al maestro */
    double mine[3] = {t_calc, t_wait, (double)n_done};
    double *all = NULL;
    if (rank == 0) all = (double *)malloc(3 * (size_t)size * sizeof(double));
    MPI_Gather(mine, 3, MPI_DOUBLE, all, 3, MPI_DOUBLE, 0, MPI_COMM_WORLD);

    /* Nombre de host de cada proceso (para ver el reparto por maquina) */
    char pname[MPI_MAX_PROCESSOR_NAME];
    memset(pname, 0, sizeof(pname));
    int plen = 0;
    MPI_Get_processor_name(pname, &plen);
    char *names = NULL;
    if (rank == 0) names = (char *)calloc((size_t)size, MPI_MAX_PROCESSOR_NAME);
    MPI_Gather(pname, MPI_MAX_PROCESSOR_NAME, MPI_CHAR, names, MPI_MAX_PROCESSOR_NAME, MPI_CHAR, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        int nw = (size == 1) ? 1 : size - 1;
        int first = (size == 1) ? 0 : 1;
        double sc = 0, sw = 0;
        fprintf(stderr, "# Por proceso: rank, t_calc, t_espera, tareas, host\n");
        for (int r = first; r < first + nw; r++) {
            fprintf(stderr, "#  %d, %.4f, %.4f, %d, %s\n", r, all[3 * r], all[3 * r + 1],
                    (int)all[3 * r + 2], &names[(size_t)r * MPI_MAX_PROCESSOR_NAME]);
            sc += all[3 * r];
            sw += all[3 * r + 1];
        }
        double pct = (sc + sw) > 0 ? 100.0 * sw / (sc + sw) : 0.0;
        printf("P,W,H,iter,bloque,tareas,T_total,T_calc_prom,T_espera_prom,pct_espera\n");
        printf("%d,%d,%d,%d,%d,%d,%.4f,%.4f,%.4f,%.2f\n",
               size, W, H, MAXIT, B, ntasks, t_total, sc / nw, sw / nw, pct);
        if (out) {
            if (write_png(out, img) == 0) fprintf(stderr, "# Imagen guardada: %s\n", out);
            else fprintf(stderr, "# ERROR al escribir %s\n", out);
        }
        free(all); free(img); free(names);
    }
    free(buf);
    MPI_Finalize();
    return 0;
}
