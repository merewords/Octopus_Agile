import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os
from octopus_api import OctopusEnergyAPI
from utils import (
    calculate_costs,
    create_rates_chart,
    create_consumption_chart,
    create_cost_chart,
    create_combined_usage_cost_chart
)

# Set page configuration
st.set_page_config(
    page_title="Octopus Energy Dashboard",
    page_icon="🐙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Get API key from environment variable
api_key = os.environ.get('OCTOPUS_API_KEY', '')
MPAN_key = os.environ.get('MPAN_KEY', '')
meter_key = os.environ.get('METER_KEY', '')

# Initialize session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = api_key
if 'mpan' not in st.session_state:
    st.session_state.mpan = MPAN_key  # Default from screenshot
if 'meter_serial' not in st.session_state:
    st.session_state.meter_serial = meter_key  # Default from screenshot
if 'standing_charge' not in st.session_state:
    st.session_state.standing_charge = 0.3954
if 'active_page' not in st.session_state:
    st.session_state.active_page = "Rates"
if 'default_days' not in st.session_state:
    st.session_state.default_days = 30


def sidebar_inputs():
    """Sidebar for API credentials and settings."""
    with st.sidebar:
        st.title("Octopus EnerAgile Dashboard")
        
        # API Status section
        st.header("Connection Status")
        
        if st.session_state.api_key:
            st.success("Connected to Octopus Agile API")
        else:
            st.error("API Key not configured")
        
        # Navigation
        st.header("Navigation")
        page = st.radio("Select Page", ["Rates", "DA5_1LW_Usage"])
        
        # Only show meter inputs if on Usage page
        if page == "DA5_1LW_Usage":
            #st.header("Meter Information")
            
            # Display current meter info
            st.info(f"MPAN: {st.session_state.mpan}")
            st.info(f"Meter Serial: {st.session_state.meter_serial}")
            
            # Allow editing standing charge
            standing_charge = st.number_input(
                "Standing Charge (£/day)",
                value=st.session_state.standing_charge,
                step=0.00,
                format="%.2f",
                help="Daily standing charge in pounds"
            )
            
            # Update standing charge in session state
            st.session_state.standing_charge = standing_charge
            
            # Date range selector for usage page
            st.header("Date Range")
            default_days = st.slider(
                "Days of History", 
                min_value=7, 
                max_value=90, 
                value=30,
                help="Number of days of history to display"
            )
            st.session_state.default_days = default_days
        
        # Update active page in session state
        st.session_state.active_page = page
        
        # Add a refresh button
        if st.button("Refresh Data"):
            st.rerun()


def rates_page():
    """Display the Agile tariff rates page."""
    st.title("Octopus Agile Half-Hour Electricity Rates")
    
    # Check if API key is provided
    if not st.session_state.api_key:
        st.warning("Please provide your Octopus Energy API key in the sidebar.")
        return
    
    # Initialize API client
    api = OctopusEnergyAPI(api_key=st.session_state.api_key)
    
    # Add a loading indicator
    with st.spinner("Fetching latest Agile tariff rates..."):
        # Fetch the tariff rates
        tariff_df = api.get_agile_tariff_rates()
    
    if tariff_df.empty:
        st.error("Failed to fetch tariff rates. Please check your API key and try again.")
        return
    
    # Create the chart and get cheapest slots
    fig, cheapest_slots = create_rates_chart(tariff_df)
    
    # Display the cheapest slots table first
    if not cheapest_slots.empty:
        st.subheader("10 Cheapest Half-Hour Slots Today")
        
        # Format the cheapest slots for display
        display_cheapest = cheapest_slots.copy()
        display_cheapest['Time'] = display_cheapest['time']
        display_cheapest['Period'] = display_cheapest['period']
        display_cheapest['Rate (p/kWh)'] = display_cheapest['value_inc_vat'].round(2)
        
        # Select and order columns for display
        display_cheapest = display_cheapest[['Period', 'Time', 'Rate (p/kWh)']].reset_index(drop=True)
        
        # Use different colors for each period
        def highlight_period(row):
            if 'All day' in row['Period']:
                return ['background-color: rgba(0, 128, 0, 0.2)'] * len(row)
            return [''] * len(row)
        
        # Display the styled table
        st.dataframe(
            display_cheapest.style.apply(highlight_period, axis=1),
            use_container_width=True
        )
        
        # Legend for the table and chart
        col1 = st.columns(1)
        with col1:
            st.markdown("🟢 **All day (00:01-23:59)**")
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=True)
    
    # Get timezone
    uk_tz = pytz.timezone('Europe/London')
    today = datetime.now(uk_tz).date()
    
    # Add expandable section for all of today's rates
    with st.expander("View All of Today's Rates"):
        today_rates = tariff_df[tariff_df['date'] == today].copy()
        
        if not today_rates.empty:
            # Format for display
            today_rates['Time'] = today_rates['valid_from'].dt.strftime('%H:%M')
            today_rates['Rate (p/kWh)'] = today_rates['value_inc_vat'].round(2)
            
            # Select and rename columns for display
            display_df = today_rates[['Time', 'Rate (p/kWh)']].reset_index(drop=True)
            
            # Display as table
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No rates available for today.")
    
    # Add expandable section for tomorrow's rates
    tomorrow = (datetime.now(uk_tz) + timedelta(days=1)).date()
    
    with st.expander("View Tomorrow's Rates"):
        tomorrow_rates = tariff_df[tariff_df['date'] == tomorrow].copy()
        
        if not tomorrow_rates.empty:
            # Format for display
            tomorrow_rates['Time'] = tomorrow_rates['valid_from'].dt.strftime('%H:%M')
            tomorrow_rates['Rate (p/kWh)'] = tomorrow_rates['value_inc_vat'].round(2)
            
            # Select and rename columns for display
            display_df = tomorrow_rates[['Time', 'Rate (p/kWh)']].reset_index(drop=True)
            
            # Display as table
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("Rates for tomorrow are not yet available.")


