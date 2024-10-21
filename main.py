import streamlit as st
import pandas as pd
import numpy as np
import joblib
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

# Load the trained models
model_co2 = joblib.load('greenhouse_gas_model_co2.joblib')
model_co = joblib.load('greenhouse_gas_model_co.joblib')
model_ch4 = joblib.load('greenhouse_gas_model_ch4.joblib')

# OpenWeatherMap API key
API_KEY = "b7e6baf62f44d6f3052581fd70c52e2b"  # Replace with your actual API key

def get_air_quality(lat, lon):
    base_url = "http://api.openweathermap.org/data/2.5/air_pollution"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY
    }
    try:
        response = requests.get(base_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['list'][0]['components']
        else:
            st.warning(f"Failed to fetch air quality data. Status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.warning(f"Error fetching air quality data: {e}")
        return None

def get_air_quality_forecast(lat, lon):
    base_url = "http://api.openweathermap.org/data/2.5/air_pollution/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY
    }
    try:
        response = requests.get(base_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['list']
        else:
            st.warning(f"Failed to fetch air quality forecast data. Status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.warning(f"Error fetching air quality forecast data: {e}")
        return None

st.title('Predicting future emissions of greenhouse gases with respect to past emissions')

st.write("""
This app predicts CO2, CO, and CH4 concentrations based on location and date for the next 60 days. 
It also attempts to fetch real-time air quality data and provides various visualizations to help understand the data.
""")

# Sidebar for filters
st.sidebar.header("Gas Selection")
show_co2 = st.sidebar.checkbox("Show CO2", value=True)
show_co = st.sidebar.checkbox("Show CO", value=False)
show_ch4 = st.sidebar.checkbox("Show CH4", value=False)

# Create input fields
latitude = st.slider('Latitude', min_value=-90.0, max_value=90.0, value=40.7128, step=0.1)
longitude = st.slider('Longitude', min_value=-180.0, max_value=180.0, value=-74.0060, step=0.1)
current_date = datetime.now()

# Generate predictions for the next 60 days
dates = [current_date + timedelta(days=i) for i in range(60)]
days_of_year = [date.timetuple().tm_yday for date in dates]
input_data = np.array([[latitude, longitude, day] for day in days_of_year])

predictions_co2 = model_co2.predict(input_data) if show_co2 else []
predictions_co = model_co.predict(input_data) if show_co else []
predictions_ch4 = model_ch4.predict(input_data) if show_ch4 else []

st.subheader('Model Predictions for the Next 60 Days')

# Create a DataFrame with the predictions
df_predictions = pd.DataFrame({'Date': dates})
if show_co2:
    df_predictions['CO2'] = predictions_co2
if show_co:
    df_predictions['CO'] = predictions_co
if show_ch4:
    df_predictions['CH4'] = predictions_ch4

# Display the predictions
st.write(df_predictions)

# Visualize the predictions
fig = go.Figure()
if show_co2:
    fig.add_trace(go.Scatter(x=df_predictions['Date'], y=df_predictions['CO2'], mode='lines', name='CO2'))
if show_co:
    fig.add_trace(go.Scatter(x=df_predictions['Date'], y=df_predictions['CO'], mode='lines', name='CO'))
if show_ch4:
    fig.add_trace(go.Scatter(x=df_predictions['Date'], y=df_predictions['CH4'], mode='lines', name='CH4'))

fig.update_layout(title='Predicted Gas Concentrations for the Next 60 Days',
                  xaxis_title='Date',
                  yaxis_title='Concentration (ppm)')
st.plotly_chart(fig)

# Fetch real-time data
st.subheader('Real-time Air Quality Data')
air_quality = get_air_quality(latitude, longitude)

if air_quality:
    st.write("Current air quality components:")
    for component, value in air_quality.items():
        st.write(f"{component}: {value}")
    
    # Bar chart of air quality components
    fig_bar = px.bar(x=list(air_quality.keys()), y=list(air_quality.values()),
                     labels={'x': 'Component', 'y': 'Concentration (μg/m³)'},
                     title='Air Quality Components')
    st.plotly_chart(fig_bar)
else:
    st.info("Real-time air quality data is currently unavailable. Please check your internet connection or try again later.")

# Fetch and visualize air quality forecast
forecast_data = get_air_quality_forecast(latitude, longitude)

if forecast_data:
    # Prepare data for time series chart
    times = [datetime.fromtimestamp(item['dt']) for item in forecast_data]
    co_values = [item['components']['co'] for item in forecast_data]
    
    # Time series chart
    fig_time = go.Figure()
    fig_time.add_trace(go.Scatter(x=times, y=co_values, mode='lines+markers', name='CO'))
    fig_time.update_layout(title='CO Concentration Forecast',
                           xaxis_title='Time',
                           yaxis_title='Concentration (μg/m³)')
    st.plotly_chart(fig_time)

    # Graph chart of predicted vs "actual" (forecast) values
    if show_co:
        min_length = min(len(predictions_co), len(co_values))
        
        fig_comparison = go.Figure()
        
        # Add predicted CO values
        fig_comparison.add_trace(go.Scatter(
            x=list(range(min_length)), 
            y=predictions_co[:min_length], 
            mode='lines', 
            name='Predicted CO',
            line=dict(color='blue')
        ))
        
        # Add forecast CO values
        fig_comparison.add_trace(go.Scatter(
            x=list(range(min_length)), 
            y=co_values[:min_length], 
            mode='lines', 
            name='Forecast CO',
            line=dict(color='red')
        ))
        
        fig_comparison.update_layout(
            title='Predicted CO vs Forecast CO',
            xaxis_title='Time Points',
            yaxis_title='CO Concentration',
            legend_title='Data Source'
        )
        
        st.plotly_chart(fig_comparison)
    else:
        st.info("Enable CO in the sidebar to see the comparison between predicted and forecast CO values.")
else:
    st.info("Air quality forecast data is currently unavailable. Please check your internet connection or try again later.")

# Map to visualize the location
st.subheader('Location')
df = pd.DataFrame({'lat': [latitude], 'lon': [longitude]})
st.map(df)

# Information about the project
st.subheader('About this project')
st.write("""
This project was developed for the MSME Idea Hackathon 4.0. It uses machine learning models
trained on synthetic data to predict CO2, CO, and CH4 concentrations at different locations for the next 60 days.
When available, the predictions are compared with real-time air quality data and forecasts from OpenWeatherMap.
""")

# Model performance metrics
st.subheader('Model Performance')
st.write("""
The models' performance metrics on the test set:
- CO2 - Mean Squared Error: X1, R-squared Score: Y1
- CO - Mean Squared Error: X2, R-squared Score: Y2
- CH4 - Mean Squared Error: X3, R-squared Score: Y3

""")

# Disclaimer
st.sidebar.success("""
This is a demonstration app using models trained on synthetic data based on real-world patterns.

Disclaimer: Real-world gas concentrations may vary significantly from these predictions.
""")
