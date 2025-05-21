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
    "システム": "システムプライス(円/kWh)",
    "北海道": "エリアプライス北海道(円/kWh)",
    "東北": "エリアプライス東北(円/kWh)",
    "東京": "エリアプライス東京(円/kWh)",
    "中部": "エリアプライス中部(円/kWh)",
    "北陸": "エリアプライス北陸(円/kWh)",
    "関西": "エリアプライス関西(円/kWh)",
    "中国": "エリアプライス中国(円/kWh)",
    "四国": "エリアプライス四国(円/kWh)",
    "九州": "エリアプライス九州(円/kWh)"
}

selected_areas = st.sidebar.multiselect("表示するエリア", list(price_columns.keys()), default=list(price_columns.keys()))

# ---------- フィルタと集計 ----------
df_filtered = df[(df["日時"] >= pd.to_datetime(start_date)) & (df["日時"] <= pd.to_datetime(end_date))]

# 集計単位に応じてリサンプリング
if agg_option == "日別":
    df_filtered = df_filtered.set_index("日時").resample("D").mean().reset_index()
elif agg_option == "週別":
    df_filtered = df_filtered.set_index("日時").resample("W-MON").mean().reset_index()

# ---------- グラフタブ ----------
tab1, tab2, tab3, tab4 = st.tabs(["📈 Spike High", "📉 Spike Low", "📊 トレンド", "💹 売買・約定量"])

# 対象のカラム
selected_price_cols = [price_columns[area] for area in selected_areas]

with tab1:
    st.header("Spike High")
    for col in selected_price_cols:
        df_high = df_filtered[df_filtered[col] >= high_criteria]
        if not df_high.empty:
            fig = px.scatter(df_high, x="日時", y=col, title=col, labels={"日時": "日時", col: "価格 (円/kWh)"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"{col} に該当データがありません。")

with tab2:
    st.header("Spike Low")
    for col in selected_price_cols:
        df_low = df_filtered[df_filtered[col] <= low_criteria]
        if not df_low.empty:
            fig = px.scatter(df_low, x="日時", y=col, title=col, labels={"日時": "日時", col: "価格 (円/kWh)"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"{col} に該当データがありません。")

with tab3:
    st.header("年間トレンド")
    fig = go.Figure()
    for col in selected_price_cols:
        fig.add_trace(go.Scatter(x=df_filtered["日時"], y=df_filtered[col], mode='lines', name=col))
    fig.update_layout(title="エリア別価格のトレンド",
                      xaxis_title="日時", yaxis_title="価格 (円/kWh)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.header("売り・買い・約定量トレンド")
    fig = go.Figure()
    for name in ["売り入札量(kWh)", "買い入札量(kWh)", "約定総量(kWh)"]:
        if name in df_filtered.columns:
            fig.add_trace(go.Scatter(x=df_filtered["日時"], y=df_filtered[name], mode='lines', name=name))
    fig.update_layout(title="売買・約定量の推移",
                      xaxis_title="日時", yaxis_title="電力量 (kWh)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# ---------- データエクスポート ----------
st.sidebar.markdown("---")
st.sidebar.subheader("データのエクスポート")

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')  # 日本語対応のUTF-8（BOM付き）

csv = convert_df_to_csv(df_filtered)

st.sidebar.download_button(
    label="📥 フィルタ済みデータをCSVでダウンロード",
    data=csv,
    file_name="filtered_data.csv",
    mime='text/csv'
)
