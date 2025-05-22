import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import chardet

# ---------- クエリと表示言語切り替え ----------
query_params = st.query_params
lang_param = query_params.get("lang") or "ja"
language_en = lang_param == "en"

st.sidebar.markdown("## 🌐 Language")
language_en = st.sidebar.toggle("Display in English", value=language_en)

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

# ---------- PLEXOSデータ読み込み ----------
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

# --- 各タブの実装（省略：Spike High, Low, Trend, Volume 同様に処理）

# --- 統計量タブ
if uploaded_file:
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

# ---------- CSVエクスポート ----------
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