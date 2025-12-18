import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(layout="wide")

TITULO = "🎟️ RIFA – Selección de Números"
PRECIO_TICKET = 10
ADMIN_PASSWORD = "admin123"
HORAS_RESERVA = 24

SHEET_NAME = "Rifa Promoción 2026"  # nombre EXACTO del archivo

RANGOS = [
    (121, 140),
    (1561, 1580),
    (1586, 1605),
    (1696, 1715),
    (1771, 1790),
    (2036, 2060),
]

# =============================
# GOOGLE SHEETS
# =============================
def conectar_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1


def cargar_data():
    sheet = conectar_sheet()
    registros = sheet.get_all_records()

    if not registros:
        return pd.DataFrame(columns=["Nombre", "Numero", "Estado", "Fecha"])

    df = pd.DataFrame(registros)

    # Normalización crítica
    df["Numero"] = pd.to_numeric(df["Numero"], errors="coerce")
    df["Estado"] = (
        df["Estado"]
        .astype(str)
        .str.strip()
        .str.upper()
    )
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    return df


def guardar_data(df):
    sheet = conectar_sheet()
    sheet.clear()
    sheet.update([df.columns.tolist()] + df.astype(str).values.tolist())


# =============================
# UTILIDADES
# =============================
def generar_todos_los_numeros():
    nums = []
    for a, b in RANGOS:
        nums.extend(range(a, b + 1))
    return nums


def parsear_numeros(texto):
    numeros = set()
    if not texto:
        return []

    for parte in texto.split(","):
        parte = parte.strip()
        if "-" in parte:
            try:
                ini, fin = parte.split("-")
                numeros.update(range(int(ini), int(fin) + 1))
            except:
                pass
        else:
            try:
                numeros.add(int(parte))
            except:
                pass
    return sorted(numeros)


def limpiar_reservas_vencidas(df):
    if df.empty:
        return df

    ahora = datetime.now()
    mask = (
        (df["Estado"] == "RESERVADO") &
        (df["Fecha"] < ahora - timedelta(hours=HORAS_RESERVA))
    )
    return df[~mask]


def generar_reporte_whatsapp(df):
    total = len(generar_todos_los_numeros())
    vendidos = df[df["Estado"] == "PAGADO"]
    reservados = df[df["Estado"] == "RESERVADO"]
    disponibles = total - len(df)
    total_recaudado = len(vendidos) * PRECIO_TICKET

    msg = (
        "📢 *REPORTE RIFA – PROMOCIÓN 2026*\n\n"
        f"🎟️ Total de tickets: {total}\n"
        f"✅ Pagados: {len(vendidos)}\n"
        f"⏳ Reservados: {len(reservados)}\n"
        f"🟢 Disponibles: {disponibles}\n"
        f"💰 Total recaudado: S/ {total_recaudado}\n\n"
        "📋 *Detalle por participante*\n\n"
    )

    for nombre, grupo in df.groupby("Nombre"):
        nums = ", ".join(map(str, sorted(grupo["Numero"].tolist())))
        estado = grupo["Estado"].iloc[0]
        msg += (
            f"• {nombre}\n"
            f"  🎟️ {nums}\n"
            f"  📌 {estado}\n\n"
        )

    msg += f"📅 *Actualizado:* {datetime.now().strftime('%d/%m/%Y %H:%M')}"
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

ocupados = set(df["Numero"].dropna().astype(int).tolist())

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
# PARTICIPANTE
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
# CONFIRMAR RESERVA
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
        nuevos = pd.DataFrame({
            "Nombre": [st.session_state.nombre] * len(numeros),
            "Numero": numeros,
            "Estado": "RESERVADO",
            "Fecha": [datetime.now()] * len(numeros),
        })
        df = pd.concat([df, nuevos], ignore_index=True)
        guardar_data(df)
        st.session_state.confirmado = True
        st.rerun()

# =============================
# PANEL ADMIN
# =============================
st.markdown("---")
st.subheader("🔐 Panel Administrador")

pwd = st.text_input("Contraseña de administrador", type="password")

if pwd == ADMIN_PASSWORD:
    st.success("Acceso concedido")

    st.subheader("📋 Control de tickets")
    st.dataframe(df, use_container_width=True)

    st.subheader("✏️ Cambiar estado por número")
    txt = st.text_input(
        "Números (comas o rangos)",
        placeholder="Ej: 121,131,1561-1580",
    )
    nuevo_estado = st.selectbox("Nuevo estado", ["RESERVADO", "PAGADO"])

    if st.button("Actualizar estado"):
        lista = parsear_numeros(txt)
        df.loc[df["Numero"].isin(lista), "Estado"] = nuevo_estado
        guardar_data(df)
        st.success(f"Actualizado: {lista}")
        st.rerun()

    st.subheader("📱 Reporte final para WhatsApp")
    st.text_area(
        "Copiar y pegar",
        generar_reporte_whatsapp(df),
        height=300,
    )