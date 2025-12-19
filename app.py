import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================
st.set_page_config(layout="wide")

TITULO = "🎟️ RIFA – Selección de Números"
PRECIO_TICKET = 10
ADMIN_PASSWORD = "admin123"

RANGOS = [
    (121, 140),
    (1561, 1580),
    (1586, 1605),
    (1696, 1715),
    (1771, 1790),
    (2036, 2060),
]

SHEET_ID = "1_kiS4BeYT80GfmyrHhhCyycPcNmmC1SDOAfR1K4JjT8"
SHEET_NAME = "Hoja 1"

# ======================================================
# GOOGLE SHEETS
# ======================================================
@st.cache_resource
def conectar_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)


def cargar_data():
    sheet = conectar_sheet()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["Nombre", "Numero", "Estado", "Fecha"])
    return pd.DataFrame(data)


def guardar_filas(filas):
    sheet = conectar_sheet()
    sheet.append_rows(filas, value_input_option="USER_ENTERED")


# ======================================================
# UTILIDADES
# ======================================================
def todos_los_numeros():
    nums = []
    for a, b in RANGOS:
        nums.extend(range(a, b + 1))
    return nums


# ======================================================
# SESSION STATE
# ======================================================
if "seleccionados" not in st.session_state:
    st.session_state.seleccionados = set()

if "accion_pendiente" not in st.session_state:
    st.session_state.accion_pendiente = None

if "nombre" not in st.session_state:
    st.session_state.nombre = ""

if "cantidad" not in st.session_state:
    st.session_state.cantidad = 1


# ======================================================
# CARGA DE DATOS
# ======================================================
df = cargar_data()

if not df.empty:
    df["Numero"] = df["Numero"].astype(int)

ocupados = set(df["Numero"].tolist())


# ======================================================
# UI PRINCIPAL
# ======================================================
st.title(TITULO)

pagados = len(df[df["Estado"] == "PAGADO"])
reservados = len(df[df["Estado"] == "RESERVADO"])
total_vendido = pagados * PRECIO_TICKET

c1, c2, c3 = st.columns(3)
c1.metric("🎟️ Pagados", pagados)
c2.metric("⏳ Reservados", reservados)
c3.metric("💰 Total vendido", f"S/ {total_vendido}")

st.markdown("---")

# ======================================================
# DATOS PARTICIPANTE
# ======================================================
st.subheader("👤 Datos del participante")
st.text_input("Nombre completo", key="nombre")
st.number_input("Cantidad de tickets", min_value=1, max_value=20, key="cantidad")

st.info(
    f"Seleccionados: {len(st.session_state.seleccionados)} / {st.session_state.cantidad}"
)

# ======================================================
# BOTONES DE NÚMEROS (ESTABLE)
# ======================================================
def boton(num):
    key = f"num_{num}"

    seleccionado = num in st.session_state.seleccionados
    ocupado = num in ocupados
    limite = len(st.session_state.seleccionados) >= st.session_state.cantidad

    if ocupado:
        label = f"🔴 {num}"
    elif seleccionado:
        label = f"🔵 {num}"
    elif limite:
        label = f"⚪ {num}"
    else:
        label = f"🟢 {num}"

    if st.button(label, key=key):
        if ocupado:
            return

        if seleccionado:
            st.session_state.accion_pendiente = ("remove", num)
        elif not limite:
            st.session_state.accion_pendiente = ("add", num)
        else:
            st.warning(
                f"Solo puedes seleccionar {st.session_state.cantidad} número(s).",
                icon="⚠️",
            )


st.subheader("📋 Selecciona tus números")

for a, b in RANGOS:
    st.markdown(f"### 🔢 Rango {a:04d} – {b:04d}")
    cols = st.columns(10)
    for i, n in enumerate(range(a, b + 1)):
        with cols[i % 10]:
            boton(n)


# ======================================================
# APLICAR ACCIÓN (UNA SOLA VEZ)
# ======================================================
if st.session_state.accion_pendiente:
    accion, num = st.session_state.accion_pendiente

    if accion == "add":
        st.session_state.seleccionados.add(num)
    elif accion == "remove":
        st.session_state.seleccionados.remove(num)

    st.session_state.accion_pendiente = None
    st.rerun()


# ======================================================
# RESUMEN
# ======================================================
st.markdown("---")
numeros = sorted(st.session_state.seleccionados)
monto = len(numeros) * PRECIO_TICKET

st.write(f"👤 **{st.session_state.nombre}**")
st.write(f"🎟️ **Números:** {', '.join(map(str, numeros))}")
st.write(f"💰 **Monto:** S/ {monto}")


# ======================================================
# CONFIRMAR RESERVA (ÚNICA ESCRITURA)
# ======================================================
if (
    st.session_state.nombre
    and len(numeros) == st.session_state.cantidad
):
    if st.button("✅ CONFIRMAR RESERVA"):
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filas = []

        for n in numeros:
            filas.append([
                st.session_state.nombre,
                int(n),
                "RESERVADO",
                ahora,
            ])

        guardar_filas(filas)

        st.success("Reserva registrada correctamente")

        st.session_state.seleccionados = set()
        st.rerun()


# ======================================================
# PANEL ADMIN
# ======================================================
st.markdown("---")
st.subheader("🔐 Panel Administrador")

pwd = st.text_input("Contraseña", type="password")

if pwd == ADMIN_PASSWORD:
    st.success("Acceso concedido")
    st.dataframe(df, use_container_width=True)