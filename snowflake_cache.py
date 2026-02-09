"""
Snowflake caching utilities for Octopus Energy data.
This module provides functions to cache API responses in Snowflake tables
for faster access and reduced API calls.
"""

import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
from typing import Optional

# Only import Snowflake when available (won't work locally without connection)
try:
    from snowflake.snowpark.context import get_active_session
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False


class SnowflakeCache:
    """Handle caching of Octopus Energy data in Snowflake tables."""
    
    def __init__(self):
        """Initialize the cache handler."""
        if SNOWFLAKE_AVAILABLE:
            try:
                self.session = get_active_session()
                self.enabled = True
            except:
                self.session = None
                self.enabled = False
        else:
            self.session = None
            self.enabled = False
    
    def _ensure_tables_exist(self):
        """Create cache tables if they don't exist."""
        if not self.enabled:
            return
        
        # Create tariff rates cache table
        self.session.sql("""
            CREATE TABLE IF NOT EXISTS TARIFF_RATES_CACHE (
                valid_from TIMESTAMP_NTZ,
                valid_to TIMESTAMP_NTZ,
                value_inc_vat FLOAT,
                value_exc_vat FLOAT,
                cached_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                PRIMARY KEY (valid_from)
            )
        """).collect()
        
        # Create consumption cache table
        self.session.sql("""
            CREATE TABLE IF NOT EXISTS CONSUMPTION_CACHE (
                mpan VARCHAR,
                meter_serial VARCHAR,
                interval_start TIMESTAMP_NTZ,
                interval_end TIMESTAMP_NTZ,
                consumption FLOAT,
                cached_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                PRIMARY KEY (mpan, meter_serial, interval_start)
            )
        """).collect()
        
        # Create gas consumption cache table
        self.session.sql("""
            CREATE TABLE IF NOT EXISTS GAS_CONSUMPTION_CACHE (
                mprn VARCHAR,
                meter_serial VARCHAR,
                interval_start TIMESTAMP_NTZ,
                interval_end TIMESTAMP_NTZ,
                consumption FLOAT,
                cached_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                PRIMARY KEY (mprn, meter_serial, interval_start)
            )
        """).collect()
    
    def get_cached_tariff_rates(self, hours_old: int = 24) -> Optional[pd.DataFrame]:
        """
        Retrieve cached tariff rates if they're recent enough.
        
        Args:
            hours_old: Maximum age of cached data in hours
            
        Returns:
            DataFrame of cached rates or None if cache is stale/empty
        """
        if not self.enabled:
            return None
        
        try:
            self._ensure_tables_exist()
            
            # Get cached data that's not too old
            cutoff = datetime.now() - timedelta(hours=hours_old)
            
            result = self.session.sql(f"""
                SELECT valid_from, valid_to, value_inc_vat, value_exc_vat
                FROM TARIFF_RATES_CACHE
                WHERE cached_at >= '{cutoff.strftime('%Y-%m-%d %H:%M:%S')}'
                ORDER BY valid_from
            """).to_pandas()
            
            if not result.empty:
                # Convert timestamp columns
                result['valid_from'] = pd.to_datetime(result['valid_from'], utc=True)
                result['valid_to'] = pd.to_datetime(result['valid_to'], utc=True)
                return result
            
        except Exception as e:
            st.warning(f"Cache retrieval failed: {e}")
        
        return None
    
    def cache_tariff_rates(self, df: pd.DataFrame):
        """
        Store tariff rates in Snowflake cache.
        
        Args:
            df: DataFrame containing tariff rates
        """
        if not self.enabled or df.empty:
            return
        
        try:
            self._ensure_tables_exist()
            
            # Prepare data for insertion
            cache_df = df[['valid_from', 'valid_to', 'value_inc_vat', 'value_exc_vat']].copy()
            
            # Convert timestamps to timezone-naive for Snowflake
            cache_df['valid_from'] = pd.to_datetime(cache_df['valid_from']).dt.tz_localize(None)
            cache_df['valid_to'] = pd.to_datetime(cache_df['valid_to']).dt.tz_localize(None)
            
            # Clear old cache and insert new data
            self.session.sql("DELETE FROM TARIFF_RATES_CACHE").collect()
            
            # Write to Snowflake
            self.session.write_pandas(
                cache_df,
                table_name="TARIFF_RATES_CACHE",
                auto_create_table=False,
                overwrite=False
            )
            
        except Exception as e:
            st.warning(f"Cache storage failed: {e}")
    
    def get_cached_consumption(
        self, 
        mpan: str, 
        meter_serial: str, 
        days_old: int = 1
    ) -> Optional[pd.DataFrame]:
        """
        Retrieve cached consumption data.
        
        Args:
            mpan: Meter Point Administration Number
            meter_serial: Meter serial number
            days_old: Maximum age of cached data in days
            
        Returns:
            DataFrame of cached consumption or None
        """
        if not self.enabled:
            return None
        
        try:
            self._ensure_tables_exist()
            
            cutoff = datetime.now() - timedelta(days=days_old)
            
            result = self.session.sql(f"""
                SELECT interval_start, interval_end, consumption
                FROM CONSUMPTION_CACHE
                WHERE mpan = '{mpan}'
                  AND meter_serial = '{meter_serial}'
                  AND cached_at >= '{cutoff.strftime('%Y-%m-%d %H:%M:%S')}'
                ORDER BY interval_start
            """).to_pandas()
            
            if not result.empty:
                result['interval_start'] = pd.to_datetime(result['interval_start'], utc=True)
                result['interval_end'] = pd.to_datetime(result['interval_end'], utc=True)
                return result
            
        except Exception as e:
            st.warning(f"Consumption cache retrieval failed: {e}")
        
        return None
    
    def cache_consumption(self, df: pd.DataFrame, mpan: str, meter_serial: str):
        """
        Store consumption data in Snowflake cache.
        
        Args:
            df: DataFrame containing consumption data
            mpan: Meter Point Administration Number
            meter_serial: Meter serial number
        """
        if not self.enabled or df.empty:
            return
        
        try:
            self._ensure_tables_exist()
            
            # Prepare data
            cache_df = df[['interval_start', 'interval_end', 'consumption']].copy()
            cache_df['mpan'] = mpan
            cache_df['meter_serial'] = meter_serial
            
            # Convert timestamps
            cache_df['interval_start'] = pd.to_datetime(cache_df['interval_start']).dt.tz_localize(None)
            cache_df['interval_end'] = pd.to_datetime(cache_df['interval_end']).dt.tz_localize(None)
            
            # Delete existing entries for this meter and time range
            min_time = cache_df['interval_start'].min()
            max_time = cache_df['interval_start'].max()
            
            self.session.sql(f"""
                DELETE FROM CONSUMPTION_CACHE
                WHERE mpan = '{mpan}'
                  AND meter_serial = '{meter_serial}'
                  AND interval_start BETWEEN '{min_time}' AND '{max_time}'
            """).collect()
            
            # Insert new data
            self.session.write_pandas(
                cache_df[['mpan', 'meter_serial', 'interval_start', 'interval_end', 'consumption']],
                table_name="CONSUMPTION_CACHE",
                auto_create_table=False,
                overwrite=False
            )
            
        except Exception as e:
            st.warning(f"Consumption cache storage failed: {e}")
    
    def get_cached_gas_consumption(
        self, 
        mprn: str, 
        meter_serial: str, 
        days_old: int = 1
    ) -> Optional[pd.DataFrame]:
        """
        Retrieve cached gas consumption data.
        
        Args:
            mprn: Meter Point Reference Number
            meter_serial: Gas meter serial number
            days_old: Maximum age of cached data in days
            
        Returns:
            DataFrame of cached gas consumption or None
        """
        if not self.enabled:
            return None
        
        try:
            self._ensure_tables_exist()
            
            cutoff = datetime.now() - timedelta(days=days_old)
            
            result = self.session.sql(f"""
                SELECT interval_start, interval_end, consumption
                FROM GAS_CONSUMPTION_CACHE
                WHERE mprn = '{mprn}'
                  AND meter_serial = '{meter_serial}'
                  AND cached_at >= '{cutoff.strftime('%Y-%m-%d %H:%M:%S')}'
                ORDER BY interval_start
            """).to_pandas()
            
            if not result.empty:
                result['interval_start'] = pd.to_datetime(result['interval_start'], utc=True)
                result['interval_end'] = pd.to_datetime(result['interval_end'], utc=True)
                return result
            
        except Exception as e:
            st.warning(f"Gas consumption cache retrieval failed: {e}")
        
        return None
    
    def cache_gas_consumption(self, df: pd.DataFrame, mprn: str, meter_serial: str):
        """
        Store gas consumption data in Snowflake cache.
        
        Args:
            df: DataFrame containing gas consumption data
            mprn: Meter Point Reference Number
            meter_serial: Gas meter serial number
        """
        if not self.enabled or df.empty:
            return
        
        try:
            self._ensure_tables_exist()
            
            # Prepare data
            cache_df = df[['interval_start', 'interval_end', 'consumption']].copy()
            cache_df['mprn'] = mprn
            cache_df['meter_serial'] = meter_serial
            
            # Convert timestamps
            cache_df['interval_start'] = pd.to_datetime(cache_df['interval_start']).dt.tz_localize(None)
            cache_df['interval_end'] = pd.to_datetime(cache_df['interval_end']).dt.tz_localize(None)
            
            # Delete existing entries for this meter and time range
            min_time = cache_df['interval_start'].min()
            max_time = cache_df['interval_start'].max()
            
            self.session.sql(f"""
                DELETE FROM GAS_CONSUMPTION_CACHE
                WHERE mprn = '{mprn}'
                  AND meter_serial = '{meter_serial}'
                  AND interval_start BETWEEN '{min_time}' AND '{max_time}'
            """).collect()
            
            # Insert new data
            self.session.write_pandas(
                cache_df[['mprn', 'meter_serial', 'interval_start', 'interval_end', 'consumption']],
                table_name="GAS_CONSUMPTION_CACHE",
                auto_create_table=False,
                overwrite=False
            )
            
        except Exception as e:
            st.warning(f"Gas consumption cache storage failed: {e}")


# Optional: Add cache warming function
def warm_cache_on_schedule():
    """
    Function to be called by Snowflake Task to pre-populate cache.
    This can be scheduled to run periodically (e.g., every hour).
    """
    cache = SnowflakeCache()
    if not cache.enabled:
        return
    
    # This would be called by a Snowflake Task
    # Example: Fetch latest tariff rates and cache them
    # You would need to implement the actual API call logic here
    pass
