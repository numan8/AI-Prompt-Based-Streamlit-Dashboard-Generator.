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
    "#2563EB",
    "#7C3AED",
    "#EC4899",
    "#F59E0B",
    "#10B981",
    "#06B6D4",
    "#EF4444",
    "#84CC16"
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
    background: linear-gradient(135deg, #EEF2FF 0%, #FDF2F8 50%, #ECFEFF 100%);
}
.block-container {
    padding-top: 0.4rem;
    padding-bottom: 0.2rem;
    padding-left: 1rem;
    padding-right: 1rem;
}
.main-title {
    font-size: 24px;
    font-weight: 900;
    color: #111827;
    margin-bottom: 0px;
}
.sub-title {
    font-size: 12px;
    color: #4B5563;
    margin-bottom: 2px;
}
.metric-card {
    color: white;
    padding: 8px;
    border-radius: 13px;
    text-align: center;
    box-shadow: 0px 4px 14px rgba(0,0,0,0.18);
}
.metric-card h2 {
    font-size: 19px;
    margin: 0;
}
.metric-card p {
    font-size: 10px;
    margin: 0;
}
.insight-box {
    background: white;
    padding: 9px;
    border-radius: 12px;
    border-left: 5px solid #7C3AED;
    font-size: 11px;
    box-shadow: 0px 3px 12px rgba(0,0,0,0.10);
}
h1, h2, h3 {
    font-size: 15px !important;
    margin-top: 0.1rem !important;
    margin-bottom: 0.2rem !important;
}
.stTextArea textarea {
    min-height: 60px !important;
    border-radius: 12px;
}
.stButton > button {
    height: 34px;
    background: linear-gradient(135deg, #2563EB, #EC4899);
    color: white;
    border-radius: 10px;
    font-weight: 800;
    border: none;
}
[data-testid="stVerticalBlock"] {
    gap: 0.25rem;
}
[data-testid="stHorizontalBlock"] {
    gap: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="main-title">📊 AI Prompt-Based Dashboard Generator</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="sub-title">Upload data, write one prompt, and generate a colorful AI dashboard.</div>',
    unsafe_allow_html=True
)

with st.sidebar:
    st.header("⚙️ Setup")

    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="Paste your API key"
    )

    uploaded_file = st.file_uploader(
        "Upload CSV or Excel file",
        type=["csv", "xlsx"]
    )

if not api_key:
    st.warning("Paste your OpenAI API key in the sidebar.")
    st.stop()

if uploaded_file is None:
    st.info("Upload your CSV or Excel file in the sidebar.")
    st.stop()

client = OpenAI(api_key=api_key)

try:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"File loading error: {e}")
    st.stop()

df.columns = [str(col).strip() for col in df.columns]

numeric_cols = df.select_dtypes(include="number").columns.tolist()
categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
date_cols = []

for col in df.columns:
    try:
        temp = pd.to_datetime(df[col], errors="coerce")
        if temp.notna().sum() > len(df) * 0.5:
            date_cols.append(col)
    except:
        pass

user_prompt = st.text_area(
    "💬 Dashboard Prompt",
    placeholder="Example: Create a colorful CEO dashboard with KPIs, trends, regional analysis, product performance, and recommendations.",
    height=60
)

generate = st.button("🚀 Generate Dashboard", use_container_width=True)

if not generate:
    st.stop()

if not user_prompt.strip():
    st.warning("Write a dashboard prompt first.")
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
      "type": "bar | line | scatter | pie | box | histogram",
      "x": "column name",
      "y": "column name or null",
      "color": "column name or null",
      "aggregation": "sum | mean | count | none"
    }}
  ],
  "map": {{
    "create_map": true or false,
    "lat": "latitude column or null",
    "lon": "longitude column or null",
    "size": "numeric column or null",
    "color": "column or null",
    "title": "map title"
  }},
  "interpretation": "very short dashboard interpretation and recommendation"
}}

