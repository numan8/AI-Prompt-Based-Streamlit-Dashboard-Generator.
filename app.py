import json
import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI

st.set_page_config(
    page_title="AI Dashboard Generator",
    page_icon="📊",
    layout="wide"
)

CUSTOM_COLORS = [
    "#2563EB", "#7C3AED", "#EC4899", "#F59E0B",
    "#10B981", "#06B6D4", "#EF4444", "#84CC16"
]

KPI_COLORS = [
    "linear-gradient(135deg, #2563EB, #06B6D4)",
    "linear-gradient(135deg, #7C3AED, #EC4899)",
    "linear-gradient(135deg, #F59E0B, #EF4444)",
    "linear-gradient(135deg, #10B981, #84CC16)"
]

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #EEF2FF 0%, #FFF7ED 45%, #ECFEFF 100%);
}
.block-container {
    padding-top: 0.8rem;
    padding-bottom: 1rem;
    padding-left: 1.6rem;
    padding-right: 1.6rem;
}
.main-title {
    font-size: 28px;
    font-weight: 900;
    color: #111827;
}
.sub-title {
    font-size: 13px;
    color: #4B5563;
    margin-bottom: 10px;
}
.metric-card {
    color: white;
    padding: 18px;
    border-radius: 18px;
    text-align: center;
    box-shadow: 0px 6px 20px rgba(0,0,0,0.18);
}
.metric-card h2 {
    font-size: 26px;
    margin: 0;
}
.metric-card p {
    font-size: 13px;
    margin: 0;
}
.insight-box {
    background: white;
    padding: 18px;
    border-radius: 18px;
    border-left: 6px solid #7C3AED;
    font-size: 14px;
    line-height: 1.6;
    box-shadow: 0px 4px 18px rgba(0,0,0,0.10);
}
h1, h2, h3 {
    margin-top: 0.5rem !important;
    margin-bottom: 0.6rem !important;
}
.stTextArea textarea {
    min-height: 90px !important;
    border-radius: 16px;
    font-size: 15px;
}
.stButton > button {
    height: 48px;
    background: linear-gradient(135deg, #2563EB, #EC4899);
    color: white;
    border-radius: 14px;
    font-weight: 800;
    border: none;
    font-size: 16px;
}
[data-testid="stVerticalBlock"] {
    gap: 0.9rem;
}
[data-testid="stHorizontalBlock"] {
    gap: 1rem;
}
</style>
""", unsafe_allow_html=True)


def load_file(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        data = pd.read_csv(uploaded_file)
    else:
        preview = pd.read_excel(uploaded_file, sheet_name=0, header=None)
        header_row = None
        important_cols = ["Net_Sales", "Latitude", "Longitude", "City", "Province"]

        for i in range(min(15, len(preview))):
            row_values = preview.iloc[i].astype(str).str.strip().tolist()
            match_count = sum(col in row_values for col in important_cols)
            if match_count >= 2:
                header_row = i
                break

        if header_row is not None:
            data = pd.read_excel(uploaded_file, sheet_name=0, header=header_row)
        else:
            data = pd.read_excel(uploaded_file, sheet_name=0)

    data.columns = [str(c).strip() for c in data.columns]
    data = data.dropna(how="all")

    for col in data.columns:
        if data[col].dtype == "object":
            data[col] = pd.to_numeric(
                data[col].astype(str).str.replace(",", "").str.replace("%", ""),
                errors="ignore"
            )

    return data


def find_col(df, possible_names):
    lower_cols = {c.lower(): c for c in df.columns}

    for name in possible_names:
        if name.lower() in lower_cols:
            return lower_cols[name.lower()]

    for col in df.columns:
        for name in possible_names:
            if name.lower() in col.lower():
                return col

    return None


def aggregate_data(data, x, y, aggregation):
    if aggregation == "none" or y is None:
        return data

    if x not in data.columns:
        return data

    if aggregation == "sum" and y in data.columns:
        return data.groupby(x, as_index=False)[y].sum()

    if aggregation == "mean" and y in data.columns:
        return data.groupby(x, as_index=False)[y].mean()

    if aggregation == "count":
        return data.groupby(x, as_index=False).size().rename(columns={"size": "count"})

    return data


def calculate_kpi(data, column, aggregation):
    if column is None or column not in data.columns:
        return 0

    series = pd.to_numeric(data[column], errors="coerce")

    if aggregation == "sum":
        return series.sum()
    elif aggregation == "mean":
        return series.mean()
    elif aggregation == "count":
        return series.count()
    elif aggregation == "max":
        return series.max()
    elif aggregation == "min":
        return series.min()
    else:
        return series.sum()


def format_number(value):
    try:
        if pd.isna(value):
            return "0"
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif abs(value) >= 1_000:
            return f"{value / 1_000:.1f}K"
        else:
            return f"{value:,.0f}"
    except Exception:
        return str(value)


def style_fig(fig, height=360):
    fig.update_layout(
        template="plotly_white",
        height=height,
        title_font_size=18,
        title_x=0.03,
        margin=dict(l=25, r=25, t=60, b=35),
        font=dict(size=12),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10)
        )
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(size=10))
    fig.update_yaxes(gridcolor="#E5E7EB", tickfont=dict(size=10))
    return fig


def create_default_charts(df):
    charts = []

    net_sales = find_col(df, ["Net_Sales", "Sales", "Revenue", "Amount"])
    profit = find_col(df, ["Profit", "Net_Profit"])
    province = find_col(df, ["Province", "State", "Region"])
    city = find_col(df, ["City", "Location"])
    product = find_col(df, ["Product", "Item"])
    category = find_col(df, ["Category", "Product_Category"])
    segment = find_col(df, ["Customer_Segment", "Segment"])
    channel = find_col(df, ["Sales_Channel", "Channel"])

    if province and net_sales:
        charts.append({"title": "Sales by Province", "type": "bar", "x": province, "y": net_sales, "color": province, "aggregation": "sum"})

    if city and net_sales:
        charts.append({"title": "Sales by City", "type": "bar", "x": city, "y": net_sales, "color": city, "aggregation": "sum"})

    if product and profit:
        charts.append({"title": "Profit by Product", "type": "bar", "x": product, "y": profit, "color": product, "aggregation": "sum"})

    if category and net_sales:
        charts.append({"title": "Sales by Category", "type": "pie", "x": category, "y": net_sales, "color": category, "aggregation": "sum"})

    if segment and net_sales:
        charts.append({"title": "Sales by Segment", "type": "bar", "x": segment, "y": net_sales, "color": segment, "aggregation": "sum"})

    if channel and net_sales:
        charts.append({"title": "Sales by Channel", "type": "pie", "x": channel, "y": net_sales, "color": channel, "aggregation": "sum"})

    return charts[:6]


def create_chart(df, chart, categorical_cols, height=360):
    title = chart.get("title", "Chart")
    chart_type = chart.get("type", "bar")
    x = chart.get("x")
    y = chart.get("y")
    color = chart.get("color")
    aggregation = chart.get("aggregation", "none")

    if x not in df.columns:
        return None

    if y is not None and y not in df.columns:
        y = None

    if color is not None and color not in df.columns:
        color = None

    if color is None:
        color = x if x in categorical_cols else None

    chart_df = aggregate_data(df, x, y, aggregation)

    if chart_type == "bar":
        y_col = "count" if aggregation == "count" else y
        fig = px.bar(
            chart_df,
            x=x,
            y=y_col,
            title=title,
            color=color if color in chart_df.columns else x,
            color_discrete_sequence=CUSTOM_COLORS
        )

    elif chart_type == "line":
        fig = px.line(
            chart_df,
            x=x,
            y=y,
            title=title,
            color=color if color in chart_df.columns else None,
            color_discrete_sequence=CUSTOM_COLORS
        )
        fig.update_traces(line=dict(width=4), marker=dict(size=7))

    elif chart_type == "scatter":
        fig = px.scatter(
            chart_df,
            x=x,
            y=y,
            title=title,
            color=color if color in chart_df.columns else None,
            color_discrete_sequence=CUSTOM_COLORS,
            size=y if y in chart_df.columns else None
        )

    elif chart_type == "pie":
        fig = px.pie(
            chart_df,
            names=x,
            values=y,
            title=title,
            color_discrete_sequence=CUSTOM_COLORS
        )

    elif chart_type == "box":
        fig = px.box(
            df,
            x=x,
            y=y,
            title=title,
            color=color if color in df.columns else x,
            color_discrete_sequence=CUSTOM_COLORS
        )

    elif chart_type == "histogram":
        fig = px.histogram(
            df,
            x=x,
            title=title,
            color=color if color in df.columns else x,
            color_discrete_sequence=CUSTOM_COLORS
        )

    else:
        fig = px.bar(
            chart_df,
            x=x,
            y=y,
            title=title,
            color=color if color in chart_df.columns else x,
            color_discrete_sequence=CUSTOM_COLORS
        )

    return style_fig(fig, height=height)


def create_map(df, height=430):
    lat_col = find_col(df, ["Latitude", "Lat"])
    lon_col = find_col(df, ["Longitude", "Lon", "Lng"])
    sales_col = find_col(df, ["Net_Sales", "Sales", "Revenue", "Amount"])
    city_col = find_col(df, ["City", "Location"])
    province_col = find_col(df, ["Province", "State", "Region"])
    profit_col = find_col(df, ["Profit", "Net_Profit"])

    if not lat_col or not lon_col:
        return None

    map_hover = [
        c for c in [city_col, province_col, sales_col, profit_col]
        if c in df.columns
    ]

    fig_map = px.scatter_mapbox(
        df,
        lat=lat_col,
        lon=lon_col,
        size=sales_col if sales_col in df.columns else None,
        color=sales_col if sales_col in df.columns else province_col,
        hover_name=city_col if city_col in df.columns else None,
        hover_data=map_hover,
        color_continuous_scale="Turbo",
        zoom=4,
        height=height,
        title="Sales Map"
    )

    fig_map.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=0, r=0, t=50, b=0),
        font=dict(size=12),
        paper_bgcolor="white"
    )

    return fig_map


# Header
st.markdown('<div class="main-title">📊 AI Prompt-Based Dashboard Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Generate either one chart or a full dashboard from a single prompt.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Setup")
    api_key = st.text_input("OpenAI API Key", type="password", placeholder="Paste your API key")
    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

if not api_key:
    st.warning("Paste your OpenAI API key in the sidebar.")
    st.stop()

if uploaded_file is None:
    st.info("Upload your CSV or Excel file in the sidebar.")
    st.stop()

client = OpenAI(api_key=api_key)

try:
    df = load_file(uploaded_file)
except Exception as e:
    st.error(f"File loading error: {e}")
    st.stop()

st.sidebar.success(f"Loaded {df.shape[0]} rows and {df.shape[1]} columns")

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

date_cols = []
for col in df.columns:
    try:
        temp = pd.to_datetime(df[col], errors="coerce")
        if temp.notna().sum() > len(df) * 0.5:
            date_cols.append(col)
    except Exception:
        pass

user_prompt = st.text_area(
    "💬 Dashboard Prompt",
    placeholder="Examples: Create one map of Pakistan by Net Sales OR Create complete sales dashboard with map, KPIs, charts and recommendations.",
    height=90
)

generate = st.button("🚀 Generate", use_container_width=True)

if not generate:
    st.stop()

if not user_prompt.strip():
    st.warning("Write a prompt first.")
    st.stop()

summary = {
    "columns": list(df.columns),
    "rows": int(df.shape[0]),
    "numeric_columns": numeric_cols,
    "categorical_columns": categorical_cols,
    "date_columns": date_cols,
    "sample_data": df.head(10).to_dict(orient="records")
}

dashboard_prompt = f"""
You are an expert BI dashboard designer.

User request:
{user_prompt}

Dataset summary:
{json.dumps(summary, default=str)}

Return ONLY valid JSON.

JSON format:
{{
  "mode": "single_plot | dashboard",
  "dashboard_title": "short title",
  "kpis": [
    {{
      "title": "KPI title",
      "column": "numeric column name",
      "aggregation": "sum | mean | count | max | min"
    }}
  ],
  "charts": [
    {{
      "title": "chart title",
      "type": "bar | line | scatter | pie | box | histogram | map",
      "x": "column name or null",
      "y": "column name or null",
      "color": "column name or null",
      "aggregation": "sum | mean | count | none"
    }}
  ],
  "interpretation": "short interpretation"
}}

Rules:
- If user asks for one chart, one plot, single plot, only map, only chart, return mode = single_plot and only one chart.
- If user asks for full dashboard, complete dashboard, executive dashboard, return mode = dashboard.
- If user asks map and Latitude/Longitude exist, use chart type = map.
- Use only dataset columns.
- For dashboard mode, create 4 KPI cards and 4 to 6 charts.
- For single_plot mode, create only one large visualization and one short interpretation.
- If Net_Sales exists, prioritize it for sales analysis.
- Do not include markdown.
"""

try:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You generate BI dashboard JSON only."},
            {"role": "user", "content": dashboard_prompt}
        ],
        temperature=0.2
    )

    raw_json = response.choices[0].message.content.strip()
    raw_json = raw_json.replace("```json", "").replace("```", "").strip()
    plan = json.loads(raw_json)

except Exception as e:
    st.error(f"AI planning error: {e}")
    st.stop()

mode = plan.get("mode", "dashboard")
charts = plan.get("charts", [])

st.subheader(plan.get("dashboard_title", "AI Dashboard"))

# Single plot mode
if mode == "single_plot":
    chart = charts[0] if charts else None

    if chart and chart.get("type") == "map":
        fig = create_map(df, height=620)
    elif chart:
        fig = create_chart(df, chart, categorical_cols, height=620)
    else:
        fig = create_map(df, height=620)

    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Could not create the requested plot.")

    interpretation = plan.get("interpretation", "")
    if interpretation:
        st.markdown(f"""
        <div class="insight-box">
        <b>AI Interpretation:</b> {interpretation}
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# Dashboard mode
kpis = plan.get("kpis", [])[:4]

fallback_kpis = [
    (find_col(df, ["Net_Sales", "Sales", "Revenue", "Amount"]), "Total Sales", "sum"),
    (find_col(df, ["Profit", "Net_Profit"]), "Total Profit", "sum"),
    (find_col(df, ["Quantity", "Units"]), "Quantity Sold", "sum"),
    (find_col(df, ["Target_Achievement_Percent", "Target_Achievement"]), "Target Achievement", "mean"),
]

for col, title, agg in fallback_kpis:
    if len(kpis) < 4 and col:
        kpis.append({"title": title, "column": col, "aggregation": agg})

kpi_cols = st.columns(4)

for i, kpi in enumerate(kpis[:4]):
    title = kpi.get("title", "KPI")
    column = kpi.get("column")
    aggregation = kpi.get("aggregation", "sum")
    value = calculate_kpi(df, column, aggregation)

    with kpi_cols[i]:
        st.markdown(f"""
        <div class="metric-card" style="background:{KPI_COLORS[i]}">
            <h2>{format_number(value)}</h2>
            <p>{title}</p>
        </div>
        """, unsafe_allow_html=True)

fig_map = create_map(df, height=420)
if fig_map:
    st.plotly_chart(fig_map, use_container_width=True)

charts = [c for c in charts if c.get("type") != "map"][:6]

if len(charts) < 6:
    for c in create_default_charts(df):
        if len(charts) < 6:
            charts.append(c)

for i in range(0, len(charts), 2):
    cols = st.columns(2)

    for j in range(2):
        chart_index = i + j
        if chart_index >= len(charts):
            continue

        chart = charts[chart_index]

        try:
            fig = create_chart(df, chart, categorical_cols, height=360)
            if fig:
                with cols[j]:
                    st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.warning(f"Could not create chart: {chart.get('title', 'Chart')}")

interpretation = plan.get("interpretation", "")

if interpretation:
    st.markdown(f"""
    <div class="insight-box">
    <b>AI Interpretation:</b> {interpretation}
    </div>
    """, unsafe_allow_html=True)
