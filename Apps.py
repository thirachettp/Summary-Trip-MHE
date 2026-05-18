import streamlit as st
import pandas as pd
from datetime import datetime
import gdown
import glob
import os
import requests

# =========================
# SESSION STATE INIT (ต้องอยู่บนสุด)
# =========================

if "extra_stores" not in st.session_state:
    st.session_state.extra_stores = []

if "reset_form" not in st.session_state:
    st.session_state.reset_form = False

if "saved_success" not in st.session_state:
    st.session_state.saved_success = None

# =========================
# CONFIG
# =========================

FOLDER_URL = "https://drive.google.com/drive/folders/18HOet6f4lq6KHEBc3ACXXi_OKH6zdRhp"
DOWNLOAD_PATH = "database"
API_URL = "https://script.google.com/macros/s/AKfycbyx2SLLAugkd-ywNqfZa5vY9MAmITVA4Q5ByYhS7-3WPitYcq9y3mbZK_OJKzo_Q9aX/exec"

# =========================
# RESET HANDLER (สำคัญมาก)
# =========================

if st.session_state.reset_form:

    st.session_state.extra_stores = []

    for key in list(st.session_state.keys()):
        if key.startswith(("code_", "name_", "ep_", "et_", "er_", "eb_")):
            del st.session_state[key]

    st.session_state.reset_form = False


# =========================
# DOWNLOAD DATABASE
# =========================

@st.cache_resource(ttl=3600)
def sync_google_drive():

    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    gdown.download_folder(
        url=FOLDER_URL,
        output=DOWNLOAD_PATH,
        quiet=True,
        use_cookies=False
    )


# =========================
# LOAD DATA
# =========================

@st.cache_data(ttl=86400)
def load_data():

    sync_google_drive()

    files = glob.glob(
        os.path.join(
            DOWNLOAD_PATH,
            "Summary plan load daily report*.xlsx"
        )
    )

    # =========================
    # SORT NEWEST FILES
    # =========================

    files = sorted(
        files,
        key=os.path.getmtime,
        reverse=True
    )[:10]

    df_list = []

    for f in files:

        try:

            df = pd.read_excel(
                f,
                header=2
            )

            df['Source_File'] = os.path.basename(f)

            df_list.append(df)

            print(f"Loaded: {f}")

        except Exception as e:

            print(f"ERROR: {f}")
            print(e)

    if not df_list:
        return pd.DataFrame()

    return pd.concat(
        df_list,
        ignore_index=True
    )
# =========================
# LOAD CSS
# =========================
def load_css():
    with open("style.css") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True
        )

