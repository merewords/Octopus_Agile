-- =====================================================
-- Snowflake Deployment Script for Octopus Agile Dashboard
-- =====================================================
-- This script sets up the database, schema, stage, and Streamlit app
-- in Snowflake for the Octopus Energy Dashboard

-- Step 1: Create Database and Schema
-- =====================================================
CREATE DATABASE IF NOT EXISTS OCTOPUS_ENERGY;
USE DATABASE OCTOPUS_ENERGY;

CREATE SCHEMA IF NOT EXISTS APPS;
USE SCHEMA APPS;

-- Step 2: Create Warehouse (if not exists)
-- =====================================================
-- Adjust the warehouse size based on your needs
CREATE WAREHOUSE IF NOT EXISTS STREAMLIT_WH
  WITH WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 300
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

-- Step 3: Create Stage for Streamlit Files
-- =====================================================
CREATE STAGE IF NOT EXISTS STREAMLIT_STAGE
  DIRECTORY = ( ENABLE = TRUE )
  COMMENT = 'Stage for Octopus Energy Streamlit app files';

-- Step 4: Upload Application Files
-- =====================================================
-- Note: You need to upload files using SnowSQL or Snowsight UI
-- Example SnowSQL commands (run from your local terminal):
-- 
-- snowsql -c <connection_name> -q "PUT file:///workspaces/Octopus_Agile/streamlit_app.py @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
-- snowsql -c <connection_name> -q "PUT file:///workspaces/Octopus_Agile/octopus_api.py @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
-- snowsql -c <connection_name> -q "PUT file:///workspaces/Octopus_Agile/utils.py @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
-- snowsql -c <connection_name> -q "PUT file:///workspaces/Octopus_Agile/snowflake_cache.py @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
-- snowsql -c <connection_name> -q "PUT file:///workspaces/Octopus_Agile/environment.yml @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"

-- Verify uploaded files:
LIST @STREAMLIT_STAGE;

-- Step 5: Create the Streamlit Application
-- =====================================================
CREATE OR REPLACE STREAMLIT OCTOPUS_ENERGY.APPS.AGILE_DASHBOARD
  ROOT_LOCATION = '@OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE'
  MAIN_FILE = 'streamlit_app.py'
  QUERY_WAREHOUSE = 'STREAMLIT_WH'
  COMMENT = 'Octopus Energy Agile Dashboard - View tariff rates and track energy usage';

-- Step 6: Grant Permissions (Optional)
-- =====================================================
-- Grant usage to a specific role (adjust role name as needed)
-- GRANT USAGE ON DATABASE OCTOPUS_ENERGY TO ROLE <YOUR_ROLE>;
-- GRANT USAGE ON SCHEMA OCTOPUS_ENERGY.APPS TO ROLE <YOUR_ROLE>;
-- GRANT USAGE ON WAREHOUSE STREAMLIT_WH TO ROLE <YOUR_ROLE>;
-- GRANT USAGE ON STREAMLIT OCTOPUS_ENERGY.APPS.AGILE_DASHBOARD TO ROLE <YOUR_ROLE>;

-- Step 7: Configure Secrets
-- =====================================================
-- You need to configure secrets through Snowsight UI:
-- 1. Navigate to your Streamlit app in Snowsight
-- 2. Click on "Settings" or "Secrets"
-- 3. Add the following secrets:
--    OCTOPUS_API_KEY = "your-api-key"
--    MPAN_KEY = "your-mpan"
--    METER_KEY = "your-meter-serial"
--    GAS_MPRN = "your-gas-mprn"
--    GAS_METER_SERIAL = "your-gas-meter-serial"

-- Step 8: View the Streamlit App
-- =====================================================
-- Once deployed, you can access the app via:
-- https://<account>.snowflakecomputing.com/streamlit/OCTOPUS_ENERGY.APPS.AGILE_DASHBOARD

-- Optional: Create Tables for Caching (if using Snowflake caching)
-- =====================================================
-- These tables will be auto-created by the snowflake_cache.py module
-- but you can create them manually if preferred:

CREATE TABLE IF NOT EXISTS TARIFF_RATES_CACHE (
    valid_from TIMESTAMP_NTZ,
    valid_to TIMESTAMP_NTZ,
    value_inc_vat FLOAT,
    value_exc_vat FLOAT,
    cached_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (valid_from)
);

CREATE TABLE IF NOT EXISTS CONSUMPTION_CACHE (
    mpan VARCHAR,
    meter_serial VARCHAR,
    interval_start TIMESTAMP_NTZ,
    interval_end TIMESTAMP_NTZ,
    consumption FLOAT,
    cached_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (mpan, meter_serial, interval_start)
);

CREATE TABLE IF NOT EXISTS GAS_CONSUMPTION_CACHE (
    mprn VARCHAR,
    meter_serial VARCHAR,
    interval_start TIMESTAMP_NTZ,
    interval_end TIMESTAMP_NTZ,
    consumption FLOAT,
    cached_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (mprn, meter_serial, interval_start)
);

-- Optional: Create a Scheduled Task to Pre-warm Cache
-- =====================================================
-- This task can be scheduled to run periodically to keep the cache fresh
-- Uncomment and modify as needed:

-- CREATE OR REPLACE TASK REFRESH_TARIFF_CACHE
--   WAREHOUSE = STREAMLIT_WH
--   SCHEDULE = 'USING CRON 0 */6 * * * UTC'  -- Run every 6 hours
--   COMMENT = 'Refresh tariff rates cache'
-- AS
--   -- This would call a stored procedure that fetches and caches data
--   -- You would need to implement this stored procedure separately
--   -- CALL REFRESH_CACHE_PROCEDURE();
-- ;

-- SHOW TASKS;

-- To start the task:
-- ALTER TASK REFRESH_TARIFF_CACHE RESUME;
