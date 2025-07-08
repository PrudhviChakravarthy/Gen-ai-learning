import json
import pandas as pd
from datetime import datetime
from crewai.tools import BaseTool
from utils.logger import logger


class ExcelTool(BaseTool):
    """Tool for creating and managing Excel files"""
    name: str = "excel_manager"
    description: str = "Creates and manages Excel files for laptop data"
    
    def _run(self, instruction: str) -> str:
        """Create Excel file from laptop data"""
        try:
            if "create_excel" in instruction:
                data_json = instruction.split("data:")[-1].strip()
                laptop_data = json.loads(data_json)
                
                # Create DataFrame
                df = pd.DataFrame(laptop_data)
                
                # Create Excel file with formatting
                filename = f"laptops_under_60k_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Laptops', index=False)
                    
                    # Get workbook and worksheet
                    workbook = writer.book
                    worksheet = writer.sheets['Laptops']
                    
                    # Auto-adjust column widths
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                logger.info(f"📊 Excel file created: {filename}")
                return f"Excel file created successfully: {filename}"
            
            return "Invalid instruction"
            
        except Exception as e:
            logger.error(f"Error in excel tool: {str(e)}")
            return f"Error: {str(e)}"