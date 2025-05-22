import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import chardet

# クエリから言語設定読み取り
lang_param = st.query_params.get("lang") or "ja"
language_en = lang_param == "en"


# 🌐 トグルを最上部に明示的に置く
st.sidebar.markdown("## 🌐 Language")
language_en = st.sidebar.toggle("Display in English", value=language_en)

# 言語切り替え関数
def trans(ja: str, en: str) -> str:
    return en if language_en else ja

def trans(ja: str, en: str) -> str:
    return en if language_en else ja

# ---------- データ読み込み ----------
file_path = "SpotSummary2023Origin.csv"
with open(file_path, 'rb') as f:
    rawdata = f.read(10000)
    encoding = chardet.detect(rawdata)['encoding']
df = pd.read_csv(file_path, encoding=encoding)

df["日時"] = pd.to_datetime(df["受渡日"]) + pd.to_timedelta((df["時刻コード"] - 1) * 30, unit='m')

# ---------- サイドバー ----------
st.sidebar.header(trans("条件設定", "Settings"))
min_date = df["日時"].min().date()
max_date = df["日時"].max().date()
start_date = st.sidebar.date_input(trans("開始日", "Start date"), min_value=min_date, max_value=max_date, value=min_date)
end_date = st.sidebar.date_input(trans("終了日", "End date"), min_value=min_date, max_value=max_date, value=max_date)
high_criteria = st.sidebar.slider(trans("Spike High 閾値 (円/kWh)", "Spike High Threshold (¥/kWh)"), 0.0, 100.0, 20.0, step=0.5)
low_criteria = st.sidebar.slider(trans("Spike Low 閾値 (円/kWh)", "Spike Low Threshold (¥/kWh)"), 0.0, 10.0, 0.5, step=0.1)
agg_option = st.sidebar.selectbox(trans("集計単位", "Aggregation"), ["30分単位", "日別", "週別"] if not language_en else ["30min", "Daily", "Weekly"])

