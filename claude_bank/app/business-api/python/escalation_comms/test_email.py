"""
Quick test script to send a test email via Azure Communication Services.
Run this to verify email functionality is working correctly.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from services import AzureCommunicationEmailService
from models import EmailMessage, EmailRecipient

# Load environment variables
root_env = Path(__file__).parent.parent.parent.parent.parent / ".env"
load_dotenv(root_env)

async def test_send_email():
    """Send a test email to verify Azure Communication Services setup."""
    
    # Get configuration
    endpoint = os.getenv("AZURE_COMMUNICATION_SERVICES_ENDPOINT")
    from_email = os.getenv("AZURE_COMMUNICATION_SERVICES_EMAIL_FROM")
    test_recipient = os.getenv("TEST_EMAIL_RECIPIENT")
    
    print("=" * 80)
    print("Azure Communication Services - Email Test")
    print("=" * 80)
    print(f"Endpoint: {endpoint}")
    print(f"From: {from_email}")
    print(f"To: {test_recipient}")
    print("=" * 80)
    
    if not endpoint:
        print("❌ ERROR: AZURE_COMMUNICATION_SERVICES_ENDPOINT not configured")
        return
    
    if not test_recipient:
        print("❌ ERROR: TEST_EMAIL_RECIPIENT not configured")
        return
    
    # Initialize email service
    print("\n📧 Initializing Azure Communication Services email client...")
    email_service = AzureCommunicationEmailService(
        endpoint=endpoint,
        from_email=from_email
    )
    print("✅ Email client initialized\n")
    
    # Create test email
    email_message = EmailMessage(
        to=[EmailRecipient(email=test_recipient, name="Test User")],
        subject="🎉 BankX - EscalationComms Test Email",
        body="""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style="color: #0066cc; border-bottom: 2px solid #0066cc; padding-bottom: 10px;">
                    🎉 BankX Multi-Agent Banking System
                </h2>
                
                <p>Hello!</p>
                
                <p>This is a <strong>test email</strong> from the BankX EscalationComms agent.</p>
                
                <div style="background-color: #f0f8ff; padding: 15px; border-left: 4px solid #0066cc; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #0066cc;">✅ Email Service Status</h3>
                    <ul style="margin-bottom: 0;">
                        <li>Azure Communication Services: <strong>Operational</strong></li>
                        <li>Email Domain: Azure Managed Domain</li>
                        <li>Authentication: DefaultAzureCredential (Azure CLI)</li>
                        <li>Sender: DoNotReply@b231fdc2-584f-4b7e-9bcb-1b7401d144bf.azurecomm.net</li>
                    </ul>
                </div>
                
                <p>If you're receiving this email, it means:</p>
                <ol>
                    <li>Azure Communication Services is properly configured ✅</li>
                    <li>Email sending functionality is working ✅</li>
                    <li>DNS verification is complete ✅</li>
                    <li>The EscalationComms MCP server is operational ✅</li>
                </ol>
                
                <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px;">
                    <strong>BankX Multi-Agent Banking System</strong><br>
                    UC2: Product Information & FAQ | UC3: AI Money Coach<br>
                    Powered by Azure AI Foundry + Model Context Protocol
                </p>
            </div>
        </body>
        </html>
        """,
        is_html=True
    )
    
    # Send email
    print("📤 Sending test email...")
    print(f"   To: {test_recipient}")
    print(f"   Subject: {email_message.subject}\n")
    
    try:
        result = await email_service.send_email(email_message)
        
        if result.success:
            print("=" * 80)
            print("✅ EMAIL SENT SUCCESSFULLY!")
            print("=" * 80)
            print(f"Message ID: {result.message_id}")
            print(f"Sent at: {result.sent_at}")
            print(f"\n📬 Check your inbox at: {test_recipient}")
            print("   (Check spam/junk folder if not in inbox)")
            print("=" * 80)
        else:
            print("=" * 80)
            print("❌ EMAIL SEND FAILED")
            print("=" * 80)
            print(f"Error: {result.error}")
            print("=" * 80)
    
    except Exception as e:
        print("=" * 80)
        print("❌ EXCEPTION OCCURRED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print("=" * 80)


if __name__ == "__main__":
    print("\n🚀 Starting Azure Communication Services Email Test...\n")
    asyncio.run(test_send_email())
    print("\n✅ Test completed!\n")
