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

st.markdown("""
<style>
.main-title {
    font-size: 42px;
    font-weight: 900;
    color: #111827;
}
.sub-title {
    font-size: 18px;
    color: #6B7280;
}
.metric-card {
    background: linear-gradient(135deg, #4F46E5, #7C3AED);
    color: white;
    padding: 22px;
    border-radius: 18px;
    text-align: center;
    box-shadow: 0px 4px 18px rgba(0,0,0,0.12);
}
.insight-box {
    background: #EEF2FF;
    padding: 22px;
    border-radius: 18px;
    border-left: 6px solid #4F46E5;
    font-size: 16px;
}
.stButton > button {
    background-color: #4F46E5;
    color: white;
    border-radius: 12px;
    height: 48px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="main-title">📊 AI Prompt-Based Dashboard Generator</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="sub-title">Upload data, write one prompt, and AI will generate KPIs, charts, maps, and interpretation.</div>',
    unsafe_allow_html=True
)

st.divider()

# ---------------- Sidebar: only setup ----------------
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

# ---------------- Check API and Data ----------------
if not api_key:
    st.warning("Please paste your OpenAI API key in the sidebar.")
    st.stop()

if uploaded_file is None:
    st.info("Please upload your CSV or Excel file in the sidebar.")
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

# Clean column names
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

# ---------------- Prompt-only interface ----------------
st.subheader("💬 Write Your Dashboard Prompt")

user_prompt = st.text_area(
    "Describe the dashboard you want",
    placeholder="Example: Create an executive sales dashboard with KPIs, regional performance, product analysis, trends, map if possible, and business recommendations.",
    height=130
)

generate = st.button("🚀 Generate AI Dashboard", use_container_width=True)

if not generate:
    st.info("Enter a prompt and click Generate AI Dashboard.")
    st.stop()

if not user_prompt.strip():
    st.warning("Please write a dashboard prompt first.")
    st.stop()

# ---------------- Dataset Summary ----------------
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

Your task:
Create a dashboard plan using only available dataset columns.

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
  "interpretation": "short executive interpretation with insights and recommendations"
}}

Rules:
- Use only columns that exist in the dataset.
- Create 4 to 6 useful charts.
- Use map only if latitude and longitude columns exist.
- Prefer business-friendly charts.
- Do not include markdown.
- Do not include explanation outside JSON.
"""

# ---------------- AI dashboard plan ----------------
try:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a BI dashboard generator. Return only valid JSON."
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
    st.error(f"AI dashboard planning error: {e}")
    st.stop()

# ---------------- Helper functions ----------------
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
            return f"{value/1_000_000:.2f}M"
        elif abs(value) >= 1_000:
            return f"{value/1_000:.2f}K"
        else:
            return f"{value:,.2f}"
    except:
        return str(value)


# ---------------- Render Dashboard ----------------
st.subheader(plan.get("dashboard_title", "AI Generated Dashboard"))

# KPI Cards
kpis = plan.get("kpis", [])[:4]

if kpis:
    kpi_cols = st.columns(len(kpis))

    for i, kpi in enumerate(kpis):
        title = kpi.get("title", "KPI")
        column = kpi.get("column")
        aggregation = kpi.get("aggregation", "sum")

        if column in df.columns:
            value = calculate_kpi(df, column, aggregation)

            with kpi_cols[i]:
                st.markdown(f"""
                <div class="metric-card">
                    <h2>{format_number(value)}</h2>
                    <p>{title}</p>
                </div>
                """, unsafe_allow_html=True)

st.divider()

# Charts
charts = plan.get("charts", [])

for i in range(0, len(charts), 2):
    cols = st.columns(2)

    for j in range(2):
        if i + j >= len(charts):
            break

        chart = charts[i + j]

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

        chart_df = aggregate_data(df, x, y, aggregation)

        try:
            with cols[j]:
                if chart_type == "bar":
                    if aggregation == "count":
                        fig = px.bar(chart_df, x=x, y="count", title=title, color=color)
                    else:
                        fig = px.bar(chart_df, x=x, y=y, title=title, color=color)

                elif chart_type == "line":
                    fig = px.line(chart_df, x=x, y=y, title=title, color=color)

                elif chart_type == "scatter":
                    fig = px.scatter(chart_df, x=x, y=y, title=title, color=color)

                elif chart_type == "pie":
                    fig = px.pie(chart_df, names=x, values=y, title=title)

                elif chart_type == "box":
                    fig = px.box(df, x=x, y=y, title=title, color=color)

                elif chart_type == "histogram":
                    fig = px.histogram(df, x=x, title=title, color=color)

                else:
                    fig = px.bar(chart_df, x=x, y=y, title=title, color=color)

                fig.update_layout(
                    template="plotly_white",
                    height=430,
                    title_font_size=20,
                    margin=dict(l=20, r=20, t=60, b=30)
                )

                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.warning(f"Could not create chart: {title}")

# ---------------- Map ----------------
map_plan = plan.get("map", {})

if map_plan.get("create_map") is True:
    lat = map_plan.get("lat")
    lon = map_plan.get("lon")
    size = map_plan.get("size")
    color = map_plan.get("color")
    map_title = map_plan.get("title", "Map View")

    if lat in df.columns and lon in df.columns:
        st.subheader("🗺️ Map View")

        try:
            fig_map = px.scatter_mapbox(
                df,
                lat=lat,
                lon=lon,
                size=size if size in df.columns else None,
                color=color if color in df.columns else None,
                hover_data=df.columns,
                zoom=3,
                height=550,
                title=map_title
            )

            fig_map.update_layout(
                mapbox_style="open-street-map",
                margin=dict(l=0, r=0, t=50, b=0)
            )

            st.plotly_chart(fig_map, use_container_width=True)

        except Exception as e:
            st.warning("Map could not be created.")

# ---------------- Interpretation ----------------
st.subheader("🧠 AI Interpretation")

interpretation = plan.get("interpretation", "No interpretation generated.")

st.markdown(f"""
<div class="insight-box">
{interpretation}
</div>
""", unsafe_allow_html=True)

# ---------------- Optional data preview hidden in expander ----------------
with st.expander("View uploaded data"):
    st.dataframe(df.head(50), use_container_width=True)
