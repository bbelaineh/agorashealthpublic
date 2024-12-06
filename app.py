from flask import Flask, render_template, request, jsonify
import pandas as pd
import plotly.express as px
import plotly.io as pio

app = Flask(__name__)

data = pd.read_csv("nurse_staffing_data.csv", encoding="ISO-8859-1", low_memory=False)

@app.route('/')
def home():
    return render_template('layout.html')

@app.route('/overview')
def overview():
    # Total hours worked by state
    state_hours = data.groupby('STATE')[['Hrs_RN', 'Hrs_LPN', 'Hrs_CNA']].sum().reset_index()
    state_hours['Total_Hours'] = state_hours[['Hrs_RN', 'Hrs_LPN', 'Hrs_CNA']].sum(axis=1)

    # Calculate the average nurse-to-patient ratio (Hrs_RN / MDScensus)
    data['Nurse_to_Patient_Ratio'] = data['Hrs_RN'] / data['MDScensus']
    avg_nurse_patient_ratio = data['Nurse_to_Patient_Ratio'].mean()

    # Count unique facilities by state
    state_facilities = data.groupby('STATE')['PROVNAME'].nunique().reset_index()
    state_facilities.rename(columns={'PROVNAME': 'Num_Facilities'}, inplace=True)

    # Merge state hours and facility data
    state_summary = pd.merge(state_hours, state_facilities, on='STATE')

    # Create choropleth map showing average nurse-to-patient ratio by state
    state_avg_ratio = data.groupby('STATE')['Nurse_to_Patient_Ratio'].mean().reset_index()
    choropleth_fig = px.choropleth(
        state_avg_ratio,
        locations='STATE',
        locationmode='USA-states',
        color='Nurse_to_Patient_Ratio',
        color_continuous_scale='Viridis',
        scope='usa',
        title='Average Nurse-to-Patient Ratio by State'
    )
    choropleth_html = pio.to_html(choropleth_fig, full_html=False)

    # Top 10 states by total hours worked
    top_states = state_summary.sort_values('Total_Hours', ascending=False).head(10)
    bar_chart_fig = px.bar(
        top_states,
        x='STATE',
        y='Total_Hours',
        title='Top 10 States by Total Hours Worked',
        labels={'STATE': 'State', 'Total_Hours': 'Total Hours Worked'}
    )
    bar_chart_html = pio.to_html(bar_chart_fig, full_html=False)

    # Summary metrics
    total_hours = state_summary['Total_Hours'].sum()
    total_facilities = state_summary['Num_Facilities'].sum()

    # Render overview page with all relevant data
    return render_template(
        'overview.html',
        choropleth_html=choropleth_html,
        bar_chart_html=bar_chart_html,
        total_hours=total_hours,
        total_facilities=total_facilities,
        avg_nurse_patient_ratio=round(avg_nurse_patient_ratio, 2)
    )


@app.route('/demand')
def demand():
    return render_template('demand.html')

@app.route('/geo')
def geo():
    # Get unique states from your data
    states = data['STATE'].unique()

    # Render the page with the state dropdown populated
    return render_template('geo.html', states=states)


@app.route('/get_counties')
def get_counties():
    state = request.args.get('state')
    counties = data[data['STATE'] == state]['COUNTY_NAME'].unique()
    
    # Return the counties as HTML for dynamic dropdown updates
    counties_options = ''.join([f'<option value="{county}">{county}</option>' for county in counties])
    return jsonify({'counties': counties_options})


@app.route('/get_providers')
def get_providers():
    state = request.args.get('state')
    county = request.args.get('county')
    
    providers = data[(data['STATE'] == state) & (data['COUNTY_NAME'] == county)]['PROVNAME'].unique()
    
    # Return the providers as HTML for dynamic dropdown updates
    providers_options = ''.join([f'<option value="{provider}">{provider}</option>' for provider in providers])
    return jsonify({'providers': providers_options})



@app.route('/update_geo_chart')
def update_geo_chart():
    state = request.args.get('state')
    county = request.args.get('county')
    provider = request.args.get('provider')

    # Filter data based on selections
    filtered_data = data
    if state:
        filtered_data = filtered_data[filtered_data['STATE'] == state]
    if county:
        filtered_data = filtered_data[filtered_data['COUNTY_NAME'] == county]
    if provider:
        filtered_data = filtered_data[filtered_data['PROVNAME'] == provider]

    # Create heatmap of total hours by role
    county_hours = filtered_data.groupby('COUNTY_NAME')[['Hrs_RN', 'Hrs_LPN', 'Hrs_CNA']].sum().reset_index()
    
    fig = px.choropleth(
        county_hours,
        locations='COUNTY_NAME',
        color='Hrs_RN',  # Can switch to Hrs_LPN or Hrs_CNA based on selection
        hover_name='COUNTY_NAME',
        color_continuous_scale='Viridis',
        title='Total RN Hours by County'
    )
    heatmap_html = pio.to_html(fig, full_html=False)

    # Create bar chart for staffing dynamics (e.g., total RN hours over time)
    fig_bar = px.bar(
        filtered_data,
        x='WorkDate',
        y='Hrs_RN',  # Can switch to other roles based on selection
        title=f'Total RN Hours for {provider if provider else "Selected Region"}'
    )
    bar_chart_html = pio.to_html(fig_bar, full_html=False)

    return jsonify({'heatmap': heatmap_html, 'bar_chart': bar_chart_html})

