import pandas as pd
from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go
import plotly.express as px

def calculate_costs(consumption_df, tariff_df, standing_charge=0.5):
    """
    Calculate electricity costs based on consumption data and tariff rates.
    
    Args:
        consumption_df: DataFrame containing consumption data
        tariff_df: DataFrame containing tariff rates
        standing_charge: Standing charge in pounds per day
        
    Returns:
        DataFrame with consumption data and calculated costs
    """
    if consumption_df.empty or tariff_df.empty:
        return pd.DataFrame()
    
    # Create a copy of the consumption DataFrame
    result_df = consumption_df.copy()
    
    # Merge rates into consumption data based on time periods
    result_df['cost'] = 0.0
    
    # For each consumption interval, find the matching tariff rate
    for idx, row in result_df.iterrows():
        interval_start = row['interval_start']
        
        # Find the corresponding tariff rate
        matching_rate = tariff_df[
            (tariff_df['valid_from'] <= interval_start) & 
            (tariff_df['valid_to'] > interval_start)
        ]
        
        if not matching_rate.empty:
            # Calculate cost: consumption (kWh) * rate (pence/kWh) / 100 (to convert to pounds)
            rate = matching_rate['value_inc_vat'].values[0]
            consumption = row['consumption']
            cost = (consumption * rate) / 100  # Convert pence to pounds
            result_df.at[idx, 'cost'] = cost
    
    # Add the standing charge
    # Group by date to add standing charge once per day
    daily_df = result_df.groupby('date').first().reset_index()
    
    # Create a mapping of dates to include the standing charge
    standing_charge_map = {date: standing_charge for date in daily_df['date']}
    
    # Add a column for the standing charge based on the date
    result_df['standing_charge'] = result_df['date'].map(standing_charge_map)
    
    # For dates where we've already added the standing charge, set to 0 for other entries
    result_df['standing_charge'] = result_df.groupby('date')['standing_charge'].transform(
        lambda x: pd.Series([x.iloc[0]] + [0] * (len(x) - 1), index=x.index)
    )
    
    # Calculate the total cost including standing charge
    result_df['total_cost'] = result_df['cost'] + result_df['standing_charge']
    
    return result_df

