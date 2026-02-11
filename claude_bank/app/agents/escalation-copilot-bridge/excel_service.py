"""
Excel Online service for ticket storage via Microsoft Graph API.
"""

import logging
from typing import Optional, Dict, Any
from config import settings
from graph_client import get_graph_client
from models import TicketData

logger = logging.getLogger(__name__)


class ExcelService:
    """
    Service for interacting with Excel Online via Microsoft Graph API.
    """
    
    def __init__(self):
        self.drive_id = settings.EXCEL_DRIVE_ID
        self.site_id = settings.EXCEL_SITE_ID
        self.user_id = settings.EXCEL_USER_ID
        self.file_path = settings.EXCEL_FILE_PATH
        self.table_name = settings.EXCEL_TABLE_NAME
        
    async def _get_file_id(self) -> str:
        """
        Get the file ID for the Excel file.
        
        Returns:
            File ID string
        """
        graph_client = await get_graph_client()
        
        # If drive_id is provided, use it directly
        if self.drive_id:
            # Get file by path
            endpoint = f"drives/{self.drive_id}/root:/{self.file_path.lstrip('/')}"
            file_data = await graph_client.get(endpoint)
            return file_data["id"]
        
        # If site_id is provided, get drive from site
        if self.site_id:
            endpoint = f"sites/{self.site_id}/drive/root:/{self.file_path.lstrip('/')}"
            file_data = await graph_client.get(endpoint)
            return file_data["id"]
        
        # If user_id is provided, use user's OneDrive
        if self.user_id:
            endpoint = f"users/{self.user_id}/drive/root:/{self.file_path.lstrip('/')}"
            file_data = await graph_client.get(endpoint)
            return file_data["id"]
        
        raise ValueError("No drive_id, site_id, or user_id configured for Excel access")
    
    async def discover_excel_file(self) -> Dict[str, Any]:
        """
        Discover Excel file details for setup/debugging.
        
        Returns:
            Dictionary with file information
        """
        try:
            graph_client = await get_graph_client()
            
            # Try different access methods
            methods = []
            
            if self.drive_id:
                methods.append(("drive_id", f"drives/{self.drive_id}/root:/{self.file_path.lstrip('/')}"))
            
            if self.site_id:
                methods.append(("site_id", f"sites/{self.site_id}/drive/root:/{self.file_path.lstrip('/')}"))
            
            if self.user_id:
                methods.append(("user_id", f"users/{self.user_id}/drive/root:/{self.file_path.lstrip('/')}"))
            
            results = {}
            for method_name, endpoint in methods:
                try:
                    file_data = await graph_client.get(endpoint)
                    results[method_name] = {
                        "success": True,
                        "file_id": file_data.get("id"),
                        "name": file_data.get("name"),
                        "web_url": file_data.get("webUrl")
                    }
                    logger.info(f"Successfully accessed file via {method_name}")
                except Exception as e:
                    results[method_name] = {
                        "success": False,
                        "error": str(e)
                    }
                    logger.warning(f"Failed to access file via {method_name}: {e}")
            
            return results
        
        except Exception as e:
            logger.error(f"Error discovering Excel file: {e}")
            raise
    
    async def get_table_columns(self) -> list[str]:
        """
        Get column names from the Excel table.
        
        Returns:
            List of column names
        """
        try:
            graph_client = await get_graph_client()
            file_id = await self._get_file_id()
            
            # Get table columns
            endpoint = f"drives/{self.drive_id}/items/{file_id}/workbook/tables/{self.table_name}/columns"
            columns_data = await graph_client.get(endpoint)
            
            columns = [col["name"] for col in columns_data.get("value", [])]
            logger.info(f"Excel table has columns: {columns}")
            return columns
        
        except Exception as e:
            logger.error(f"Error getting table columns: {e}")
            raise
    
    async def add_ticket_row(self, ticket: TicketData) -> bool:
        """
        Add a new ticket row to the Excel table.
        
        Args:
            ticket: Ticket data to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            graph_client = await get_graph_client()
            file_id = await self._get_file_id()
            
            # Prepare row data - order must match Excel columns
            row_data = [
                ticket.ticket_id,
                ticket.customer_id,
                ticket.customer_email,
                ticket.customer_name,
                ticket.description,
                ticket.priority,
                ticket.status,
                ticket.created_date
            ]
            
            # Add row to table
            endpoint = f"drives/{self.drive_id}/items/{file_id}/workbook/tables/{self.table_name}/rows"
            
            payload = {
                "values": [row_data]
            }
            
            logger.info(f"Adding ticket {ticket.ticket_id} to Excel table")
            logger.debug(f"Row data: {row_data}")
            
            result = await graph_client.post(endpoint, payload)
            
            logger.info(f"Successfully added ticket {ticket.ticket_id} to Excel")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add ticket to Excel: {e}")
            return False
    
    async def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Get ticket data by ID from Excel.
        
        Args:
            ticket_id: Ticket ID to search for
            
        Returns:
            Ticket data dictionary or None if not found
        """
        try:
            graph_client = await get_graph_client()
            file_id = await self._get_file_id()
            
            # Get all rows
            endpoint = f"drives/{self.drive_id}/items/{file_id}/workbook/tables/{self.table_name}/rows"
            rows_data = await graph_client.get(endpoint)
            
            # Search for ticket
            for row in rows_data.get("value", []):
                values = row.get("values", [[]])[0]
                if values and values[0] == ticket_id:
                    return {
                        "ticket_id": values[0],
                        "customer_id": values[1],
                        "customer_email": values[2],
                        "customer_name": values[3],
                        "description": values[4],
                        "priority": values[5],
                        "status": values[6],
                        "created_date": values[7]
                    }
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting ticket from Excel: {e}")
            return None


# Global instance
_excel_service: Optional[ExcelService] = None


async def get_excel_service() -> ExcelService:
    """Get or create global Excel service."""
    global _excel_service
    if _excel_service is None:
        _excel_service = ExcelService()
    return _excel_service
