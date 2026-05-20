import os
import pickle
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter

# ----------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------

EMBEDDED_DATASET = "embedded_dataset.pkl"


# ----------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ----------------------------------------------------------------------

def format_weight(value, pos=None):
    """
    Convierte valores a unidades legibles:
    950 -> 950 kg
    12500 -> 12.5 K kg
    2500000 -> 2.5 M kg
    """
    value = float(value)
    abs_val = abs(value)

    if abs_val >= 1_000_000:
        return f"{value / 1_000_000:.1f} M kg"
    elif abs_val >= 1_000:
        return f"{value / 1_000:.1f} K kg"
    else:
        return f"{value:.0f} kg"


# ----------------------------------------------------------------------
# CLASE PRINCIPAL
# ----------------------------------------------------------------------

class CargoDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Cargo Dashboard")
        self.root.geometry("1400x900")

        self.df = None

        self.create_menu()
        self.create_layout()
        self.create_buttons()

        # Cargar dataset embebido automáticamente si existe
        self.load_embedded_dataset()

    # ------------------------------------------------------------------
    # INTERFAZ
    # ------------------------------------------------------------------

    def create_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Cargar Dataset", command=self.load_dataset)
        file_menu.add_command(
            label="Guardar Dataset Interno",
            command=self.save_embedded_dataset
        )
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)

        menubar.add_cascade(label="Archivo", menu=file_menu)
        self.root.config(menu=menubar)

    def create_layout(self):
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Panel izquierdo
        self.left_panel = tk.Frame(
            self.main_frame,
            width=300,
            padx=10,
            pady=10
        )
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y)

        # Panel derecho
        self.right_panel = tk.Frame(self.main_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Información del dataset
        self.info_label = tk.Label(
            self.left_panel,
            text="No hay dataset cargado",
            justify=tk.LEFT,
            anchor="w"
        )
        self.info_label.pack(fill=tk.X, pady=(0, 20))

    def create_buttons(self):
        buttons = [
            ("Peso por Aerolínea", self.plot_by_airline),
            ("Peso por Destino", self.plot_by_destination),
            ("Peso por Mes", self.plot_by_month),
            ("Heatmap Mes x Aerolínea", self.plot_heatmap_airline_month),
            ("Heatmap Mes x Destino", self.plot_heatmap_destination_month),
        ]

        for text, command in buttons:
            btn = tk.Button(
                self.left_panel,
                text=text,
                command=command,
                width=30,
                pady=6
            )
            btn.pack(pady=4, fill=tk.X)
            
        # ------------------------------------------------------------------
    # CARGA Y PREPARACIÓN DE DATOS
    # ------------------------------------------------------------------

    def load_dataset(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar dataset",
            filetypes=[
                ("Archivos Excel", "*.xlsx *.xls"),
                ("Archivos CSV", "*.csv"),
                ("Todos los archivos", "*.*"),
            ],
        )

        if not file_path:
            return

        try:
            if file_path.lower().endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            self.prepare_dataframe(df)

            messagebox.showinfo(
                "Éxito",
                "Dataset cargado correctamente."
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar el archivo:\n\n{e}"
            )

    def prepare_dataframe(self, df):
        # Normalizar nombres de columnas
        df.columns = [str(col).strip().upper() for col in df.columns]

        # Columnas requeridas
        required = ["AG", "AER.", "FECHA", "DESTINO", "PESO VOLUMEN"]

        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(
                "Faltan las siguientes columnas requeridas:\n"
                + "\n".join(missing)
            )

        # Convertir FECHA
        df["FECHA"] = pd.to_datetime(
            df["FECHA"],
            dayfirst=True,
            errors="coerce"
        )

        # Eliminar filas con fecha inválida
        df = df.dropna(subset=["FECHA"])

        # Convertir PESO VOLUMEN a numérico
        df["PESO VOLUMEN"] = pd.to_numeric(
            df["PESO VOLUMEN"],
            errors="coerce"
        ).fillna(0)

        # Limpiar texto
        df["AER."] = df["AER."].astype(str).str.strip()
        df["DESTINO"] = df["DESTINO"].astype(str).str.strip()
        df["AG"] = df["AG"].astype(str).str.strip()

        # Crear columna MES (YYYY-MM)
        df["MES"] = df["FECHA"].dt.to_period("M").astype(str)

        # Crear columna NOMBRE_MES (ej. 2026-01 | January)
        df["NOMBRE_MES"] = (
            df["FECHA"].dt.to_period("M").astype(str)
            + " | "
            + df["FECHA"].dt.strftime("%B")
        )

        self.df = df
        self.update_info()

    def update_info(self):
        if self.df is None:
            self.info_label.config(text="No hay dataset cargado")
            return

        total_weight = self.df["PESO VOLUMEN"].sum()

        info = (
            f"Filas: {len(self.df):,}\n"
            f"Aerolíneas: {self.df['AER.'].nunique()}\n"
            f"Destinos: {self.df['DESTINO'].nunique()}\n"
            f"Meses: {self.df['MES'].nunique()}\n"
            f"Peso Total: {format_weight(total_weight)}\n\n"
            f"Rango de Fechas:\n"
            f"{self.df['FECHA'].min().date()}  →  "
            f"{self.df['FECHA'].max().date()}"
        )

        self.info_label.config(text=info)

    # ------------------------------------------------------------------
    # DATASET EMBEBIDO
    # ------------------------------------------------------------------

    def save_embedded_dataset(self):
        if self.df is None:
            messagebox.showwarning(
                "Advertencia",
                "Primero debe cargar un dataset."
            )
            return

        try:
            with open(EMBEDDED_DATASET, "wb") as f:
                pickle.dump(self.df, f)

            messagebox.showinfo(
                "Guardado",
                f"Dataset guardado en:\n{EMBEDDED_DATASET}\n\n"
                "Distribuya este archivo junto con el ejecutable."
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo guardar el dataset:\n\n{e}"
            )

    def load_embedded_dataset(self):
        if not os.path.exists(EMBEDDED_DATASET):
            return

        try:
            with open(EMBEDDED_DATASET, "rb") as f:
                self.df = pickle.load(f)

            self.update_info()

        except Exception:
            pass

    # ------------------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------------------

    def require_data(self):
        if self.df is None:
            messagebox.showwarning(
                "Advertencia",
                "Primero debe cargar un dataset."
            )
            return False
        return True

    def clear_plot(self):
        for widget in self.right_panel.winfo_children():
            widget.destroy()

    def show_figure(self, fig):
        self.clear_plot()

        canvas = FigureCanvasTkAgg(fig, master=self.right_panel)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def select_month(self):
        if not self.require_data():
            return None

        months = sorted(self.df["MES"].unique())

        selected = simpledialog.askstring(
            "Seleccionar Mes",
            "Meses disponibles:\n\n"
            + "\n".join(months)
            + "\n\nEscriba el mes exactamente como aparece (YYYY-MM):"
        )

        if selected is None:
            return None

        selected = selected.strip()

        if selected not in months:
            messagebox.showwarning(
                "Mes inválido",
                "El mes seleccionado no existe en el dataset."
            )
            return None

        return selected
    
    # ------------------------------------------------------------------
    # GRÁFICO: PESO POR AEROLÍNEA (APILADO POR DESTINO)
    # ------------------------------------------------------------------

    def plot_by_airline(self):
        if not self.require_data():
            return

        # Tabla dinámica:
        # filas = aerolíneas
        # columnas = destinos
        # valores = suma de PESO VOLUMEN
        pivot = pd.pivot_table(
            self.df,
            values="PESO VOLUMEN",
            index="AER.",
            columns="DESTINO",
            aggfunc="sum",
            fill_value=0,
            )   

        # Seleccionar top 15 aerolíneas por volumen total
        pivot["TOTAL"] = pivot.sum(axis=1)
        pivot = pivot.sort_values("TOTAL", ascending=False).head(15)
        pivot = pivot.drop(columns="TOTAL")

        # Mantener solo los 10 destinos principales para evitar
        # demasiados colores en la leyenda
        top_destinations = (
            pivot.sum(axis=0)
            .sort_values(ascending=False)
            .head(10)
            .index
            )
        pivot = pivot[top_destinations]

        # Crear gráfico
        fig, ax = plt.subplots(figsize=(14, 8))
        pivot.plot(kind="bar", stacked=True, ax=ax)

        ax.set_title(
            "Top 15 Aerolíneas por Peso Volumen "
            "(Segmentado por Destino)"
            )
        ax.set_xlabel("Aerolínea")
        ax.set_ylabel("Peso Volumen")
        ax.yaxis.set_major_formatter(FuncFormatter(format_weight))
        ax.tick_params(axis="x", rotation=45)

        # Leyenda a la derecha
        ax.legend(
            title="Destino",
            bbox_to_anchor=(1.02, 1),
            loc="upper left"
            )

        fig.tight_layout()
        self.show_figure(fig)

# ------------------------------------------------------------------
# GRÁFICO: PESO POR DESTINO (GLOBAL O POR MES)
# ------------------------------------------------------------------

    def plot_by_destination(self):
        if not self.require_data():
            return

        # Preguntar si desea filtrar por mes
        filter_by_month = messagebox.askyesno(
            "Filtro por Mes",
            "¿Desea analizar un mes específico?\n\n"
            "Sí = Seleccionar mes\n"
            "No = Mostrar datos globales"
            )

        df_plot = self.df
        title_suffix = "Global"

        if filter_by_month:
            month = self.select_month()
            if month is None:
                return

            df_plot = self.df[self.df["MES"] == month]
            title_suffix = month

        # Agrupar por destino
        data = (
            df_plot.groupby("DESTINO")["PESO VOLUMEN"]
            .sum()
            .sort_values(ascending=False)
            .head(20)
            )

        # Crear gráfico
        fig, ax = plt.subplots(figsize=(12, 7))
        data.plot(kind="bar", ax=ax)

        ax.set_title(
            f"Top 20 Destinos por Peso Volumen ({title_suffix})"
            )
        ax.set_xlabel("Destino")
        ax.set_ylabel("Peso Volumen")
        ax.yaxis.set_major_formatter(FuncFormatter(format_weight))
        ax.tick_params(axis="x", rotation=45)

        # Etiquetas sobre barras
        for container in ax.containers:
            labels = [
                format_weight(bar.get_height())
                for bar in container
                ]
            ax.bar_label(
                container,
                labels=labels,
                padding=3,
                fontsize=8
                )

        fig.tight_layout()
        self.show_figure(fig)

# ------------------------------------------------------------------
# GRÁFICO: PESO POR MES
# (Muestra cuánto embarcó cada aerolínea en un mes específico)
# ------------------------------------------------------------------

    def plot_by_month(self):
        if not self.require_data():
            return

    # Seleccionar mes
        month = self.select_month()
        if month is None:
            return

    # Filtrar datos del mes seleccionado
        df_month = self.df[self.df["MES"] == month]

    # Agrupar por aerolínea
        data = (
            df_month.groupby("AER.")["PESO VOLUMEN"]
            .sum()
            .sort_values(ascending=False)
            .head(20)
            )

    # Crear gráfico
        fig, ax = plt.subplots(figsize=(12, 7))
        data.plot(kind="bar", ax=ax)

        ax.set_title(
        f"Peso Volumen por Aerolínea - {month}"
        )
        ax.set_xlabel("Aerolínea")
        ax.set_ylabel("Peso Volumen")
        ax.yaxis.set_major_formatter(FuncFormatter(format_weight))
        ax.tick_params(axis="x", rotation=45)

    # Etiquetas sobre barras
        for container in ax.containers:
            labels = [
                format_weight(bar.get_height())
                for bar in container
                ]
            ax.bar_label(
                container,
                labels=labels,
                padding=3,
                fontsize=8
                )

        fig.tight_layout()
        self.show_figure(fig)
 
    # ------------------------------------------------------------------
    # HEATMAP: MES x AEROLÍNEA
    # ------------------------------------------------------------------

    def plot_heatmap_airline_month(self):
        if not self.require_data():
            return

        # Crear tabla dinámica
        pivot = pd.pivot_table(
            self.df,
            values="PESO VOLUMEN",
            index="AER.",
            columns="MES",
            aggfunc="sum",
            fill_value=0,
        )

        # Seleccionar top 15 aerolíneas por volumen total
        pivot["TOTAL"] = pivot.sum(axis=1)
        pivot = pivot.sort_values("TOTAL", ascending=False).head(15)
        pivot = pivot.drop(columns="TOTAL")

        # Crear figura
        fig, ax = plt.subplots(figsize=(12, 8))
        im = ax.imshow(pivot.values, aspect="auto")

        ax.set_title("Heatmap: Mes x Aerolínea")
        ax.set_xlabel("Mes")
        ax.set_ylabel("Aerolínea")

        # Etiquetas del eje X
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(
            pivot.columns,
            rotation=45,
            ha="right"
        )

        # Etiquetas del eje Y
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)

        # Barra de color
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Peso Volumen (kg)")

        fig.tight_layout()
        self.show_figure(fig)

    # ------------------------------------------------------------------
    # HEATMAP: MES x DESTINO
    # ------------------------------------------------------------------

    def plot_heatmap_destination_month(self):
        if not self.require_data():
            return

        # Crear tabla dinámica
        pivot = pd.pivot_table(
            self.df,
            values="PESO VOLUMEN",
            index="DESTINO",
            columns="MES",
            aggfunc="sum",
            fill_value=0,
        )

        # Seleccionar top 15 destinos por volumen total
        pivot["TOTAL"] = pivot.sum(axis=1)
        pivot = pivot.sort_values("TOTAL", ascending=False).head(15)
        pivot = pivot.drop(columns="TOTAL")

        # Crear figura
        fig, ax = plt.subplots(figsize=(12, 8))
        im = ax.imshow(pivot.values, aspect="auto")

        ax.set_title("Heatmap: Mes x Destino")
        ax.set_xlabel("Mes")
        ax.set_ylabel("Destino")

        # Etiquetas del eje X
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(
            pivot.columns,
            rotation=45,
            ha="right"
        )

        # Etiquetas del eje Y
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)

        # Barra de color
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Peso Volumen (kg)")

        fig.tight_layout()
        self.show_figure(fig)


# ----------------------------------------------------------------------
# PUNTO DE ENTRADA DEL PROGRAMA
# ----------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = CargoDashboard(root)
    root.mainloop()