Rules:
- Use only dataset columns.
- Create exactly 4 KPI cards.
- Create exactly 4 colorful charts.
- Use categorical columns for color where possible.
- Keep dashboard suitable for one screen.
- Use map only if latitude and longitude exist.
- Interpretation must be short.
- Do not include markdown.
"""

try:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "You generate compact colorful BI dashboard JSON only."
            },
            {
                "role": "user",
                "content": dashboard_prompt
            }
        ],
        temperature=0.2
    )

    raw_json = response.choices[0].message.content.strip()
    raw_json = raw_json.replace("```json", "").replace("```", "").strip()
    plan = json.loads(raw_json)

except Exception as e:
    st.error(f"AI planning error: {e}")
    st.stop()


def aggregate_data(data, x, y, aggregation):
    if aggregation == "none" or y is None:
        return data

    if aggregation == "sum":
        return data.groupby(x, as_index=False)[y].sum()

    if aggregation == "mean":
        return data.groupby(x, as_index=False)[y].mean()

    if aggregation == "count":
        return data.groupby(x, as_index=False).size().rename(columns={"size": "count"})

    return data


def calculate_kpi(data, column, aggregation):
    if column not in data.columns:
        return 0

    if aggregation == "sum":
        return data[column].sum()
    elif aggregation == "mean":
        return data[column].mean()
    elif aggregation == "count":
        return data[column].count()
    elif aggregation == "max":
        return data[column].max()
    elif aggregation == "min":
        return data[column].min()
    else:
        return data[column].sum()


def format_number(value):
    try:
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif abs(value) >= 1_000:
            return f"{value / 1_000:.1f}K"
        else:
            return f"{value:,.0f}"
    except:
        return str(value)


st.subheader(plan.get("dashboard_title", "AI Dashboard"))

kpis = plan.get("kpis", [])[:4]

if len(kpis) < 4:
    for col in numeric_cols[:4 - len(kpis)]:
        kpis.append({
            "title": col,
            "column": col,
            "aggregation": "sum"
        })

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

charts = plan.get("charts", [])[:4]

for i in range(0, 4, 2):
    cols = st.columns(2)

    for j in range(2):
        chart_index = i + j

        if chart_index >= len(charts):
            continue

        chart = charts[chart_index]

        title = chart.get("title", "Chart")
        chart_type = chart.get("type", "bar")
        x = chart.get("x")
        y = chart.get("y")
        color = chart.get("color")
        aggregation = chart.get("aggregation", "none")

        if x not in df.columns:
            continue

        if y is not None and y not in df.columns:
            y = None

        if color is not None and color not in df.columns:
            color = None

        if color is None:
            color = x if x in categorical_cols else None

        chart_df = aggregate_data(df, x, y, aggregation)

        try:
            with cols[j]:
                if chart_type == "bar":
                    if aggregation == "count":
                        fig = px.bar(
                            chart_df,
                            x=x,
                            y="count",
                            title=title,
                            color=color if color in chart_df.columns else x,
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

                elif chart_type == "line":
                    fig = px.line(
                        chart_df,
                        x=x,
                        y=y,
                        title=title,
                        color=color if color in chart_df.columns else None,
                        color_discrete_sequence=CUSTOM_COLORS
                    )
                    fig.update_traces(line=dict(width=3), marker=dict(size=6))

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

                fig.update_layout(
                    template="plotly_white",
                    height=220,
                    title_font_size=13,
                    title_x=0.03,
                    margin=dict(l=10, r=10, t=35, b=10),
                    font=dict(size=9),
                    paper_bgcolor="white",
                    plot_bgcolor="white",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )

                fig.update_xaxes(showgrid=False)
                fig.update_yaxes(gridcolor="#E5E7EB")

                st.plotly_chart(fig, use_container_width=True)

        except Exception:
            st.warning(f"Could not create chart: {title}")

map_plan = plan.get("map", {})

if map_plan.get("create_map") is True:
    lat = map_plan.get("lat")
    lon = map_plan.get("lon")
    size = map_plan.get("size")
    color = map_plan.get("color")

    if lat in df.columns and lon in df.columns:
        try:
            fig_map = px.scatter_mapbox(
                df,
                lat=lat,
                lon=lon,
                size=size if size in df.columns else None,
                color=color if color in df.columns else None,
                color_discrete_sequence=CUSTOM_COLORS,
                zoom=3,
                height=220,
                title=map_plan.get("title", "Map")
            )

            fig_map.update_layout(
                mapbox_style="open-street-map",
                margin=dict(l=0, r=0, t=35, b=0),
                font=dict(size=9)
            )

            st.plotly_chart(fig_map, use_container_width=True)

        except Exception:
            pass

interpretation = plan.get("interpretation", "")

if interpretation:
    st.markdown(f"""
    <div class="insight-box">
    <b>AI Interpretation:</b> {interpretation}
    </div>
    """, unsafe_allow_html=True)
