import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import chardet

# ---------- データ読み込み ----------
file_path = "SpotSummary2023Origin.csv"
with open(file_path, 'rb') as f:
    rawdata = f.read(10000)
    encoding = chardet.detect(rawdata)['encoding']
df = pd.read_csv(file_path, encoding=encoding)

# 日時列作成
df["日時"] = pd.to_datetime(df["受渡日"]) + pd.to_timedelta((df["時刻コード"] - 1) * 30, unit='m')

# ---------- UI: サイドバー ----------
st.sidebar.header("条件設定")
min_date = df["日時"].min().date()
max_date = df["日時"].max().date()

start_date = st.sidebar.date_input("開始日", min_value=min_date, max_value=max_date, value=min_date)
end_date = st.sidebar.date_input("終了日", min_value=min_date, max_value=max_date, value=max_date)

high_criteria = st.sidebar.slider("Spike High 閾値 (円/kWh)", 0.0, 100.0, 20.0, step=0.5)
low_criteria = st.sidebar.slider("Spike Low 閾値 (円/kWh)", 0.0, 10.0, 0.5, step=0.1)
agg_option = st.sidebar.selectbox("集計単位", ["30分単位", "日別", "週別"])

# ---------- 対象エリア ----------
price_columns = {
    "北海道": "エリアプライス北海道(円/kWh)",
    "東北": "エリアプライス東北(円/kWh)",
    "東京": "エリアプライス東京(円/kWh)",
    "中部": "エリアプライス中部(円/kWh)",
    "北陸": "エリアプライス北陸(円/kWh)",
    "関西": "エリアプライス関西(円/kWh)",
    "中国": "エリアプライス中国(円/kWh)",
    "四国": "エリアプライス四国(円/kWh)",
    "九州": "エリアプライス九州(円/kWh)",
    "システム": "システムプライス(円/kWh)"
}
selected_areas = st.sidebar.multiselect("表示するエリア", list(price_columns.keys()), default=list(price_columns.keys()))

# ---------- フィルタと集計 ----------
df_filtered = df[(df["日時"] >= pd.to_datetime(start_date)) & (df["日時"] <= pd.to_datetime(end_date))]
df_filtered = df_filtered.set_index("日時")
numeric_cols = df_filtered.select_dtypes(include='number').columns

if agg_option == "日別":
    df_filtered = df_filtered[numeric_cols].resample("D").mean().reset_index()
elif agg_option == "週別":
    df_filtered = df_filtered[numeric_cols].resample("W-MON").mean().reset_index()
else:
    df_filtered = df_filtered.reset_index()

# ---------- PLEXOSデータアップロード ----------
st.sidebar.markdown("---")
st.sidebar.subheader("PLEXOSデータの比較")
uploaded_file = st.sidebar.file_uploader("PLEXOS出力CSVをアップロード", type="csv")
plexos_df = None

if uploaded_file:
    raw = uploaded_file.read()
    encoding = chardet.detect(raw)['encoding']
    uploaded_file.seek(0)
    plexos_df = pd.read_csv(uploaded_file, encoding=encoding)

    # 日時整形と価格列変換（¥/MWh → ¥/kWh）
    plexos_df["Datetime"] = pd.to_datetime(plexos_df["Datetime"], errors="coerce")
    for col in plexos_df.columns:
        if "エリアプライス" in col or col == "Okinawa":
            plexos_df[col] = (
                plexos_df[col].astype(str)
                .str.replace(",", "", regex=False)
                .astype(float) / 1000
            )

    # PLEXOSにも"日時"列を合わせる（強制整合）
    plexos_df["日時"] = df_filtered["日時"].reset_index(drop=True)

# ---------- グラフタブ ----------
tabs = st.tabs(["📈 Spike High", "📉 Spike Low", "📊 トレンド", "💹 売買・約定量"])
if plexos_df is not None:
    tabs += st.tabs(["🔁 PLEXOS vs JEPX", "🔍 差分トレンド"])

selected_price_cols = [price_columns[area] for area in selected_areas if area in price_columns]

# --- Spike High
with tabs[0]:
    st.header("Spike High")
    for col in selected_price_cols:
        df_high = df_filtered[df_filtered[col] >= high_criteria]
        if not df_high.empty:
            fig = px.scatter(df_high, x="日時", y=col, title=col)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"{col} に該当データがありません。")

# --- Spike Low
with tabs[1]:
    st.header("Spike Low")
    for col in selected_price_cols:
        df_low = df_filtered[df_filtered[col] <= low_criteria]
        if not df_low.empty:
            fig = px.scatter(df_low, x="日時", y=col, title=col)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"{col} に該当データがありません。")

# --- Trend
with tabs[2]:
    st.header("年間トレンド")
    fig = go.Figure()
    for col in selected_price_cols:
        fig.add_trace(go.Scatter(x=df_filtered["日時"], y=df_filtered[col], mode='lines', name=col))
    fig.update_layout(title="エリア別価格のトレンド", xaxis_title="日時", yaxis_title="価格 (円/kWh)")
    st.plotly_chart(fig, use_container_width=True)

# --- Volume
with tabs[3]:
    st.header("売り・買い・約定量トレンド")
    fig = go.Figure()
    for name in ["売り入札量(kWh)", "買い入札量(kWh)", "約定総量(kWh)"]:
        if name in df_filtered.columns:
            fig.add_trace(go.Scatter(x=df_filtered["日時"], y=df_filtered[name], mode='lines', name=name))
    fig.update_layout(title="売買・約定量", xaxis_title="日時", yaxis_title="電力量 (kWh)")
    st.plotly_chart(fig, use_container_width=True)

# --- PLEXOS vs JEPX
if plexos_df is not None:
    with tabs[4]:
        st.header("PLEXOS vs JEPX 各地域トレンド比較")
        for area in selected_areas:
            col = price_columns.get(area)
            if col and col in plexos_df.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_filtered["日時"], y=df_filtered[col], name=f"JEPX - {area}"))
                fig.add_trace(go.Scatter(x=plexos_df["日時"], y=plexos_df[col], name=f"PLEXOS - {area}"))
                fig.update_layout(title=f"{area} の価格比較", xaxis_title="日時", yaxis_title="価格 (円/kWh)")
                st.plotly_chart(fig, use_container_width=True)

# --- 差分
    with tabs[5]:
        st.header("PLEXOS - JEPX 差分トレンド")
        for area in selected_areas:
            col = price_columns.get(area)
            if col and col in plexos_df.columns:
                diff = plexos_df[col] - df_filtered[col]
                fig = px.line(x=df_filtered["日時"], y=diff, title=f"{area} の価格差")
                fig.update_layout(xaxis_title="日時", yaxis_title="価格差 (円/kWh)")
                st.plotly_chart(fig, use_container_width=True)

# ---------- エクスポート ----------
st.sidebar.markdown("---")
st.sidebar.subheader("データのエクスポート")

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

csv = convert_df_to_csv(df_filtered)
st.sidebar.download_button("📥 フィルタ済みデータをCSVでダウンロード", data=csv, file_name="filtered_data.csv", mime='text/csv')
