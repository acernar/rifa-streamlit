import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(layout="wide")

TITULO = "🎟️ RIFA – Selección de Números"
PRECIO_TICKET = 10
ADMIN_PASSWORD = "admin123"
HORAS_RESERVA = 24

RANGOS = [
    (121, 140),
    (1561, 1580),
    (1586, 1605),
    (1696, 1715),
    (1771, 1790),
    (2036, 2060)
]

DATA_FILE = "data/rifa.xlsx"

# =============================
# FUNCIONES UTILITARIAS
# =============================
def generar_todos_los_numeros():
    nums = []
    for a, b in RANGOS:
        nums.extend(range(a, b + 1))
    return nums


def parsear_numeros(input_texto):
    numeros = set()

    if not input_texto:
        return []

    partes = input_texto.split(",")

    for parte in partes:
        parte = parte.strip()

        if "-" in parte:
            try:
                inicio, fin = parte.split("-")
                for n in range(int(inicio), int(fin) + 1):
                    numeros.add(n)
            except:
                pass
        else:
            try:
                numeros.add(int(parte))
            except:
                pass

    return sorted(numeros)


def cargar_data():
    if not os.path.exists("data"):
        os.makedirs("data")

    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["Nombre", "Numero", "Estado", "Fecha"])
        df.to_excel(DATA_FILE, index=False)
        return df

    df = pd.read_excel(DATA_FILE)

    if "Fecha" not in df.columns:
        df["Fecha"] = datetime.now()

    return df


def guardar_data(df):
    df.to_excel(DATA_FILE, index=False)


def limpiar_reservas_vencidas(df):
    if df.empty:
        return df

    ahora = datetime.now()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    mask = (
        (df["Estado"] == "RESERVADO") &
        (df["Fecha"] < ahora - timedelta(hours=HORAS_RESERVA))
    )
    return df[~mask]


def generar_reporte_whatsapp(df):
    total_tickets = len(generar_todos_los_numeros())
    vendidos = df[df["Estado"] == "PAGADO"]
    reservados = df[df["Estado"] == "RESERVADO"]
    disponibles = total_tickets - len(df)
    total_recaudado = len(vendidos) * PRECIO_TICKET

    msg = (
        "📢 *REPORTE RIFA – PROMOCIÓN 2026*\n\n"
        f"🎟️ Total de tickets: {total_tickets}\n"
        f"✅ Pagados: {len(vendidos)}\n"
        f"⏳ Reservados: {len(reservados)}\n"
        f"🟢 Disponibles: {disponibles}\n"
        f"💰 Total recaudado: S/ {total_recaudado}\n\n"
        "📋 *Detalle por participante*\n"
    )

    for nombre, grupo in df.groupby("Nombre"):
        numeros = ", ".join(map(str, sorted(grupo["Numero"].tolist())))
        estado = grupo["Estado"].iloc[0]
        msg += (
            f"• {nombre}\n"
            f"  Rifas: {numeros}\n"
            f"  Estado: {estado}\n\n"
        )

    msg += f"📌 *Actualizado al:* {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    return msg


# =============================
# SESSION STATE
# =============================
if "seleccionados" not in st.session_state:
    st.session_state.seleccionados = set()
if "nombre" not in st.session_state:
    st.session_state.nombre = ""
if "cantidad" not in st.session_state:
    st.session_state.cantidad = 1
if "confirmado" not in st.session_state:
    st.session_state.confirmado = False


# =============================
# CARGA DE DATOS
# =============================
df = cargar_data()
df = limpiar_reservas_vencidas(df)
guardar_data(df)

ocupados = set(df["Numero"].tolist())

# =============================
# UI PRINCIPAL
# =============================
st.title(TITULO)

vendidos = len(df[df["Estado"] == "PAGADO"])
reservados = len(df[df["Estado"] == "RESERVADO"])
total_vendido = vendidos * PRECIO_TICKET