def create_rates_chart(tariff_df):
    """
    Create a chart to display tariff rates with highlighted cheapest slots.
    
    Args:
        tariff_df: DataFrame containing tariff rates
        
    Returns:
        Tuple of (Plotly figure, DataFrame of cheapest slots)
    """
    if tariff_df.empty:
        return go.Figure(), pd.DataFrame()

    # Get today's and tomorrow's dates in UK timezone
    uk_tz = pytz.timezone('Europe/London')
    now = datetime.now(uk_tz)
    today = now.date()
    tomorrow = (now + timedelta(days=1)).date()
    
    # Filter for today and tomorrow
    today_rates = tariff_df[tariff_df['date'] == today].copy()
    tomorrow_rates = tariff_df[tariff_df['date'] == tomorrow].copy()
    
    # Initialize cheapest_slots DataFrame
    cheapest_slots = pd.DataFrame()
    
    # Create time period masks for today's data
    if not today_rates.empty:
        # Define the valid time window (00:01 to 23:59)
        min_minutes = 1
        max_minutes = 23 * 60 + 59

        # Print the timezone information for debugging
        print(f"Using timezone: {today_rates['valid_from'].iloc[0].tzinfo}")

        # Build a single mask and get the 10 cheapest slots overall for today
        today_rates['minute_of_day'] = (
            today_rates['valid_from'].dt.hour * 60 + today_rates['valid_from'].dt.minute
        )
        valid_mask = (today_rates['minute_of_day'] >= min_minutes) & (
            today_rates['minute_of_day'] <= max_minutes
        )

        cheapest_slots = today_rates[valid_mask].nsmallest(10, 'value_inc_vat').copy()
        cheapest_slots['period'] = '30 min'
    
    # Create marker colors based on time periods
    marker_colors = []
    if not today_rates.empty:
        for _, row in today_rates.iterrows():
            if row['valid_from'] in cheapest_slots['valid_from'].values:
                marker_colors.append('green')
            else:
                marker_colors.append('blue')
    
    fig = go.Figure()
    
    # Add today's rates
    if not today_rates.empty:
        fig.add_trace(go.Scatter(
            x=today_rates['valid_from'],
            y=today_rates['value_inc_vat'],
            mode='lines+markers',
            name="Today's Rates",
            line=dict(color='blue'),
            marker=dict(
                size=10,
                color=marker_colors,
                symbol=today_rates.apply(
                    lambda row: 'star' if row['valid_from'] in cheapest_slots['valid_from'].values else 'circle', 
                    axis=1
                )
            ),
            hovertemplate='%{x|%H:%M}: %{y:.2f}p/kWh<extra></extra>'
        ))
    
    # Add tomorrow's rates
    if not tomorrow_rates.empty:
        fig.add_trace(go.Scatter(
            x=tomorrow_rates['valid_from'],
            y=tomorrow_rates['value_inc_vat'],
            mode='lines+markers',
            name="Tomorrow's Rates",
            line=dict(color='green', dash='dash'),
            hovertemplate='%{x|%H:%M}: %{y:.2f}p/kWh<extra></extra>'
        ))
    
    # Add a vertical line for current time using a shape
    fig.add_shape(
        type="line",
        x0=now,
        x1=now,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(
            color="red",
            width=2,
            dash="solid",
        )
    )
    
    # Add annotation for current time
    fig.add_annotation(
        x=now,
        y=1,
        yref="paper",
        text="Current Time",
        showarrow=False,
        font=dict(
            color="red",
            size=12
        ),
        align="center"
    )
    
    # Configure the layout
    fig.update_layout(
        title='Octopus Agile Half-Hour Electricity Rates (Cheapest Slots Highlighted as Stars)',
        xaxis_title='Time',
        yaxis_title='Price (p/kWh)',
        #legend_title='Period',
        hovermode='x unified',
        height=600,
        showlegend=False
    )
    
    # Format x-axis to show time without date
    fig.update_xaxes(
        tickformat='%H:%M',
        tickangle=-45,
        title_font=dict(size=14),
        tickfont=dict(size=12),
    )
    
    # Format y-axis
    fig.update_yaxes(
        title_font=dict(size=14),
        tickfont=dict(size=12),
        ticksuffix='p'
    )
    
    # Format cheapest slots for display
    if not cheapest_slots.empty:
        cheapest_slots['time'] = cheapest_slots['valid_from'].dt.strftime('%H:%M')
        cheapest_slots = cheapest_slots.sort_values(by=['period', 'value_inc_vat'])
    
    return fig, cheapest_slots

