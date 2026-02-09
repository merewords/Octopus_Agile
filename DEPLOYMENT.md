# Snowflake Deployment Guide for Octopus Agile Dashboard

This guide provides step-by-step instructions for deploying the Octopus Energy Dashboard to Snowflake.

## Prerequisites

Before deploying, ensure you have:

1. **Snowflake Account** - An active account with appropriate permissions
2. **SnowSQL** - Snowflake's command-line client ([Installation Guide](https://docs.snowflake.com/en/user-guide/snowsql-install-config))
3. **API Credentials** - Your Octopus Energy API key and meter details

## Deployment Options

You can deploy using either:
- **Option A**: Automated deployment script (recommended)
- **Option B**: Manual deployment via SQL and SnowSQL commands

---

## Option A: Automated Deployment (Recommended)

### Step 1: Configure Connection

Edit the `deploy.sh` script and set your Snowflake connection details:

```bash
SNOWFLAKE_ACCOUNT="your-account-identifier"
SNOWFLAKE_USER="your-username"
SNOWFLAKE_ROLE="ACCOUNTADMIN"  # Or your preferred role
SNOWFLAKE_WAREHOUSE="STREAMLIT_WH"
CONNECTION_NAME=""  # Optional: SnowSQL connection name
```

Or configure a SnowSQL connection in `~/.snowsql/config`:

```ini
[connections.octopus]
accountname = your-account
username = your-username
rolename = ACCOUNTADMIN
warehousename = STREAMLIT_WH
```

### Step 2: Make Script Executable

```bash
chmod +x deploy.sh
```

### Step 3: Run Deployment

```bash
./deploy.sh
```

The script will:
- ✅ Validate all required files exist
- ✅ Upload files to Snowflake stage
- ✅ Create database, schema, and stage
- ✅ Deploy the Streamlit app
- ✅ Provide next steps for configuration

### Step 4: Configure Secrets

After deployment, configure your API credentials:

1. Navigate to your Streamlit app in Snowsight
2. Click **Settings** → **Secrets**
3. Add the following secrets:

```toml
OCTOPUS_API_KEY = "sk_live_xxxxxxxxxxxxx"
MPAN_KEY = "1234567890123"
METER_KEY = "E1S12345678910"
GAS_MPRN = "9876543210"
GAS_METER_SERIAL = "G4S0987654321"
```

### Step 5: Access Your App

Your app will be available at:
```
https://<account>.snowflakecomputing.com/streamlit/OCTOPUS_ENERGY.APPS.AGILE_DASHBOARD
```

---

## Option B: Manual Deployment

### Step 1: Install SnowSQL

**For Linux (including dev containers):**

```bash
# Download the installer
curl -O https://sfc-repo.snowflakecomputing.com/snowsql/bootstrap/1.2/linux_x86_64/snowsql-1.2.32-linux_x86_64.bash

# Make it executable and run
chmod +x snowsql-1.2.32-linux_x86_64.bash
bash snowsql-1.2.32-linux_x86_64.bash

# Add to PATH permanently
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
snowsql --version
```

