#!/bin/bash
# =====================================================
# Deployment Script for Octopus Agile Dashboard to Snowflake
# =====================================================
# This script automates the upload of Streamlit files to Snowflake
# and creates the Streamlit app.

set -e  # Exit on any error

# ANSI Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
# Update these variables with your Snowflake connection details
SNOWFLAKE_ACCOUNT="znyskxr-KJ59114"
SNOWFLAKE_USER="MEREWORDS"
SNOWFLAKE_ROLE="ACCOUNTADMIN"  # Or your preferred role
SNOWFLAKE_WAREHOUSE="STREAMLIT_WH"
SNOWFLAKE_DATABASE="OCTOPUS_ENERGY"
SNOWFLAKE_SCHEMA="APPS"
SNOWFLAKE_STAGE="STREAMLIT_STAGE"
CONNECTION_NAME=""  # SnowSQL connection name (from ~/.snowsql/config)

# Files to upload
FILES=(
    "streamlit_app.py"
    "octopus_api.py"
    "utils.py"
    "snowflake_cache.py"
    "environment.yml"
)

# Print functions
print_header() {
    echo -e "${BLUE}=============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

# Check if SnowSQL is installed
check_snowsql() {
    if ! command -v snowsql &> /dev/null; then
        print_error "SnowSQL is not installed or not in PATH"
        echo "Please install SnowSQL from: https://docs.snowflake.com/en/user-guide/snowsql-install-config.html"
        exit 1
    fi
    print_success "SnowSQL is installed"
}

# Prompt for connection details if not set
get_connection_details() {
    if [ -z "$CONNECTION_NAME" ]; then
        echo ""
        print_warning "No SnowSQL connection name provided"
        read -p "Enter your SnowSQL connection name (or press Enter to use individual credentials): " CONNECTION_NAME
    fi
    
    if [ -z "$CONNECTION_NAME" ]; then
        if [ -z "$SNOWFLAKE_ACCOUNT" ]; then
            read -p "Enter your Snowflake account identifier: " SNOWFLAKE_ACCOUNT
        fi
        if [ -z "$SNOWFLAKE_USER" ]; then
            read -p "Enter your Snowflake username: " SNOWFLAKE_USER
        fi
    fi
}

# Upload files to Snowflake stage
upload_files() {
    print_header "Uploading Files to Snowflake"
    
    local upload_cmd_prefix=""
    if [ -n "$CONNECTION_NAME" ]; then
        upload_cmd_prefix="snowsql -c $CONNECTION_NAME"
    else
        upload_cmd_prefix="snowsql -a $SNOWFLAKE_ACCOUNT -u $SNOWFLAKE_USER"
    fi
    
    for file in "${FILES[@]}"; do
        if [ ! -f "$file" ]; then
            print_error "File not found: $file"
            exit 1
        fi
        
        print_info "Uploading $file..."
        
        $upload_cmd_prefix \
            -d $SNOWFLAKE_DATABASE \
            -s $SNOWFLAKE_SCHEMA \
            -w $SNOWFLAKE_WAREHOUSE \
            -q "PUT file://$(pwd)/$file @$SNOWFLAKE_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
        
        if [ $? -eq 0 ]; then
            print_success "Uploaded $file"
        else
            print_error "Failed to upload $file"
            exit 1
        fi
    done
    
    echo ""
}

# Execute SQL setup script
setup_snowflake() {
    print_header "Setting up Snowflake Environment"
    
    local sql_cmd_prefix=""
    if [ -n "$CONNECTION_NAME" ]; then
        sql_cmd_prefix="snowsql -c $CONNECTION_NAME"
    else
        sql_cmd_prefix="snowsql -a $SNOWFLAKE_ACCOUNT -u $SNOWFLAKE_USER"
    fi
    
    print_info "Creating database, schema, and warehouse..."
    $sql_cmd_prefix -f deploy_to_snowflake.sql
    
    if [ $? -eq 0 ]; then
        print_success "Snowflake environment setup complete"
    else
        print_error "Failed to setup Snowflake environment"
        exit 1
    fi
    
    echo ""
}

# Verify deployment
verify_deployment() {
    print_header "Verifying Deployment"
    
    local sql_cmd_prefix=""
    if [ -n "$CONNECTION_NAME" ]; then
        sql_cmd_prefix="snowsql -c $CONNECTION_NAME"
    else
        sql_cmd_prefix="snowsql -a $SNOWFLAKE_ACCOUNT -u $SNOWFLAKE_USER"
    fi
    
    print_info "Listing files in stage..."
    $sql_cmd_prefix \
        -d $SNOWFLAKE_DATABASE \
        -s $SNOWFLAKE_SCHEMA \
        -q "LIST @$SNOWFLAKE_STAGE;"
    
    echo ""
    print_info "Verifying Streamlit app..."
    $sql_cmd_prefix \
        -d $SNOWFLAKE_DATABASE \
        -s $SNOWFLAKE_SCHEMA \
        -q "SHOW STREAMLITS LIKE 'AGILE_DASHBOARD';"
    
    echo ""
}

# Print next steps
print_next_steps() {
    print_header "Deployment Complete!"
    echo ""
    print_success "Your Octopus Agile Dashboard has been deployed to Snowflake"
    echo ""
    echo "Next Steps:"
    echo "1. Configure secrets in Snowsight UI:"
    echo "   - Navigate to: OCTOPUS_ENERGY > APPS > AGILE_DASHBOARD"
    echo "   - Click 'Settings' and add the following secrets:"
    echo "     • OCTOPUS_API_KEY"
    echo "     • MPAN_KEY"
    echo "     • METER_KEY"
    echo "     • GAS_MPRN"
    echo "     • GAS_METER_SERIAL"
    echo ""
    echo "2. Access your app at:"
    if [ -n "$SNOWFLAKE_ACCOUNT" ]; then
        echo "   https://$SNOWFLAKE_ACCOUNT.snowflakecomputing.com/streamlit/OCTOPUS_ENERGY.APPS.AGILE_DASHBOARD"
    else
        echo "   https://<your-account>.snowflakecomputing.com/streamlit/OCTOPUS_ENERGY.APPS.AGILE_DASHBOARD"
    fi
    echo ""
    print_info "For local testing with Snowflake, keep your .env file with the same secrets"
    echo ""
}

# Main execution
main() {
    clear
    print_header "Octopus Agile Dashboard - Snowflake Deployment"
    echo ""
    
    # Check prerequisites
    check_snowsql
    
    # Get connection details
    get_connection_details
    
    # Confirm deployment
    echo ""
    echo "You are about to deploy the Octopus Agile Dashboard to:"
    echo "  Database: $SNOWFLAKE_DATABASE"
    echo "  Schema: $SNOWFLAKE_SCHEMA"
    echo "  Warehouse: $SNOWFLAKE_WAREHOUSE"
    echo ""
    read -p "Continue with deployment? (y/N): " confirm
    
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled"
        exit 0
    fi
    
    echo ""
    
    # Run deployment steps
    setup_snowflake
    upload_files
    verify_deployment
    print_next_steps
}

# Run main function
main
