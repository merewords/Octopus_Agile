# Azure Web App Deployment Guide

Complete guide for deploying the Octopus Agile Dashboard to Azure Web App using Azure DevOps Pipelines.

## Prerequisites

1. **Azure Subscription** - Active Azure account
2. **Azure DevOps Organization** - With access to create pipelines
3. **GitHub Repository** - Your code (already set up: cchderek/Octopus_Agile)
4. **API Credentials** - Octopus Energy API key and meter details

---

## Deployment Methods

### Method 1: Azure DevOps Pipeline (Recommended - Automated)

#### Step 1: Create Azure Resources

**Option A: Using Azure Portal**

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **Create a resource** → **Web App**
3. Configure:
   - **Name**: `octopus-agile` (or your preferred name)
   - **Publish**: Code
   - **Runtime stack**: Python 3.11
   - **Operating System**: Linux
   - **Region**: UK South (or nearest)
   - **Pricing**: B1 (Basic) or higher
4. Click **Review + Create** → **Create**

**Option B: Using ARM Template (Automated)**

```bash
# From your local machine or Azure Cloud Shell
az group create --name octopus-agile-rg --location uksouth

az deployment group create \
  --resource-group octopus-agile-rg \
  --template-file .azure/arm-template.json \
  --parameters webAppName=octopus-agile
```

#### Step 2: Configure Azure DevOps

1. **Import Repository** (if not already done):
   - Go to Azure DevOps → Repos
   - Import from GitHub: `cchderek/Octopus_Agile`

2. **Create Service Connection**:
   - Azure DevOps → Project Settings → Service connections
   - Click **New service connection** → **Azure Resource Manager**
   - Choose **Service principal (automatic)**
   - Select your subscription and resource group
   - Name it: `octopus-agile-conn` (must match azure-pipelines.yml)
   - Click **Save**

3. **Create Environment**:
   - Azure DevOps → Pipelines → Environments
   - Click **New environment**
   - Name: `octopus-agile`
   - Resource: None (manual approval optional)
   - Click **Create**

#### Step 3: Create Pipeline

1. Azure DevOps → Pipelines → **New Pipeline**
2. Select **GitHub** (or Azure Repos if imported)
3. Choose repository: `cchderek/Octopus_Agile`
4. Select **Existing Azure Pipelines YAML file**
5. Choose `/azure-pipelines.yml`
6. Click **Run**

The pipeline will automatically:
- ✅ Install dependencies
- ✅ Build the application
- ✅ Deploy to Azure Web App

#### Step 4: Configure Web App Settings

After deployment, configure the startup command and API credentials:

**Via Azure Portal:**

1. Navigate to your Web App: `octopus-agile`

2. **Set Startup Command**:
   - Go to **Configuration** → **General settings**
   - Set **Startup Command**: `startup.sh`
   - Click **Save**

3. **Add Application Settings**:
   - Go to **Configuration** → **Application settings**
   - Click **+ New application setting** for each:

```
OCTOPUS_API_KEY = your-octopus-api-key
MPAN_KEY = your-mpan
METER_KEY = your-meter-serial
GAS_MPRN = your-gas-mprn
GAS_METER_SERIAL = your-gas-meter-serial
WEBSITES_PORT = 8000
```

4. Click **Save** → **Continue**

**Via Azure CLI:**

```bash
# Set startup command
az webapp config set \
  --resource-group octopus-agile-rg \
  --name octopus-agile \
  --startup-file "startup.sh"

# Add application settings
az webapp config appsettings set \
  --resource-group octopus-agile-rg \
  --name octopus-agile \
  --settings \
    OCTOPUS_API_KEY="your-key" \
    MPAN_KEY="your-mpan" \
    METER_KEY="your-meter" \
    GAS_MPRN="your-mprn" \
    GAS_METER_SERIAL="your-serial" \
    WEBSITES_PORT="8000"
```

#### Step 5: Access Your App

Your app will be available at:
```
https://octopus-agile.azurewebsites.net
```