@app.route('/trends')
def trends():
    return render_template('trends.html')

@app.route('/update_trends_chart')
def update_trends_chart():
    # Get filter inputs (e.g., date range, nurse role)
    date_range = request.args.get('date_range')  # Weekly/Monthly
    nurse_role = request.args.get('nurse_role')  # Hrs_RN, Hrs_LPN, etc.
    
    # Filter data based on the selections (could be by date range, role, etc.)
    filtered_data = data

    # Aggregate the data based on weekly/monthly trends
    if date_range == 'weekly':
        filtered_data['Week'] = pd.to_datetime(filtered_data['WorkDate']).dt.isocalendar().week
        trend_data = filtered_data.groupby(['Week'])[nurse_role].sum().reset_index()
    elif date_range == 'monthly':
        filtered_data['Month'] = pd.to_datetime(filtered_data['WorkDate']).dt.month
        trend_data = filtered_data.groupby(['Month'])[nurse_role].sum().reset_index()
    else:
        trend_data = filtered_data.groupby(['WorkDate'])[nurse_role].sum().reset_index()

    # Create a line chart for nurse hours worked
    fig_line = px.line(trend_data, x='Week' if date_range == 'weekly' else 'Month', y=nurse_role, 
                       title=f'{nurse_role} Hours Worked over Time')
    line_chart_html = pio.to_html(fig_line, full_html=False)

    # Scatterplot: Compare MDScensus with total nurse hours
    fig_scatter = px.scatter(filtered_data, x='MDScensus', y=nurse_role,
                             title='Scatterplot of MDScensus vs. Nurse Hours Worked')
    scatter_plot_html = pio.to_html(fig_scatter, full_html=False)

    return jsonify({'line_chart': line_chart_html, 'scatter_plot': scatter_plot_html})

@app.route('/insights')
def insights():
    # Render the Insights tab
    return render_template('insights.html')

@app.route('/update_insights', methods=['GET'])
def update_insights():
    # Retrieve filter inputs
    selected_states = request.args.getlist('states')
    selected_counties = request.args.getlist('counties')
    selected_providers = request.args.getlist('providers')

    # Filter the dataset based on inputs
    filtered_data = data
    if selected_states:
        filtered_data = filtered_data[filtered_data['State'].isin(selected_states)]
    if selected_counties:
        filtered_data = filtered_data[filtered_data['County'].isin(selected_counties)]
    if selected_providers:
        filtered_data = filtered_data[filtered_data['PROVNAME'].isin(selected_providers)]

    # Aggregate metrics for visualizations
    provider_summary = filtered_data.groupby('PROVNAME').agg(
        total_hours=('TotalHours', 'sum'),
        avg_census=('MDScensus', 'mean')
    ).reset_index()

    # Create bar chart for provider-level details
    fig_bar = px.bar(
        provider_summary, 
        x='PROVNAME', 
        y='total_hours', 
        title='Total Nurse Hours by Provider',
        labels={'PROVNAME': 'Provider', 'total_hours': 'Total Hours'}
    )
    bar_chart_html = pio.to_html(fig_bar, full_html=False)

    # Side-by-side comparison
    county_summary = filtered_data.groupby('County').agg(
        total_hours=('TotalHours', 'sum'),
        avg_census=('MDScensus', 'mean')
    ).reset_index()
    fig_compare = px.bar(
        county_summary, 
        x='County', 
        y='total_hours', 
        color='avg_census',
        title='Side-by-Side Comparison of Counties',
        labels={'total_hours': 'Total Hours', 'avg_census': 'Average Census'}
    )
    comparison_chart_html = pio.to_html(fig_compare, full_html=False)

    return jsonify({'bar_chart': bar_chart_html, 'comparison_chart': comparison_chart_html})

@app.route('/get_filter_options', methods=['GET'])
def get_filter_options():
    # Extract unique states, counties, and providers
    states = data['State'].unique().tolist()
    counties = data['County'].unique().tolist()
    providers = data['PROVNAME'].unique().tolist()
    return jsonify({'states': states, 'counties': counties, 'providers': providers})


if __name__ == '__main__':
    app.run(debug=True)
