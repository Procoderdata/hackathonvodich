import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- BƯỚC 1: IMPORT COMPONENT CỦA CHÚNG TA ---
from orrery_component import st_orrery

# --- Cấu hình trang web ---
st.set_page_config(
    page_title="Exo-Orrery AI",
    page_icon="🪐",
    layout="wide"
)

# --- HÀM TẢI DỮ LIỆU (ĐÃ SỬA LỖI ĐƯỜNG DẪN) ---
@st.cache_data
def load_and_merge_data():
    all_dfs = []
    
    # Đọc dữ liệu từ TESS (TOI)
    try:
        # SỬA ĐƯỜNG DẪN Ở ĐÂY
        df_toi = pd.read_csv('data/TOI_2025.10.02_08.11.35.csv', comment='#', on_bad_lines='skip')
        df_toi_std = df_toi[['hostname', 'ra', 'dec', 'st_dist']].copy()
        df_toi_std.rename(columns={'hostname': 'star_name', 'st_dist': 'distance'}, inplace=True)
        df_toi_std['source'] = 'TESS'
        all_dfs.append(df_toi_std)
    except FileNotFoundError:
        st.warning("Không tìm thấy file TESS (TOI). Bỏ qua.")
    except KeyError:
        st.warning("File TESS (TOI) có cấu trúc không mong muốn. Bỏ qua.")

    # Đọc dữ liệu từ K2
    try:
        # SỬA ĐƯỜNG DẪN Ở ĐÂY
        df_k2 = pd.read_csv('data/k2pandc_2025.10.02_08.11.42.csv', comment='#', on_bad_lines='skip')
        df_k2_std = df_k2[['hostname', 'ra', 'dec', 'sy_dist']].copy()
        df_k2_std.rename(columns={'hostname': 'star_name', 'sy_dist': 'distance'}, inplace=True)
        df_k2_std['source'] = 'K2'
        all_dfs.append(df_k2_std)
    except FileNotFoundError:
        st.warning("Không tìm thấy file K2. Bỏ qua.")
    except KeyError:
        st.warning("File K2 có cấu trúc không mong muốn. Bỏ qua.")

    if not all_dfs:
        st.error("Không thể tải được bất kỳ file dữ liệu nào có thông tin khoảng cách (K2 hoặc TESS).")
        return None
        
    final_df = pd.concat(all_dfs, ignore_index=True)
    final_df.dropna(inplace=True)
    return final_df

# --- GIAO DIỆN CHÍNH CỦA ỨNG DỤNG ---
st.title("🪐 Exo-Orrery AI: The Interactive Discovery Platform")
st.write("Một công cụ AI và trực quan hóa để khám phá các thế giới ngoài Hệ Mặt Trời.")

# Tải và hợp nhất dữ liệu
merged_data = load_and_merge_data()

# --- PHẦN 1: BẢN ĐỒ NGÂN HÀ 3D ---
if merged_data is not None:
    st.header("🌌 Bản đồ Ngân hà 3D - Dữ liệu Hợp nhất từ TESS & K2")
    st.write(f"Đã tìm thấy và hợp nhất {len(merged_data)} hệ sao có đủ dữ liệu 3D.")

    ra_rad = np.radians(merged_data['ra'])
    dec_rad = np.radians(merged_data['dec'])
    dist = merged_data['distance']

    merged_data['x'] = dist * np.cos(dec_rad) * np.cos(ra_rad)
    merged_data['y'] = dist * np.cos(dec_rad) * np.sin(ra_rad)
    merged_data['z'] = dist * np.sin(dec_rad)

    fig = px.scatter_3d(
        merged_data, x='x', y='y', z='z', color='source',
        hover_name='star_name', hover_data={'distance': ':.2f'},
        template='plotly_dark', title='Phân bố 3D của các Hệ sao đã biết'
    )
    fig.update_traces(marker=dict(size=2, opacity=0.8))
    st.plotly_chart(fig, use_container_width=True)

    # --- PHẦN 2: TRIỆU HỒI COMPONENT ORRERY 3D ---
    st.header("🔭 Mô hình Hệ sao Chi tiết")
    st.write("Đây là component 3D được vẽ bằng Three.js, nhận dữ liệu trực tiếp từ Python.")

    # Dữ liệu giả để kiểm tra
    mock_system_data = {
        "star": { "name": "Sun", "radius": 1.0, "color": "yellow" },
        "planets": [
            { "name": "Earth", "radius": 0.1, "distance": 15, "color": "blue" }
        ]
    }

    # Gọi component của chúng ta
    st_orrery(key="orrery_viewer", data=mock_system_data)