**For other operating systems:** See the [Snowflake documentation](https://docs.snowflake.com/en/user-guide/snowsql-install-config).

### Step 2: Create Infrastructure

Execute the SQL commands in `deploy_to_snowflake.sql`:

```bash
snowsql -c <connection_name> -f deploy_to_snowflake.sql
```

Or execute manually in Snowsight:

```sql
CREATE DATABASE IF NOT EXISTS OCTOPUS_ENERGY;
CREATE SCHEMA IF NOT EXISTS APPS;
CREATE WAREHOUSE IF NOT EXISTS STREAMLIT_WH
  WITH WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 300
  AUTO_RESUME = TRUE;
CREATE STAGE IF NOT EXISTS STREAMLIT_STAGE;
```

### Step 3: Upload Application Files

Upload each file using SnowSQL PUT commands:

```bash
# Navigate to project directory
cd /workspaces/Octopus_Agile

# Upload files
snowsql -c <connection_name> -q "PUT file://streamlit_app.py @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
snowsql -c <connection_name> -q "PUT file://octopus_api.py @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
snowsql -c <connection_name> -q "PUT file://utils.py @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
snowsql -c <connection_name> -q "PUT file://snowflake_cache.py @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
snowsql -c <connection_name> -q "PUT file://environment.yml @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
```

### Step 4: Verify Upload

```sql
LIST @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE;
```

You should see all 5 files listed.

### Step 5: Create Streamlit App

```sql
CREATE OR REPLACE STREAMLIT OCTOPUS_ENERGY.APPS.AGILE_DASHBOARD
  ROOT_LOCATION = '@OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE'
  MAIN_FILE = 'streamlit_app.py'
  QUERY_WAREHOUSE = 'STREAMLIT_WH';
```

### Step 6: Configure Secrets

Follow the same process as Option A, Step 4.

---

## Updating the App

### Update Application Code

When you make changes to the application:

1. **Upload updated files:**

```bash
./deploy.sh --update
```

Or manually:

```bash
snowsql -c <connection_name> -q "PUT file://streamlit_app.py @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
```

2. **Refresh the app** in your browser (Ctrl+R or Cmd+R)

### Update Dependencies

If you modify `environment.yml`:

1. Upload the new file
2. Recreate the Streamlit app (it will rebuild the environment)

```sql
CREATE OR REPLACE STREAMLIT OCTOPUS_ENERGY.APPS.AGILE_DASHBOARD
  ROOT_LOCATION = '@OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE'
  MAIN_FILE = 'streamlit_app.py'
  QUERY_WAREHOUSE = 'STREAMLIT_WH';
```

---

## Snowflake Caching (Optional)

The app includes optional Snowflake table caching for improved performance.

### Enable Caching

1. The cache tables are auto-created on first use
2. To manually create tables, see `deploy_to_snowflake.sql` (Step 8)

### Cache Benefits

- **Faster load times** - Reduces API calls to Octopus Energy
- **Historical data** - Preserves data even if API limits are reached
- **Cost savings** - Fewer external API calls

### Cache Configuration

By default, caching is enabled. To disable:

```python
# In streamlit_app.py, set:
USE_SNOWFLAKE_CACHE = False
```

---

## Troubleshooting

### Issue: "Streamlit app not found"

**Solution:** Verify the app was created:
```sql
SHOW STREAMLIT IN SCHEMA OCTOPUS_ENERGY.APPS;
```

### Issue: "Permission denied"

**Solution:** Grant necessary permissions:
```sql
GRANT USAGE ON DATABASE OCTOPUS_ENERGY TO ROLE <YOUR_ROLE>;
GRANT USAGE ON SCHEMA OCTOPUS_ENERGY.APPS TO ROLE <YOUR_ROLE>;
GRANT USAGE ON WAREHOUSE STREAMLIT_WH TO ROLE <YOUR_ROLE>;
```

### Issue: "Package import errors"

**Solution:** Verify `environment.yml` is uploaded and valid:
```sql
LIST @OCTOPUS_ENERGY.APPS.STREAMLIT_STAGE PATTERN='.*environment.yml';
```

### Issue: "API key not working"

**Solution:** 
1. Verify secrets are configured correctly in Snowsight
2. Check secret names match exactly (case-sensitive)
3. Ensure no extra whitespace in secret values

### Issue: "Data not loading"

**Solution:**
1. Check warehouse is running: `SHOW WAREHOUSES LIKE 'STREAMLIT_WH';`
2. Verify API credentials in secrets
3. Check browser console for errors
4. Review Streamlit app logs in Snowsight

---

## Cost Optimization

### Warehouse Sizing

The default `XSMALL` warehouse is sufficient for this app:
- Cost: ~$2/hour (when running)
- Auto-suspends after 5 minutes of inactivity
- Auto-resumes when app is accessed

### Further Optimization

1. **Enable caching** to reduce API calls
2. **Adjust auto-suspend** time if needed:
```sql
ALTER WAREHOUSE STREAMLIT_WH SET AUTO_SUSPEND = 60;  -- 1 minute
```

3. **Monitor usage:**
```sql
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE WAREHOUSE_NAME = 'STREAMLIT_WH'
ORDER BY START_TIME DESC
LIMIT 10;
```

---

## Support & Resources

- **Snowflake Streamlit Docs**: https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit
- **Octopus Energy API**: https://developer.octopus.energy/docs/api/
- **Repository Issues**: https://github.com/cchderek/Octopus_Agile/issues

---

## Next Steps

After successful deployment:

1. ✅ Verify app loads in browser
2. ✅ Configure all secrets
3. ✅ Test tariff rates page
4. ✅ Test electricity usage page
5. ✅ Test gas usage page
6. ✅ Share app URL with team members
7. ✅ Set up monitoring/alerts (optional)

Enjoy your Snowflake-hosted Octopus Energy Dashboard! 🐙❄️