load_css()
# =========================
# MAIN DATA
# =========================
st.set_page_config(
    page_title="Summary Trip",
    page_icon="🚚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

raw = load_data()
raw_df = raw.copy()

raw_df = raw_df[['NO.', 'Trip No.', 'ID Truck', 'Store Code', 'Store  Name','Trip No..1','Pallet','Rollcage','Boxes','Source_File']]
raw_df = raw_df[raw_df['Store Code'].notna()]

raw_df['Trip No.'] = raw_df['Trip No.'].ffill()
raw_df['ID Truck'] = raw_df['ID Truck'].ffill()

raw_df['Store Code'] = (
    pd.to_numeric(raw_df['Store Code'], errors='coerce')
    .fillna(0)
    .astype(int)
    .astype(str)
)

raw_df['Trip No..1'] = (
    raw_df['Trip No..1']
    .ffill()
    .astype(str)
)

raw_df = raw_df.drop_duplicates()

# =========================
# LOOKUP MAP
# =========================

code_to_name = dict(zip(raw_df['Store Code'], raw_df['Store  Name']))
name_to_code = dict(zip(raw_df['Store  Name'], raw_df['Store Code']))

# =========================
# UI
# =========================

st.title("Summary Trip MHE")

trip_options = [""] + sorted(set(raw_df['Trip No..1'].dropna().astype(str)))

document_no = st.selectbox(
    "Document No.",
    options=trip_options,
    index=None,
    placeholder="เลือกหรือพิมพ์เลข",
    accept_new_options=True,
    key="trip_select"
)

results = []

results = []

if document_no != "":

    # =========================
    # HEADER INPUT
    # =========================

    c1, c2 = st.columns(2)

    with c1:
        staff_list = ["Aof", "Bank", "Boss", "Nina"]

        user = st.selectbox(
            "ชื่อผู้กรอก",
            options=staff_list,
            placeholder="เลือกหรือพิมพ์ชื่อ",
            accept_new_options=True,
            key="user_select"
        )

    with c2:
        door_no = int(
            st.number_input(
                "Door No.",
                min_value=1,
                step=1,
                key="door_input"
            )
        )

    # =========================
    # REMARK
    # =========================

    # remark = st.text_area(
    #     "Remark",
    #     placeholder="กรอกรายละเอียดเพิ่มเติม...",
    #     height=80,
    #     key="remark_input"
    # )

    # =========================
    # FILTER DATA
    # =========================

    trip_df = raw_df[
        (raw_df['Trip No..1'] == document_no) |
        (raw_df['Trip No.'] == document_no)
    ]

    if not trip_df.empty:

        st.markdown(f"""
        <div class="metric-row">

        <!-- LEFT CARD -->
        <div class="metric-card">

        <div class="inline-row">

        <div class="inline-item">
        <div class="metric-label">Trip No.</div>

        <div class="metric-value">
        {trip_df['Trip No.'].iloc[0]}
        </div>
        </div>

        <div class="inline-item">
        <div class="metric-label">Load No.</div>

        <div class="metric-value">
        {trip_df['Trip No..1'].iloc[0]}
        </div>
        </div>

        </div>

        </div>

        <!-- RIGHT CARD -->
        <div class="metric-card">

        <div class="metric-label">Truck Id.</div>

        <div class="metric-value">
        {trip_df['ID Truck'].iloc[0]}
        </div>

        </div>

        </div>
        """, unsafe_allow_html=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =========================
# EXISTING STORES
# =========================

for idx, row in trip_df.iterrows():

    with st.expander(
        f"🏪 {row['Store Code']} - {row['Store  Name']}",
        expanded=True
    ):

        c1, c2 = st.columns(2)

        with c1:
            pallet = st.number_input(
                "Pallet",
                0,
                key=f"p_{idx}"
            )

            tote = st.number_input(
                "Tote",
                0,
                key=f"t_{idx}"
            )

        with c2:
            roll = st.number_input(
                "Roll",
                0,
                key=f"r_{idx}"
            )

            boxes = st.number_input(
                "Box",
                0,
                key=f"b_{idx}"
            )

        # =========================
        # REMARK
        # =========================

        remark = st.text_area(
            "Remark",
            placeholder="กรอกรายละเอียดเพิ่มเติม...",
            height=80,
            key=f"remark_{idx}"
        )

    results.append({
        "Timestamp_Edited": timestamp,
        "Document No.": document_no,
        "Door No.": door_no,
        "User": user,
        "Remark": remark,
        "Store Code": row["Store Code"],
        "Store Name": row["Store  Name"],
        "Pallet": pallet,
        "Toteboxes": tote,
        "Rollcage": roll,
        "Boxes": boxes
    })
# =========================
# EXTRA STORES
# =========================

store_map = raw_df[['Store Code', 'Store  Name']].drop_duplicates()

for i, store in enumerate(st.session_state.extra_stores):

    options = [
        f"{row['Store Code']} - {row['Store  Name']}"
        for _, row in store_map.iterrows()
    ]

    with st.expander(
        f"🏪 Extra Stores",
        expanded=True
    ):

        selected = st.selectbox(
            "Select Store",
            options=[""] + options,
            key=f"store_{i}"
        )

        if selected:
            code, name = selected.split(" - ", 1)
        else:
            code, name = "", ""

        st.session_state.extra_stores[i]["Store Code"] = code
        st.session_state.extra_stores[i]["Store Name"] = name

        # =========================
        # INPUTS
        # =========================

        c1, c2 = st.columns(2)

        with c1:
            pallet = st.number_input(
                "Pallet",
                0,
                key=f"ep_{i}"
            )

        with c2:
            roll = st.number_input(
                "Roll",
                0,
                key=f"er_{i}"
            )

        c3, c4 = st.columns(2)

        with c3:
            tote = st.number_input(
                "Tote",
                0,
                key=f"et_{i}"
            )

        with c4:
            boxes = st.number_input(
                "Box",
                0,
                key=f"eb_{i}"
            )

        # =========================
        # REMARK
        # =========================

        remark = st.text_area(
            "Remark",
            placeholder="กรอกรายละเอียดเพิ่มเติม...",
            height=80,
            key=f"erm_{i}"
        )

        # =========================
        # UPDATE SESSION
        # =========================

        st.session_state.extra_stores[i].update({
            "Pallet": pallet,
            "Toteboxes": tote,
            "Rollcage": roll,
            "Boxes": boxes,
            "Remark": remark
        })

        st.markdown("")

        # =========================
        # DELETE
        # =========================

        if st.button(
            "🗑 Delete Store",
            key=f"del_{i}"
        ):
            st.session_state.extra_stores.pop(i)
            st.rerun()


# =========================
# ADD STORE
# =========================

if st.button("➕ Add Store"):
    st.session_state.extra_stores.append({
        "Store Code": "",
        "Store Name": "",
        "Pallet": 0,
        "Toteboxes": 0,
        "Rollcage": 0,
        "Boxes": 0
    })
    st.rerun()

# =========================
# SAVE
# =========================

if st.button("✅ Save"):

    final_results = []

    # =========================
    # 1. EXISTING STORES
    # =========================

    for r in results:

        has_qty = (
            r["Pallet"] > 0 or
            r["Toteboxes"] > 0 or
            r["Rollcage"] > 0 or
            r["Boxes"] > 0
        )

        has_remark = str(r.get("Remark", "")).strip() != ""

        if has_qty or has_remark:
            final_results.append(r)

    # =========================
    # 2. EXTRA STORES
    # =========================

    for s in st.session_state.extra_stores:

        has_qty = (
            s.get("Pallet", 0) > 0 or
            s.get("Toteboxes", 0) > 0 or
            s.get("Rollcage", 0) > 0 or
            s.get("Boxes", 0) > 0
        )

        has_remark = str(
            s.get("Remark", "")
        ).strip() != ""

        has_store = (
            s["Store Code"] or
            s["Store Name"]
        )

        if has_store and (has_qty or has_remark):

            final_results.append({
                "Timestamp_Edited": timestamp,
                "Document No.": document_no,
                "Door No.": door_no,
                "User": user,
                "Store Code": s["Store Code"],
                "Store Name": s["Store Name"],
                "Pallet": s.get("Pallet", 0),
                "Toteboxes": s.get("Toteboxes", 0),
                "Rollcage": s.get("Rollcage", 0),
                "Boxes": s.get("Boxes", 0),
                "Remark": s.get("Remark", "")
            })

    # =========================
    # NO DATA
    # =========================

    if len(final_results) == 0:
        st.warning("ไม่มีข้อมูลสำหรับบันทึก")
        st.stop()

    # =========================
    # SEND API
    # =========================

    result_df = pd.DataFrame(final_results)

    response = requests.post(
        API_URL,
        json=result_df.to_dict(orient="records")
    )

    if response.status_code == 200:

        st.session_state.saved_success = True
        st.session_state.reset_form = True

        if "trip_select" in st.session_state:
            del st.session_state["trip_select"]

        st.rerun()

    else:

        st.session_state.saved_success = False
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
# =========================
# MESSAGE
# =========================

if st.session_state.get("saved_success") is True:
    st.success("Saved!")
    st.toast("Saved & Reset ✔️")
    st.session_state.saved_success = None

elif st.session_state.get("saved_success") is False:
    st.error("Save failed")
    st.session_state.saved_success = None

print(f'Total : {len(raw['Source_File'].unique())} \n {raw['Source_File'].unique()}')
