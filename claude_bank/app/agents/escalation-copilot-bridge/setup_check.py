"""
Setup helper script for Escalation Copilot Bridge.
Run this to validate your configuration and test connectivity.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings, validate_settings
from graph_client import get_graph_client
from excel_service import get_excel_service
from email_service import get_email_service


async def main():
    """Run setup checks."""
    
    print("=" * 60)
    print("Escalation Copilot Bridge - Setup Validator")
    print("=" * 60)
    print()
    
    # Check 1: Configuration
    print("📋 Checking configuration...")
    is_valid, errors = validate_settings()
    
    if is_valid:
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration has errors:")
        for error in errors:
            print(f"   - {error}")
        print()
        print("Please fix these errors in your .env file")
        return
    
    print()
    
    # Check 2: Microsoft Graph Authentication
    print("🔐 Testing Microsoft Graph authentication...")
    try:
        graph_client = await get_graph_client()
        token = await graph_client.get_access_token()
        print(f"✅ Successfully authenticated with Microsoft Graph")
        print(f"   Token length: {len(token)} characters")
    except Exception as e:
        print(f"❌ Failed to authenticate: {e}")
        print()
        print("Please check:")
        print("  - AZURE_CLIENT_ID is correct")
        print("  - AZURE_CLIENT_SECRET is correct (not expired)")
        print("  - AZURE_TENANT_ID is correct")
        return
    
    print()
    
    # Check 3: Excel File Access
    print("📊 Testing Excel file access...")
    try:
        excel_service = await get_excel_service()
        file_info = await excel_service.discover_excel_file()
        
        # Find successful method
        success_method = None
        for method, info in file_info.items():
            if info.get("success"):
                success_method = method
                print(f"✅ Successfully accessed Excel file via {method}")
                print(f"   File ID: {info.get('file_id')}")
                print(f"   File name: {info.get('name')}")
                print(f"   Web URL: {info.get('web_url')}")
                break
        
        if not success_method:
            print("❌ Could not access Excel file via any method:")
            for method, info in file_info.items():
                print(f"   - {method}: {info.get('error')}")
            print()
            print("Please check:")
            print("  - EXCEL_DRIVE_ID, EXCEL_SITE_ID, or EXCEL_USER_ID is set correctly")
            print("  - EXCEL_FILE_PATH is correct")
            print("  - File exists at the specified location")
            print("  - App has Files.ReadWrite.All permission")
            return
        
        # Try to get table columns
        print()
        print("📑 Checking Excel table...")
        try:
            columns = await excel_service.get_table_columns()
            print(f"✅ Found table '{settings.EXCEL_TABLE_NAME}' with {len(columns)} columns:")
            for col in columns:
                print(f"   - {col}")
            
            # Validate expected columns
            expected = ["Ticket ID", "Customer ID", "Customer Email", "Customer Name", 
                       "Description", "Priority", "Status", "Created Date"]
            if columns == expected:
                print("✅ Column structure matches expected format")
            else:
                print("⚠️  Column structure differs from expected:")
                print(f"   Expected: {expected}")
                print(f"   Got: {columns}")
        except Exception as e:
            print(f"❌ Could not access table: {e}")
            print()
            print("Please check:")
            print(f"  - Table named '{settings.EXCEL_TABLE_NAME}' exists in Excel file")
            print("  - Table has proper headers")
            return
    
    except Exception as e:
        print(f"❌ Excel access failed: {e}")
        return
    
    print()
    
    # Check 4: Email Configuration
    print("📧 Testing email configuration...")
    try:
        email_service = await get_email_service()
        print(f"✅ Email service initialized")
        print(f"   Sender: {settings.EMAIL_SENDER_ADDRESS}")
        print(f"   Name: {settings.EMAIL_SENDER_NAME}")
        
        # Ask if user wants to send test email
        print()
        response = input("Send a test email? (y/n): ").strip().lower()
        if response == 'y':
            test_email = input("Enter your email address: ").strip()
            if test_email:
                print(f"Sending test email to {test_email}...")
                success = await email_service.send_test_email(test_email)
                if success:
                    print("✅ Test email sent! Check your inbox.")
                else:
                    print("❌ Failed to send test email")
                    print()
                    print("Please check:")
                    print("  - EMAIL_SENDER_ADDRESS is correct")
                    print("  - App has Mail.Send permission")
                    print("  - Admin consent has been granted")
    
    except Exception as e:
        print(f"❌ Email service failed: {e}")
    
    print()
    print("=" * 60)
    print("Setup validation complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. If all checks passed, you're ready to start the service:")
    print("   python main.py")
    print()
    print("2. Test the A2A endpoint:")
    print('   curl -X POST http://localhost:9006/a2a/invoke \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"messages": [{"role": "user", "content": "Create ticket: Test issue. Email: test@example.com, Name: Test User"}], "customer_id": "CUST-001"}\'')
    print()


if __name__ == "__main__":
    # Check if .env exists
    if not Path(".env").exists():
        print("❌ .env file not found!")
        print()
        print("Please create a .env file from .env.example:")
        print("  cp .env.example .env")
        print("  # Then edit .env with your configuration")
        sys.exit(1)
    
    asyncio.run(main())