def usage_page():
    """Display the electricity usage and cost page."""
    st.title("Electricity Usage and Cost History")
    
    # Check if required fields are provided
    if not st.session_state.api_key:
        st.warning("Please provide your Octopus Energy API key in the sidebar.")
        return
    
    if not st.session_state.mpan or not st.session_state.meter_serial:
        st.warning("Please provide your electricity meter MPAN and serial number in the sidebar.")
        return
    
    # Initialize API client
    api = OctopusEnergyAPI(api_key=st.session_state.api_key)
    
    # Use date range from sidebar
    default_days = st.session_state.default_days
    
    # Calculate date range based on default_days
    to_date = datetime.now()
    from_date = to_date - timedelta(days=default_days)
    
    # Display the selected date range
    st.info(f"Showing data from {from_date.strftime('%d %b %Y')} to {to_date.strftime('%d %b %Y')}")
    
    # Convert dates to datetime objects at start and end of day
    period_from = datetime.combine(from_date.date(), datetime.min.time())
    period_to = datetime.combine(to_date.date(), datetime.max.time())
    
    # Add a loading indicator
    with st.spinner("Fetching your electricity usage data..."):
        # Fetch consumption data
        consumption_df = api.get_consumption_data(
            mpan=st.session_state.mpan,
            serial_number=st.session_state.meter_serial,
            period_from=period_from,
            period_to=period_to
        )
    
    if consumption_df.empty:
        st.error("Failed to fetch consumption data. Please check your meter details and try again.")
        return
    
    # Initialize cost_df as empty DataFrame in case tariff fetch fails
    cost_df = pd.DataFrame()
    
    # Fetch tariff rates for the whole consumption period
    with st.spinner("Fetching historical tariff rates for cost calculation..."):
        # Use the same period as the consumption data to ensure we have rates for all usage
        tariff_df = api.get_agile_tariff_rates(
            period_from=period_from,
            period_to=period_to
        )
    
    if tariff_df.empty:
        st.error("Failed to fetch historical tariff rates. Cost calculations will not be available.")
    else:
        st.success(f"Successfully retrieved {len(tariff_df)} historical tariff rate records for cost calculation.")
        # Calculate costs
        cost_df = calculate_costs(
            consumption_df, 
            tariff_df, 
            standing_charge=st.session_state.standing_charge
        )
    
    # Create combined consumption and cost chart
    st.subheader("Electricity Consumption and Cost")
    combined_fig = create_combined_usage_cost_chart(consumption_df, cost_df)
    st.plotly_chart(combined_fig, use_container_width=True)
    
    # Display summary statistics
    if not cost_df.empty:
        st.subheader("Usage Summary")
        
        total_consumption = consumption_df['consumption'].sum()
        total_cost = cost_df['cost'].sum()
        total_standing_charge = cost_df['standing_charge'].sum()
        total_bill = total_cost + total_standing_charge
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Consumption", f"{total_consumption:.2f} kWh")
        
        with col2:
            st.metric("Usage Cost", f"£{total_cost:.2f}")
        
        with col3:
            st.metric("Standing Charges", f"£{total_standing_charge:.2f}")
        
        with col4:
            st.metric("Total Bill", f"£{total_bill:.2f}")
        
        # Display detailed data in an expandable section
        with st.expander("View Detailed Daily Data"):
            # Group by day
            daily_data = cost_df.groupby('date').agg({
                'consumption': 'sum',
                'cost': 'sum',
                'standing_charge': 'sum'
            }).reset_index()
            
            # Calculate total cost
            daily_data['total_cost'] = daily_data['cost'] + daily_data['standing_charge']
            
            # Format for display
            display_df = daily_data.copy()
            display_df['Date'] = display_df['date']
            display_df['Consumption (kWh)'] = display_df['consumption'].round(2)
            display_df['Usage Cost (£)'] = display_df['cost'].round(2)
            display_df['Standing Charge (£)'] = display_df['standing_charge'].round(2)
            display_df['Total Cost (£)'] = display_df['total_cost'].round(2)
            
            # Select columns for display
            display_df = display_df[[
                'Date', 
                'Consumption (kWh)', 
                'Usage Cost (£)', 
                'Standing Charge (£)', 
                'Total Cost (£)'
            ]]
            
            # Sort by date (most recent first)
            display_df = display_df.sort_values(by='Date', ascending=False)
            
            # Display as table
            st.dataframe(display_df, use_container_width=True)
    else:
        # If we have consumption data but no cost data
        st.subheader("Usage Summary")
        total_consumption = consumption_df['consumption'].sum()
        st.metric("Total Consumption", f"{total_consumption:.2f} kWh")
        st.warning("Cost data is not available. Unable to calculate costs without tariff information.")


def main():
    """Main app function."""
    # Display sidebar
    sidebar_inputs()
    
    # Display the active page
    if st.session_state.active_page == "Rates":
        rates_page()
    else:
        usage_page()


if __name__ == "__main__":
    main()