(Replace `octopus-agile` with your actual app name)

---

### Method 2: Manual Deployment via Azure CLI

For one-time deployment without pipeline:

```bash
# 1. Login to Azure
az login

# 2. Create resource group (if not exists)
az group create --name octopus-agile-rg --location uksouth

# 3. Create App Service Plan
az appservice plan create \
  --name octopus-agile-plan \
  --resource-group octopus-agile-rg \
  --is-linux \
  --sku B1

# 4. Create Web App
az webapp create \
  --name octopus-agile \
  --resource-group octopus-agile-rg \
  --plan octopus-agile-plan \
  --runtime "PYTHON:3.11" \
  --startup-file "startup.sh"

# 5. Configure app settings
az webapp config appsettings set \
  --resource-group octopus-agile-rg \
  --name octopus-agile \
  --settings \
    OCTOPUS_API_KEY="your-key" \
    MPAN_KEY="your-mpan" \
    METER_KEY="your-meter" \
    GAS_MPRN="your-mprn" \
    GAS_METER_SERIAL="your-serial" \
    WEBSITES_PORT="8000"

# 6. Deploy from local Git or GitHub
# Option A: From local directory
cd /workspaces/Octopus_Agile
az webapp up \
  --name octopus-agile \
  --resource-group octopus-agile-rg \
  --runtime "PYTHON:3.11"

# Option B: From GitHub
az webapp deployment source config \
  --name octopus-agile \
  --resource-group octopus-agile-rg \
  --repo-url https://github.com/cchderek/Octopus_Agile \
  --branch feature/gas-usage \
  --manual-integration
```

---

## Pipeline Configuration Details

The pipeline (`azure-pipelines.yml`) performs:

### Build Stage:
1. Uses Python 3.11
2. Installs dependencies from `requirements.txt`
3. Creates deployment package (ZIP)
4. Uploads artifact

### Deploy Stage:
1. Downloads build artifact
2. Deploys to Azure Web App
3. Azure Web App runs `startup.sh` on container start (configured in Web App settings)

### Triggered by:
- Commits to `main` branch
- Commits to `feature/gas-usage` branch

**Note**: The startup command must be configured in the Azure Web App settings (Configuration → General settings → Startup Command = `startup.sh`)

---

## Monitoring & Troubleshooting

### View Logs

**Azure Portal:**
1. Web App → **Log stream** (real-time logs)
2. Web App → **Diagnose and solve problems**

**Azure CLI:**
```bash
# Enable logging
az webapp log config \
  --name octopus-agile \
  --resource-group octopus-agile-rg \
  --application-logging filesystem \
  --level information

# View logs
az webapp log tail \
  --name octopus-agile \
  --resource-group octopus-agile-rg
```

### Common Issues

#### Issue: "Application Error"
**Solution:**
- Check logs: `az webapp log tail`
- Verify `WEBSITES_PORT=8000` is set
- Ensure `startup.sh` is executable

#### Issue: "502 Bad Gateway"
**Solution:**
- App is starting (wait 1-2 minutes)
- Check Application Insights or logs
- Verify Python version matches (3.11)

#### Issue: "Dependencies not found"
**Solution:**
- Ensure `requirements.txt` includes all packages
- Check build logs in Azure DevOps pipeline

#### Issue: "API not working"
**Solution:**
- Verify all environment variables are set correctly
- Check for typos in variable names (case-sensitive)
- Test API key independently

### Performance Tuning

**Enable Always On** (prevents cold starts):
```bash
az webapp config set \
  --name octopus-agile \
  --resource-group octopus-agile-rg \
  --always-on true
```

**Scale Up** (if needed):
```bash
az appservice plan update \
  --name octopus-agile-plan \
  --resource-group octopus-agile-rg \
  --sku S1  # Standard tier
```

---

## Cost Optimization

### Pricing Tiers

