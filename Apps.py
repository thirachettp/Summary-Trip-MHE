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

@st.cache_resource
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

@st.cache_data(ttl=300)
def load_data():

    sync_google_drive()

    files = glob.glob(
        os.path.join(DOWNLOAD_PATH, "Summary plan load daily report*.xlsx")
    )

    df_list = []

    for f in files:
        df = pd.read_excel(f, header=2)
        df_list.append(df)

    return pd.concat(df_list, ignore_index=True)


# =========================
# MAIN DATA
# =========================
st.set_page_config(
    page_title="Summary Trip MHE",
    page_icon="🚚",
    layout="wide"
)


raw = load_data()
raw_df = raw.copy()

raw_df = raw_df[['NO.', 'Trip No.', 'ID Truck', 'Store Code', 'Store  Name']]
raw_df = raw_df[raw_df['Store Code'].notna()]

raw_df['Trip No.'] = raw_df['Trip No.'].ffill()
raw_df['ID Truck'] = raw_df['ID Truck'].ffill()

raw_df['Store Code'] = (
    pd.to_numeric(raw_df['Store Code'], errors='coerce')
    .fillna(0)
    .astype(int)
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

trip_no = st.selectbox(
    "เลือก Trip No.",
    sorted(raw_df['Trip No.'].unique())
)

trip_df = raw_df[raw_df['Trip No.'] == trip_no]

st.write(f"Trip No : {trip_no}")

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

results = []

st.write(f"ID Truck : {trip_df['ID Truck'].iloc[0]}")


# =========================
# EXISTING STORES
# =========================

for idx, row in trip_df.iterrows():

    st.markdown("---")

    st.write(f"🏪 {row['Store Code']} - {row['Store  Name']}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pallet = st.number_input("Pallet", 0, key=f"p_{idx}")
    with col2:
        tote = st.number_input("Toteboxes", 0, key=f"t_{idx}")
    with col3:
        roll = st.number_input("Rollcage", 0, key=f"r_{idx}")
    with col4:
        boxes = st.number_input("Boxes", 0, key=f"b_{idx}")

    results.append({
        "Timestamp_Edited": timestamp,
        "Trip No.": trip_no,
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

    st.markdown("---")

    colA, colB, colDel = st.columns([2, 2, 1])
    
    # STORE CODE

    options = [
        f"{row['Store Code']} - {row['Store  Name']}"
        for _, row in store_map.iterrows()
    ]

    with colA:
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

    # NUMBERS
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pallet = st.number_input("Pallet", 0, key=f"ep_{i}")
    with col2:
        tote = st.number_input("Toteboxes", 0, key=f"et_{i}")
    with col3:
        roll = st.number_input("Rollcage", 0, key=f"er_{i}")
    with col4:
        boxes = st.number_input("Boxes", 0, key=f"eb_{i}")

    st.session_state.extra_stores[i].update({
        "Pallet": pallet,
        "Toteboxes": tote,
        "Rollcage": roll,
        "Boxes": boxes
    })

    # DELETE
    with colDel:
        if st.button("🗑", key=f"del_{i}"):
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

    # =========================
    # 1. existing stores (เดิม)
    # =========================
    final_results = results.copy()

    # =========================
    # 2. extra stores (ต้องเพิ่ม)
    # =========================
    for s in st.session_state.extra_stores:
        if s["Store Code"] or s["Store Name"]:
            final_results.append({
                "Timestamp_Edited": timestamp,
                "Trip No.": trip_no,
                "Store Code": s["Store Code"],
                "Store Name": s["Store Name"],
                "Pallet": s.get("Pallet", 0),
                "Toteboxes": s.get("Toteboxes", 0),
                "Rollcage": s.get("Rollcage", 0),
                "Boxes": s.get("Boxes", 0)
            })

    # =========================
    # 3. send API
    # =========================
    result_df = pd.DataFrame(final_results)

    response = requests.post(
        API_URL,
        json=result_df.to_dict(orient="records")
    )

    if response.status_code == 200:
        st.session_state.saved_success = True
        st.session_state.reset_form = True
        st.rerun()

    else:
        st.session_state.saved_success = False
        st.rerun()

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