c1, c2, c3 = st.columns(3)
c1.metric("🎟️ Pagados", vendidos)
c2.metric("⏳ Reservados", reservados)
c3.metric("💰 Total vendido", f"S/ {total_vendido}")

st.markdown("---")

# =============================
# FORMULARIO PARTICIPANTE
# =============================
st.subheader("👤 Datos del participante")
st.text_input("Nombre completo", key="nombre")
st.number_input("Cantidad de tickets", 1, 20, key="cantidad")

st.info(
    f"Seleccionados: {len(st.session_state.seleccionados)} / {st.session_state.cantidad}"
)

# =============================
# BOTONES DE NÚMEROS
# =============================
def boton(num):
    if num in ocupados:
        st.button(f"🔴 {num}", disabled=True)
    elif num in st.session_state.seleccionados:
        if st.button(f"🔵 {num}"):
            st.session_state.seleccionados.remove(num)
    else:
        if len(st.session_state.seleccionados) >= st.session_state.cantidad:
            st.button(f"⚪ {num}", disabled=True)
        else:
            if st.button(f"🟢 {num}"):
                st.session_state.seleccionados.add(num)


st.subheader("📋 Selecciona tus números")
for a, b in RANGOS:
    st.markdown(f"### 🔢 Rango {a:04d} – {b:04d}")
    cols = st.columns(10)
    for i, n in enumerate(range(a, b + 1)):
        with cols[i % 10]:
            boton(n)

# =============================
# RESUMEN Y CONFIRMACIÓN
# =============================
st.markdown("---")
numeros = sorted(st.session_state.seleccionados)
monto = len(numeros) * PRECIO_TICKET

st.write(f"👤 **{st.session_state.nombre}**")
st.write(f"🎟️ **Números:** {', '.join(map(str, numeros))}")
st.write(f"💰 **Monto:** S/ {monto}")

if (
    st.session_state.nombre
    and len(numeros) == st.session_state.cantidad
    and not st.session_state.confirmado
):
    if st.button("✅ CONFIRMAR RESERVA"):
        nuevos = pd.DataFrame(
            {
                "Nombre": [st.session_state.nombre] * len(numeros),
                "Numero": numeros,
                "Estado": "RESERVADO",
                "Fecha": [datetime.now()] * len(numeros),
            }
        )
        df = pd.concat([df, nuevos], ignore_index=True)
        guardar_data(df)
        st.session_state.confirmado = True
        st.rerun()

# =============================
# PANEL ADMINISTRADOR
# =============================
st.markdown("---")
st.subheader("🔐 Panel Administrador")

pwd = st.text_input("Contraseña de administrador", type="password")

if pwd == ADMIN_PASSWORD:
    st.success("Acceso concedido")

    st.subheader("📋 Control de tickets")
    st.dataframe(df, use_container_width=True)

    st.subheader("✏️ Cambiar estado por número de ticket")

    input_numeros = st.text_input(
        "Números de ticket (comas o rangos con guion)",
        placeholder="Ej: 121,131,1561-1580",
    )

    nuevo_estado = st.selectbox("Nuevo estado", ["RESERVADO", "PAGADO"])

    if st.button("Actualizar estado"):
        lista_numeros = parsear_numeros(input_numeros)

        if not lista_numeros:
            st.warning("No se ingresaron números válidos.")
        else:
            encontrados = []
            no_encontrados = []

            for n in lista_numeros:
                idx = df.index[df["Numero"] == n].tolist()
                if idx:
                    df.loc[idx, "Estado"] = nuevo_estado
                    encontrados.append(n)
                else:
                    no_encontrados.append(n)

            guardar_data(df)

            if encontrados:
                st.success(
                    f"Estado actualizado a **{nuevo_estado}** para: {encontrados}"
                )

            if no_encontrados:
                st.info(f"No se encontraron estos números: {no_encontrados}")

            st.rerun()

    st.subheader("📱 Reporte final para WhatsApp")
    st.text_area(
        "Copiar y pegar",
        generar_reporte_whatsapp(df),
        height=300,
    )
