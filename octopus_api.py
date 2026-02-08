import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

class OctopusEnergyAPI:
    """Class to interact with the Octopus Energy API."""
    
    BASE_URL = "https://api.octopus.energy/v1"
    
    def __init__(self, api_key=None):
        """Initialize the API wrapper with an API key."""
        self.api_key = api_key
        self.auth = (api_key, "") if api_key else None
    
    def get_agile_tariff_rates(self, tariff_code="E-1R-AGILE-24-10-01-C", product_code="AGILE-24-10-01", 
                             period_from=None, period_to=None):
        """
        Fetch Agile tariff rates for a specified period.
        
        Args:
            tariff_code: The specific tariff code to fetch rates for
            product_code: The product code for the Agile tariff
            period_from: Start date (defaults to today)
            period_to: End date (defaults to tomorrow)
            
        Returns:
            DataFrame containing the tariff rates with timestamps
        """
        try:
            # Calculate the date range if not provided
            uk_tz = pytz.timezone('Europe/London')
            now = datetime.now(uk_tz)
            
            if period_from is None:
                # Default to today at 00:00
                period_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
                
            if period_to is None:
                # Default to 2 days from now
                if isinstance(period_from, datetime):
                    period_to = period_from + timedelta(days=2)
                else:
                    # If period_from is a date, convert to datetime
                    period_from = datetime.combine(period_from, datetime.min.time())
                    period_to = period_from + timedelta(days=2)
            
            # Format dates for the API
            period_from_str = period_from.strftime("%Y-%m-%dT%H:%M:%SZ")
            period_to_str = period_to.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            print(f"Fetching tariff rates from {period_from_str} to {period_to_str}")
            
            # Construct the API URL
            url = f"{self.BASE_URL}/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/"
            
            # Add query parameters for the date range
            params = {
                "period_from": period_from_str,
                "period_to": period_to_str,
                "page_size": 1500,  # Request more rates at once
            }
            
            # Make the API request
            response = requests.get(url, params=params, auth=self.auth)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            rates = data.get("results", [])
            
            # Check if we need to get more pages
            next_url = data.get("next")
            while next_url:
                print(f"Fetching next page of tariff rates...")
                response = requests.get(next_url, auth=self.auth)
                response.raise_for_status()
                data = response.json()
                rates.extend(data.get("results", []))
                next_url = data.get("next")
            
            if not rates:
                print("No tariff rates found for the specified period.")
                return pd.DataFrame()
            
            # Convert to pandas DataFrame
            df = pd.DataFrame(rates)
            
            print(f"Retrieved {len(df)} tariff rate records")
            
            # Convert timestamps to datetime objects with UTC timezone
            df["valid_from"] = pd.to_datetime(df["valid_from"], utc=True)
            df["valid_to"] = pd.to_datetime(df["valid_to"], utc=True)
            
            # Convert to UK local time (handles BST/GMT automatically)
            uk_tz = pytz.timezone('Europe/London')
            df["valid_from"] = df["valid_from"].dt.tz_convert(uk_tz)
            df["valid_to"] = df["valid_to"].dt.tz_convert(uk_tz)
            
            # Add a day column for filtering based on UK time
            df["date"] = df["valid_from"].dt.date
            
            # Add a time column for display
            df["time"] = df["valid_from"].dt.strftime("%H:%M")
            
            # Convert value_inc_vat to numeric
            df["value_inc_vat"] = pd.to_numeric(df["value_inc_vat"])
            
            # Sort by valid_from
            df = df.sort_values("valid_from")
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching tariff rates: {e}")
            return pd.DataFrame()

    def get_consumption_data(self, mpan, serial_number, period_from=None, period_to=None):
        """
        Fetch consumption data for a specific meter.
        
        Args:
            mpan: Meter Point Administration Number
            serial_number: Meter serial number
            period_from: Start date (defaults to 30 days ago)
            period_to: End date (defaults to today)
            
        Returns:
            DataFrame containing consumption data
        """
        try:
            # Set default period (last 30 days) if not provided
            if not period_from or not period_to:
                uk_tz = pytz.timezone('Europe/London')
                now = datetime.now(uk_tz)
                
                if not period_to:
                    period_to = now
                
                if not period_from:
                    period_from = now - timedelta(days=30)
            
            # Format dates for the API
            period_from_str = period_from.strftime("%Y-%m-%dT%H:%M:%SZ")
            period_to_str = period_to.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Construct the API URL
            url = f"{self.BASE_URL}/electricity-meter-points/{mpan}/meters/{serial_number}/consumption/"
            
            # Add query parameters
            params = {
                "period_from": period_from_str,
                "period_to": period_to_str,
                "page_size": 5000,  # Request a large page size to get all data
            }
            
            # Make the API request
            response = requests.get(url, params=params, auth=self.auth)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            consumption = data.get("results", [])
            
            if not consumption:
                return pd.DataFrame()
            
            # Convert to pandas DataFrame
            df = pd.DataFrame(consumption)
            
            # Convert timestamps to datetime objects with UTC timezone
            df["interval_start"] = pd.to_datetime(df["interval_start"], utc=True)
            df["interval_end"] = pd.to_datetime(df["interval_end"], utc=True)
            
            # Convert to UK local time (handles BST/GMT automatically)
            uk_tz = pytz.timezone('Europe/London')
            df["interval_start"] = df["interval_start"].dt.tz_convert(uk_tz)
            df["interval_end"] = df["interval_end"].dt.tz_convert(uk_tz)
            
            # Add date and time columns based on UK time
            df["date"] = df["interval_start"].dt.date
            df["time"] = df["interval_start"].dt.strftime("%H:%M")
            # Also add hour column for time period analysis
            df["hour"] = df["interval_start"].dt.hour
            
            # Sort by interval_start
            df = df.sort_values("interval_start")
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching consumption data: {e}")
            return pd.DataFrame()
