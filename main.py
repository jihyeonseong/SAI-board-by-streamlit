import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import os
import time
import sys
from datetime import datetime, timedelta

from plt_setup import finastra_theme

@st.cache(show_spinner=False, suppress_st_warning=True,
          allow_output_mutation=True)
def load_data(data_category='validation'):
    data1 = pd.read_csv(f'./data/{data_category}_1.csv')
    data1.drop(columns=["Unnamed: 0"], inplace=True)
    data2 = pd.read_csv(f'./data/{data_category}_2.csv')
    data2.drop(columns=["Unnamed: 0"], inplace=True)
    data = pd.concat([data1, data2])
    data.set_index('timestamp', inplace=True)
    return data

def filter_on_date(df, start, end):
    end = end + timedelta(days=1)
    df = df[(pd.to_datetime(df.index) >= pd.to_datetime(start)) &
            (pd.to_datetime(df.index) <= pd.to_datetime(end))]
    return df

def main():
    ###### CUSTOMIZE COLOR THEME ######
    alt.themes.register("finastra", finastra_theme)
    alt.themes.enable("finastra")
    violet, fuchsia = ["#694ED6", "#C137A2"]

    ###### SET UP PAGE ######
    icon_path = os.path.join("./img", "icon.png")
    st.set_page_config(page_title="SAI-Board", page_icon=icon_path,
                       layout='centered', initial_sidebar_state="collapsed")
    _, logo, _ = st.columns(3)
    logo.image(icon_path, width=200)
    style = ("text-align:center; padding: 0px; font-family: arial black;, "
             "font-size: 400%")
    title = f"<h1 style='{style}'>SAI<sup>Board</sup></h1><br><br>"
    st.write(title, unsafe_allow_html=True)

    ####### CREATE SIDEBAR CATEGORY FILTER######
    st.sidebar.title("Filter Options")
    date_place = st.sidebar.empty()

    with st.spinner(text="Fetching Data..."):
        data = load_data()

    ###### DATE WIDGET ######
    start = str(data.index.min()).split(' ')[0]
    end = str(data.index.max()).split(' ')[0]
    start = datetime.strptime(start, "%Y-%m-%d")
    end = datetime.strptime(end, "%Y-%m-%d")

    selected_dates = date_place.date_input("Select a Date Range",
                                           value=[start, end], min_value=start, max_value=end, key=None)
    time.sleep(0.8)  # Allow user some time to select the two dates -- hacky :D
    start, end = selected_dates

    data = filter_on_date(data, start, end)

    ###### DISPLAY DATA ######
    URL_Expander = st.expander(f"View Raw Data:", True)
    URL_Expander.write(f"### {len(data):,d} Matching Data by seconds ")
    display_cols = data.columns
    URL_Expander.write(data[display_cols])

    ###### CHART: METRIC OVER TIME ######
    st.markdown("---")
    st.header("Data Monitoring")
    col1, col2, col3 = st.columns((1, 1, 3))
    hour = col1.selectbox("Hour", range(0, 23))
    min = col2.selectbox("Minute", range(0, 60))
    sensor = col3.selectbox("Sensors", data.columns[:-1])
    df = data.copy()
    df = df[hour*3600:(hour+1)*3600].copy()
    df = df[min*60:(min+1)*60].copy()
    df1 = df.loc[:, [sensor]].reset_index()[5:]
    df2 = df.loc[:, [sensor]].rolling(5).mean().reset_index()[5:]
    df1["WHO"] = sensor
    df2["WHO"] = "Rolling Mean"
    plot_df = pd.concat([df1, df2]).reset_index(drop=True)
    plot_df["timestamp"] = pd.to_datetime(plot_df["timestamp"])
    metric_chart = alt.Chart(plot_df, title="Trends Over Time", padding={"left": 10, "top": 1, "right": 10, "bottom": 1}
                             ).mark_line().encode(
        x=alt.X("yearmonthdatehoursminutesseconds(timestamp):O", title="DATE"),
        y=alt.Y(f"{sensor}:Q", scale=alt.Scale(type="linear")),
        color=alt.Color("WHO", legend=None),
        strokeDash=alt.StrokeDash("WHO", sort=None,
                                      legend=alt.Legend(
                                          title=None, symbolType="stroke", symbolFillColor="gray",
                                          symbolStrokeWidth=4, orient="top",
                                      ),
                                  ),
        tooltip=["timestamp", alt.Tooltip(sensor, format=".3f")]
    )
    metric_chart = metric_chart.properties(
        height=340,
        width=200
    ).interactive()
    st.altair_chart(metric_chart, use_container_width=True)

    ###Most Recent Attack Chart###
    st.markdown("---")
    df = data.loc[:, ["attack"]].copy()
    df['filter'] = df["attack"]==1
    df_attack = df.loc[df['filter']==True]
    attack_start = df_attack.index[0]
    cnt = len(df.loc[:attack_start])
    while True:
        if df.iloc[cnt, :]['filter']==False:
            attack_end = df.index[cnt]
            break
        else:
            cnt+=1
    st.header("Recent Attack")
    st.subheader(str(datetime.strptime(attack_end ,"%Y-%m-%d %H:%M:%S")-datetime.strptime(attack_start, "%Y-%m-%d %H:%M:%S"))+" attack remains")
    sensor = st.selectbox("Attacked Sensors", data.columns[:-1])
    col1, col2 = st.columns((1, 4))
    metric_options = [5, 10, 30, 60]
    roll = col1.radio("Rolling Window", options=metric_options)

    df = data.loc[attack_start:attack_end].copy()
    df1 = df.loc[:, [sensor]].reset_index()[roll:]
    df2 = df.loc[:, [sensor]].rolling(roll).mean().reset_index()[roll:]
    df1["WHO"] = sensor
    df2["WHO"] = "Rolling Mean"
    plot_df = pd.concat([df1, df2]).reset_index(drop=True)
    plot_df["timestamp"] = pd.to_datetime(plot_df["timestamp"])
    metric_chart = alt.Chart(plot_df, title="Trends Over Time", padding={"left": 10, "top": 1, "right": 10, "bottom": 1}
                             ).mark_line().encode(
        x=alt.X("yearmonthdatehoursminutesseconds(timestamp):O", title="DATE"),
        y=alt.Y(f"{sensor}:Q", scale=alt.Scale(type="linear")),
        color=alt.Color("WHO", legend=None),
        strokeDash=alt.StrokeDash("WHO", sort=None,
                                  legend=alt.Legend(
                                      title=None, symbolType="stroke", symbolFillColor="gray",
                                      symbolStrokeWidth=4, orient="top",
                                  ),
                                  ),
        tooltip=["timestamp", alt.Tooltip(sensor, format=".3f")]
    )
    metric_chart = metric_chart.properties(
        height=340,
        width=200
    ).interactive()
    col2.altair_chart(metric_chart, use_container_width=True)
          
    ###Model Interpretability###
    st.markdown("---")
    ranking = st.sidebar.slider("Select Number of Important Sensor Ranking", 1, 20, value=5)
    rel_rank = pd.read_csv('./data/ranking.csv')
    rel_ranking.set_index(0, inplace=True)
    top_ranking = rel_rank.index[:ranking]
    conf_plot = alt.Chart(top_ranking, title=f"Top {ranking} important sensors", padding={"left": 1, "top": 10, "right": 1, "bottom": 1}
                    ).mark_bar().encode(
                    x=alt.X("Confidence:Q", title="Confidence"),
                    y=alt.Y("Neighbor:N", sort="-x", title="Similar Company"),
                 tooltip=["Neighbor", alt.Tooltip("Confidence", format=".3f")],
                 color=alt.Color("Confidence:Q", scale=alt.Scale(), legend=None)
                ).properties(
                  height=25 * num_neighbors + 90
                ).configure_axis(grid=False)
    st.altair_chart(conf_plot, use_container_width=True)

if __name__ == '__main__':
    main()
    alt.themes.enable("default")