| Tier | Cost/Month (approx) | Features |
|------|---------------------|----------|
| **B1** (Basic) | £10-15 | Good for testing, 1 instance |
| **S1** (Standard) | £50-60 | Always On, auto-scale, SSL |
| **P1V2** (Premium) | £100+ | High performance, VNet |

### Recommendations

1. **Start with B1** for development/testing
2. **Upgrade to S1** for production (Always On feature)
3. **Enable auto-scale** if traffic varies
4. **Use deployment slots** for zero-downtime updates (S1+)

---

## CI/CD Workflow

### Automatic Deployment

Once configured, deployments are automatic:

1. **Push code** to GitHub (`main` or `feature/gas-usage`)
2. **Pipeline triggers** automatically
3. **Builds** and runs tests
4. **Deploys** to Azure Web App
5. **App restarts** with new code

### Manual Deployment

Trigger manually in Azure DevOps:
- Pipelines → Select pipeline → **Run pipeline**

---

## Security Best Practices

### 1. Enable HTTPS Only
```bash
az webapp update \
  --name octopus-agile \
  --resource-group octopus-agile-rg \
  --https-only true
```

### 2. Use Key Vault for Secrets (Optional)

Instead of app settings, use Azure Key Vault:

```bash
# Create Key Vault
az keyvault create \
  --name octopus-kv \
  --resource-group octopus-agile-rg \
  --location uksouth

# Add secrets
az keyvault secret set \
  --vault-name octopus-kv \
  --name OCTOPUS-API-KEY \
  --value "your-api-key"

# Grant Web App access
az webapp identity assign \
  --name octopus-agile \
  --resource-group octopus-agile-rg

# Reference in app settings
az webapp config appsettings set \
  --name octopus-agile \
  --resource-group octopus-agile-rg \
  --settings OCTOPUS_API_KEY="@Microsoft.KeyVault(SecretUri=https://octopus-kv.vault.azure.net/secrets/OCTOPUS-API-KEY/)"
```

### 3. Restrict Access (Optional)

Add IP restrictions or authentication:
```bash
az webapp config access-restriction add \
  --name octopus-agile \
  --resource-group octopus-agile-rg \
  --rule-name "Home" \
  --action Allow \
  --ip-address "YOUR_IP/32" \
  --priority 100
```

---

## Updating the Application

### Via Pipeline (Automated)
1. Make changes to code
2. Commit and push to GitHub
3. Pipeline automatically deploys

### Via Azure CLI (Manual)
```bash
cd /workspaces/Octopus_Agile
az webapp up \
  --name octopus-agile \
  --resource-group octopus-agile-rg
```

---

## Useful Commands

```bash
# Restart web app
az webapp restart --name octopus-agile --resource-group octopus-agile-rg

# Stop web app
az webapp stop --name octopus-agile --resource-group octopus-agile-rg

# Start web app
az webapp start --name octopus-agile --resource-group octopus-agile-rg

# Show web app details
az webapp show --name octopus-agile --resource-group octopus-agile-rg

# Delete web app
az webapp delete --name octopus-agile --resource-group octopus-agile-rg

# Delete entire resource group
az group delete --name octopus-agile-rg --yes
```

---

## Support & Resources

- **Azure Web Apps Docs**: https://learn.microsoft.com/en-us/azure/app-service/
- **Azure DevOps Pipelines**: https://learn.microsoft.com/en-us/azure/devops/pipelines/
- **Python on Azure**: https://learn.microsoft.com/en-us/azure/app-service/quickstart-python
- **Streamlit Deployment**: https://docs.streamlit.io/deploy

---

## Next Steps

After successful deployment:

1. ✅ Test all pages (Rates, Electricity Usage, Gas Usage)
2. ✅ Configure custom domain (optional)
3. ✅ Set up Application Insights monitoring
4. ✅ Configure backup and disaster recovery
5. ✅ Add authentication if needed (Azure AD)
6. ✅ Set up alerts for errors/downtime

Your Octopus Energy Dashboard is now live on Azure! 🚀