def create_combined_usage_cost_chart(consumption_df, cost_df=None):
    """
    Create a combined chart to display consumption data and costs.
    
    Args:
        consumption_df: DataFrame containing consumption data
        cost_df: DataFrame containing cost data (optional)
        
    Returns:
        Plotly figure object
    """
    if consumption_df.empty:
        return go.Figure()
    
    # Group by day for daily consumption
    daily_consumption = consumption_df.groupby('date')['consumption'].sum().reset_index()
    
    fig = go.Figure()
    
    # Add consumption bars
    fig.add_trace(go.Bar(
        x=daily_consumption['date'],
        y=daily_consumption['consumption'],
        name='Consumption (kWh)',
        marker_color='skyblue',
        hovertemplate='Date: %{x}<br>Consumption: %{y:.2f} kWh<extra></extra>'
    ))
    
    # Add cost line if cost data is available
    if cost_df is not None and not cost_df.empty:
        # Group by day for daily costs
        daily_usage_cost = cost_df.groupby('date')['cost'].sum().reset_index()
        daily_standing_charge = cost_df.groupby('date')['standing_charge'].sum().reset_index()
        
        # Merge the two dataframes
        daily_costs = pd.merge(daily_usage_cost, daily_standing_charge, on='date')
        
        # Calculate total cost (usage + standing charge)
        daily_costs['total_cost'] = daily_costs['cost'] + daily_costs['standing_charge']
        
        # Add total cost line
        fig.add_trace(go.Scatter(
            x=daily_costs['date'],
            y=daily_costs['total_cost'],
            mode='lines+markers',
            name='Total Cost (£)',
            line=dict(color='red', width=3),
            marker=dict(size=8),
            hovertemplate='Date: %{x}<br>Total Cost: £%{y:.2f}<extra></extra>',
            yaxis='y2'  # Use secondary y-axis
        ))
        
        # Add cost annotation for each point
        for i, row in daily_costs.iterrows():
            fig.add_annotation(
                x=row['date'],
                y=row['total_cost'],
                text=f"£{row['total_cost']:.2f}",
                yshift=10,
                showarrow=False,
                font=dict(size=10, color="red"),
                yref='y2'
            )
    
    # Configure the layout with dual y-axes
    fig.update_layout(
        title='Daily Electricity Consumption and Cost',
        xaxis_title='Date',
        yaxis=dict(
            title=dict(
                text='Consumption (kWh)',
                font=dict(color='skyblue')
            ),
            tickfont=dict(color='skyblue')
        ),
        yaxis2=dict(
            title=dict(
                text='Cost (£)',
                font=dict(color='red')
            ),
            tickfont=dict(color='red'),
            anchor="x",
            overlaying="y",
            side="right",
            tickprefix='£'
        ),
        #legend=dict(
         #   orientation="h",
          #  yanchor="bottom",
           # y=1.02,
            #xanchor="center",
            #x=0.5
        #),
        hovermode='x unified',
        height=600,
        margin=dict(t=100),
        showlegend=False
    )
    
    # Format x-axis
    fig.update_xaxes(
        tickangle=-45,
        title_font=dict(size=14),
        tickfont=dict(size=12),
    )
    
    return fig

# Keep these functions for backward compatibility
def create_consumption_chart(consumption_df):
    """Create a chart to display consumption data. For backward compatibility."""
    return create_combined_usage_cost_chart(consumption_df)

def create_cost_chart(cost_df):
    """Create a chart to display cost data. For backward compatibility."""
    if cost_df.empty:
        return go.Figure()
    
    # Group by day for daily costs
    daily_usage_cost = cost_df.groupby('date')['cost'].sum().reset_index()
    daily_standing_charge = cost_df.groupby('date')['standing_charge'].sum().reset_index()
    
    # Merge the two dataframes
    daily_costs = pd.merge(daily_usage_cost, daily_standing_charge, on='date')
    
    # Create figure
    fig = go.Figure()
    
    # Add usage cost bars
    fig.add_trace(go.Bar(
        x=daily_costs['date'],
        y=daily_costs['cost'],
        name='Usage Cost',
        marker_color='blue',
        hovertemplate='Date: %{x}<br>Usage Cost: £%{y:.2f}<extra></extra>'
    ))
    
    # Add standing charge bars
    fig.add_trace(go.Bar(
        x=daily_costs['date'],
        y=daily_costs['standing_charge'],
        name='Standing Charge',
        marker_color='orange',
        hovertemplate='Date: %{x}<br>Standing Charge: £%{y:.2f}<extra></extra>'
    ))
    
    # Configure the layout for stacked bars
    fig.update_layout(
        title='Daily Electricity Costs',
        xaxis_title='Date',
        yaxis_title='Cost (£)',
        barmode='stack',
        hovermode='x unified',
        height=500,
        showlegend=False
    )
    
    # Format axis
    fig.update_xaxes(
        tickangle=-45,
        title_font=dict(size=14),
        tickfont=dict(size=12),
    )
    
    fig.update_yaxes(
        tickprefix='£',
        title_font=dict(size=14),
        tickfont=dict(size=12),
    )
    
    return fig
