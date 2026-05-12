import streamlit as st
import pandas as pd
from datetime import datetime
import gdown
import glob
import os
import requests

# =========================
# CONFIG
# =========================

FOLDER_URL = "https://drive.google.com/drive/folders/18HOet6f4lq6KHEBc3ACXXi_OKH6zdRhp"

DOWNLOAD_PATH = "database"

# =========================
# DOWNLOAD DATABASE
# =========================

@st.cache_resource
def sync_google_drive():

    # โหลดครั้งเดียว
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    # โหลด folder
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
        os.path.join(
            DOWNLOAD_PATH,
            "Summary plan load daily report*.xlsx"
        )
    )

    latest_file = max(files, key=os.path.getmtime)

    df = pd.read_excel(
        latest_file,
        header=2
    )

    return df

# =========================
# MAIN
# =========================

raw = load_data()

raw_df = raw.copy()

raw_cols = [
    'NO.',
    'Trip No.',
    'Store Code',
    'Store  Name'
]

raw_df = raw_df[raw_cols]

# remove blank store
raw_df = raw_df[raw_df['Store Code'].notna()]

# fill merged cells
raw_df['Trip No.'] = raw_df['Trip No.'].ffill()

raw_df['Store Code'] = (
    pd.to_numeric(raw_df['Store Code'], errors='coerce')
    .fillna(0)
    .astype(int)
    .astype(str)
)

# remove duplicate stores
raw_df = raw_df.drop_duplicates()

# =========================
# UI
# =========================

st.title("Create Order")

# Trip dropdown
trip_no = st.selectbox(
    "เลือก Trip No.",
    sorted(raw_df['Trip No.'].unique())
)

# filter stores in selected trip
trip_df = raw_df[
    raw_df['Trip No.'] == trip_no
]

st.subheader(f"Stores in Trip : {trip_no}")

# =========================
# TIMESTAMP / BATCH
# =========================

timestamp = datetime.now().strftime(
    "%Y-%m-%d %H:%M:%S"
)

# =========================
# INPUT FORM
# =========================

results = []

for idx, row in trip_df.iterrows():

    st.markdown("---")

    st.write(
        f"🏪 {row['Store Code']} - {row['Store  Name']}"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        pallet = st.number_input(
            f"Pallet {row['Store Code']}",
            min_value=0,
            step=1,
            key=f"pallet_{idx}"
        )

    with col2:
        toteboxes = st.number_input(
            f"Toteboxes {row['Store Code']}",
            min_value=0,
            step=1,
            key=f"tote_{idx}"
        )

    with col3:
        rollcage = st.number_input(
            f"Rollcage {row['Store Code']}",
            min_value=0,
            step=1,
            key=f"roll_{idx}"
        )

    results.append({
        'Timestamp_Edited': timestamp,
        'Trip No.': trip_no,
        'Store Code': row['Store Code'],
        'Store Name': row['Store  Name'],
        'Pallet': pallet,
        'Toteboxes': toteboxes,
        'Rollcage': rollcage
    })

# =========================
# SAVE
# =========================

if st.button("Save"):

    # convert to dataframe
    result_df = pd.DataFrame(results)

    # dataframe -> json
    data = result_df.to_dict(orient='records')

    response = requests.post(
        "https://script.google.com/macros/s/AKfycbyx2SLLAugkd-ywNqfZa5vY9MAmITVA4Q5ByYhS7-3WPitYcq9y3mbZK_OJKzo_Q9aX/exec",
        json=data
    )

    if response.status_code == 200:
        st.success("Saved!")
    else:
        st.error("Save failed")

    st.dataframe(result_df)