# ---------- price_columns ----------
price_columns_ja = {
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
price_columns_en = {
    "Hokkaido": "エリアプライス北海道(円/kWh)",
    "Tohoku": "エリアプライス東北(円/kWh)",
    "TEPCO": "エリアプライス東京(円/kWh)",
    "Chubu": "エリアプライス中部(円/kWh)",
    "Hokuriku": "エリアプライス北陸(円/kWh)",
    "Kansai": "エリアプライス関西(円/kWh)",
    "Chugoku": "エリアプライス中国(円/kWh)",
    "Shikoku": "エリアプライス四国(円/kWh)",
    "Kyushu": "エリアプライス九州(円/kWh)",
    "System": "システムプライス(円/kWh)"
}
price_columns = price_columns_en if language_en else price_columns_ja

selected_areas = st.sidebar.multiselect(trans("表示するエリア", "Select Areas"), list(price_columns.keys()), default=list(price_columns.keys()))

# ---------- フィルタ ----------
df_filtered = df[(df["日時"] >= pd.to_datetime(start_date)) & (df["日時"] <= pd.to_datetime(end_date))]
df_filtered = df_filtered.set_index("日時")
numeric_cols = df_filtered.select_dtypes(include='number').columns

if agg_option in ["日別", "Daily"]:
    df_filtered = df_filtered[numeric_cols].resample("D").mean().reset_index()
elif agg_option in ["週別", "Weekly"]:
    df_filtered = df_filtered[numeric_cols].resample("W-MON").mean().reset_index()
else:
    df_filtered = df_filtered.reset_index()

# ---------- PLEXOS CSV ----------
plexos_column_mapping = {
    "Chubu": "エリアプライス中部(円/kWh)",
    "Chugoku": "エリアプライス中国(円/kWh)",
    "Hokkaido": "エリアプライス北海道(円/kWh)",
    "Hokuriku": "エリアプライス北陸(円/kWh)",
    "Kansai": "エリアプライス関西(円/kWh)",
    "Kyushu": "エリアプライス九州(円/kWh)",
    "Okinawa": "Okinawa",
    "Shikoku": "エリアプライス四国(円/kWh)",
    "TEPCO": "エリアプライス東京(円/kWh)",
    "Tohoku": "エリアプライス東北(円/kWh)"
}

st.sidebar.markdown("---")
st.sidebar.subheader(trans("PLEXOSデータの比較", "Compare with PLEXOS"))
uploaded_file = st.sidebar.file_uploader(trans("PLEXOS出力CSVをアップロード", "Upload PLEXOS CSV"), type="csv")
plexos_df = None

if uploaded_file:
    raw = uploaded_file.read()
    encoding = chardet.detect(raw)['encoding']
    uploaded_file.seek(0)
    plexos_df = pd.read_csv(uploaded_file, encoding=encoding)
    plexos_df["Datetime"] = pd.to_datetime(plexos_df["Datetime"], errors="coerce")
    plexos_df.rename(columns=plexos_column_mapping, inplace=True)
    for col in plexos_column_mapping.values():
        if col in plexos_df.columns:
            plexos_df[col] = (
                plexos_df[col].astype(str)
                .str.replace(",", "", regex=False)
                .astype(float) / 1000
            )
    plexos_df["日時"] = df_filtered["日時"].reset_index(drop=True)

# ---------- タブ ----------
tab_labels = [
    trans("📈 Spike High", "📈 Spike High"),
    trans("📉 Spike Low", "📉 Spike Low"),
    trans("📊 トレンド", "📊 Trend"),
    trans("💹 売買・約定量", "💹 Bid/Contract Volume")
]
if uploaded_file:
    tab_labels += [trans("🔁 PLEXOSとJEPXの比較", "🔁 PLEXOS vs JEPX"),
                   trans("🔍 地域別価格差", "🔍 Price Difference"),
                   trans("📊 統計量", "📊 Statistics")]
tabs = st.tabs(tab_labels)

selected_price_cols = [price_columns[area] for area in selected_areas if area in price_columns]

# --- 各グラフ ---
selected_price_cols = [price_columns[area] for area in selected_areas if area in price_columns]

# Spike High
with tabs[0]:
    st.header("Spike High")
    for col in selected_price_cols:
        df_high = df_filtered[df_filtered[col] >= high_criteria]
        if not df_high.empty:
            fig = px.scatter(df_high, x="日時", y=col, title=col)
            st.plotly_chart(fig, use_container_width=True)

# Spike Low
with tabs[1]:
    st.header("Spike Low")
    for col in selected_price_cols:
        df_low = df_filtered[df_filtered[col] <= low_criteria]
        if not df_low.empty:
            fig = px.scatter(df_low, x="日時", y=col, title=col)
            st.plotly_chart(fig, use_container_width=True)

# Trend
with tabs[2]:
    st.header(trans("トレンド", "Trend"))
    fig = go.Figure()
    for col in selected_price_cols:
        fig.add_trace(go.Scatter(x=df_filtered["日時"], y=df_filtered[col], mode='lines', name=col,
                                 hovertemplate=f"%{{x}}<br>%{{y}} {trans('円/kWh','¥/kWh')}"))
    fig.update_layout(title=trans("エリア別価格トレンド", "Area Price Trend"),
                      xaxis_title=trans("日時", "Datetime"),
                      yaxis_title=trans("価格 (円/kWh)", "Price (¥/kWh)"))
    st.plotly_chart(fig, use_container_width=True)

# Volume
with tabs[3]:
    st.header(trans("売買・約定量トレンド", "Bid/Contract Volume"))
    fig = go.Figure()
    for name in ["売り入札量(kWh)", "買い入札量(kWh)", "約定総量(kWh)"]:
        if name in df_filtered.columns:
            fig.add_trace(go.Scatter(x=df_filtered["日時"], y=df_filtered[name], mode='lines', name=name))
    fig.update_layout(xaxis_title=trans("日時", "Datetime"), yaxis_title=trans("電力量 (kWh)", "Energy (kWh)"))
    st.plotly_chart(fig, use_container_width=True)

# PLEXOS vs JEPX
if uploaded_file:
    with tabs[4]:
        st.header("PLEXOS vs JEPX")
        for area in selected_areas:
            col = price_columns.get(area)
            if col and col in plexos_df.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_filtered["日時"], y=df_filtered[col], name=f"JEPX - {area}"))
                fig.add_trace(go.Scatter(x=plexos_df["日時"], y=plexos_df[col], name=f"PLEXOS - {area}"))
                fig.update_layout(title=f"{area} {trans('の価格比較', 'Price Comparison')}")
                st.plotly_chart(fig, use_container_width=True)

    with tabs[5]:
        st.header(trans("PLEXOS - JEPX 差分トレンド", "PLEXOS - JEPX Price Difference"))
        for area in selected_areas:
            col = price_columns.get(area)
            if col and col in plexos_df.columns:
                diff = plexos_df[col] - df_filtered[col]
                diff_df = pd.DataFrame({"日時": df_filtered["日時"], "価格差": diff})
                fig = px.line(diff_df, x="日時", y="価格差", title=f"{area} {trans('の価格差', 'Price Diff')}")
                fig.update_layout(xaxis_title=trans("日時", "Datetime"), yaxis_title=trans("価格差 (円/kWh)", "Diff (¥/kWh)"))
                st.plotly_chart(fig, use_container_width=True)
    with tabs[6]:
        st.header(trans("価格差の統計量とヒストグラム", "Price Difference Statistics & Histogram"))
        for area in selected_areas:
            col = price_columns.get(area)
            if col and col in plexos_df.columns:
                diff = df_filtered[col] - plexos_df[col]  # JEPX - PLEXOS
                stats = {
                    trans("最大値", "Max"): diff.max(),
                    trans("最小値", "Min"): diff.min(),
                    trans("平均値", "Mean"): diff.mean(),
                    trans("標準偏差", "Std"): diff.std()
                }
                stat_df = pd.DataFrame.from_dict(stats, orient="index", columns=[f"{area}"])
                st.subheader(f"{area}")
                st.dataframe(stat_df)

                # ヒストグラム
                fig = px.histogram(diff, nbins=30, title=f"{area} {trans('の価格差ヒストグラム', 'Price Difference Histogram')}")
                fig.update_layout(xaxis_title=trans("価格差 (円/kWh)", "Price Diff (¥/kWh)"),
                                  yaxis_title=trans("頻度", "Frequency"))
                st.plotly_chart(fig, use_container_width=True)

# ---------- エクスポート ----------
st.sidebar.markdown("---")
st.sidebar.subheader(trans("データのエクスポート", "Data Export"))

@st.cache_data
def convert_df_to_csv(df):
    rename_dict = {v: k for k, v in (price_columns_en if language_en else price_columns_ja).items()}
    return df.rename(columns=rename_dict).to_csv(index=False).encode('utf-8-sig')

csv = convert_df_to_csv(df_filtered)
st.sidebar.download_button(label=trans("📥 フィルタ済みデータをCSVでダウンロード", "📥 Download Filtered CSV"),
                           data=csv,
                           file_name="filtered_data.csv",
                           mime='text/csv')