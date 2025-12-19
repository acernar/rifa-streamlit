import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(layout="wide")

TITULO = "🎟️ RIFA – Selección de Números"
PRECIO_TICKET = 10
ADMIN_PASSWORD = "admin123"

# Zona horaria Perú (GMT-5)
TZ_PERU = timezone(timedelta(hours=-5))

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

# =============================
# GOOGLE SHEETS
# =============================
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


def append_filas(filas):
    sheet = conectar_sheet()
    sheet.append_rows(filas, value_input_option="USER_ENTERED")


def actualizar_estado(numeros, nuevo_estado):
    sheet = conectar_sheet()
    data = sheet.get_all_values()

    if len(data) <= 1:
        return 0

    header = data[0]
    filas = data[1:]
    cambios = 0

    for i, fila in enumerate(filas, start=2):
        try:
            numero = int(fila[1])
        except:
            continue

        if numero in numeros:
            sheet.update(f"C{i}", nuevo_estado)
            cambios += 1

    return cambios

# =============================
# UTILIDADES
# =============================
def todos_los_numeros():
    nums = []
    for a, b in RANGOS:
        nums.extend(range(a, b + 1))
    return nums


def parsear_numeros(texto):
    resultado = set()
    if not texto:
        return []

    for parte in texto.split(","):
        parte = parte.strip()
        if "-" in parte:
            try:
                a, b = map(int, parte.split("-"))
                resultado.update(range(a, b + 1))
            except:
                pass
        else:
            try:
                resultado.add(int(parte))
            except:
                pass

    return sorted(resultado)

# =============================
# SESSION STATE
# =============================
if "seleccionados" not in st.session_state:
    st.session_state.seleccionados = set()

if "nombre" not in st.session_state:
    st.session_state.nombre = ""

if "cantidad" not in st.session_state:
    st.session_state.cantidad = 1

# =============================
# CARGA DATOS
# =============================
df = cargar_data()
ocupados = set(df["Numero"].astype(int).tolist())

# =============================
# UI PRINCIPAL
# =============================
st.title(TITULO)

pagados = len(df[df["Estado"] == "PAGADO"])
reservados = len(df[df["Estado"] == "RESERVADO"])
total_vendido = pagados * PRECIO_TICKET

c1, c2, c3 = st.columns(3)
c1.metric("🎟️ Pagados", pagados)
c2.metric("⏳ Reservados", reservados)
c3.metric("💰 Total vendido", f"S/ {total_vendido}")

st.markdown("---")

# =============================
# PARTICIPANTE
# =============================
st.subheader("👤 Datos del participante")
st.text_input("Nombre completo", key="nombre")
st.number_input("Cantidad de tickets", 1, 20, key="cantidad")

st.info(
    f"Seleccionados: {len(st.session_state.seleccionados)} / {st.session_state.cantidad}"
)

# =============================
# BOTONES
# =============================
def boton(num):
    if num in ocupados:
        st.button(f"🔴 {num}", disabled=True)
        return

    if num in st.session_state.seleccionados:
        if st.button(f"🔵 {num}"):
            st.session_state.seleccionados.remove(num)
        return

    if len(st.session_state.seleccionados) >= st.session_state.cantidad:
        st.button(f"⚪ {num}", disabled=True)
        return

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
# RESUMEN
# =============================
st.markdown("---")
numeros = sorted(st.session_state.seleccionados)
monto = len(numeros) * PRECIO_TICKET

st.write(f"👤 **{st.session_state.nombre}**")
st.write(f"🎟️ **Números:** {', '.join(map(str, numeros))}")
st.write(f"💰 **Monto:** S/ {monto}")

# =============================
# CONFIRMAR
# =============================
if st.session_state.nombre and len(numeros) == st.session_state.cantidad:
    if st.button("✅ CONFIRMAR"):
        ahora = datetime.now(TZ_PERU).strftime("%Y-%m-%d %H:%M:%S")
        filas = []

        for n in numeros:
            filas.append([
                st.session_state.nombre,
                int(n),
                "RESERVADO",
                ahora,
            ])

        append_filas(filas)

        st.session_state.seleccionados = set()
        st.success("Reserva registrada correctamente")
        st.rerun()

# =============================
# PANEL ADMIN
# =============================
st.markdown("---")
st.subheader("🔐 Panel Administrador")

pwd = st.text_input("Contraseña", type="password")

if pwd == ADMIN_PASSWORD:
    st.success("Acceso concedido")

    st.dataframe(df, use_container_width=True)

    st.subheader("✏️ Cambiar estado por número")

    txt_nums = st.text_input(
        "Números (ej: 1577,1579,1600-1605)"
    )

    nuevo_estado = st.selectbox(
        "Nuevo estado",
        ["RESERVADO", "PAGADO"]
    )

    if st.button("Actualizar estado"):
        lista = parsear_numeros(txt_nums)
        if not lista:
            st.warning("No ingresaste números válidos")
        else:
            cambios = actualizar_estado(lista, nuevo_estado)
            st.success(f"{cambios} tickets actualizados")
            st.rerun()