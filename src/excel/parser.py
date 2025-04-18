import pandas as pd
import numpy as np
from openpyxl import load_workbook
from typing import Dict, List, Optional, Tuple
import os
import logging
import traceback

from ..models.dealer import DealerOutlet
from ..models.scenario import Scenario

class ExcelParser:
    """
    Parser for reading and writing dealer feasibility Excel files
    """
    
    @staticmethod
    def read_df_format(file_path: str) -> Tuple[Optional[DealerOutlet], Optional[Scenario]]:
        """
        Read dealer and scenario data from a DF format Excel file
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Tuple of (DealerOutlet, Scenario) objects, or (None, None) if parsing fails
        """
        try:
            # Read the Excel file
            df_dict = pd.read_excel(file_path, sheet_name=None)
            
            # Check for required sheets
            required_sheets = ['DF A1', 'sales', 'Investment', 'Insurance DF A1']
            missing_sheets = [sheet for sheet in required_sheets if sheet not in df_dict]
            if missing_sheets:
                logging.error(f"Missing required sheets in Excel file {file_path}: {', '.join(missing_sheets)}")
                # Optionally raise an error or return None
                # raise ValueError(f"Missing sheets: {', '.join(missing_sheets)}")
                return None, None # Return None if critical sheets are missing
                
            # Extract data from the main sheet
            main_df = df_dict.get('DF A1', pd.DataFrame())
            sales_df = df_dict.get('sales', pd.DataFrame())
            investment_df = df_dict.get('Investment', pd.DataFrame())
            insurance_df = df_dict.get('Insurance DF A1', pd.DataFrame())
            
            # Extract basic information
            dealer_name = ""
            dealer_location = ""
            district = ""
            feeding_point = ""
            area_executive = ""
            referred_by = ""
            
            # Extract sales data
            pmg_sales = 0.0
            hsd_sales = 0.0
            hobc_sales = 0.0
            lube_sales = 0.0
            
            # Try to find basic information in the main sheet
            for i, row in main_df.iterrows():
                if row.iloc[0] == 'District:':
                    district = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
                elif row.iloc[0] == 'Feeding Point :':
                    feeding_point = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
                elif row.iloc[0] == 'Area Executive:':
                    area_executive = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
                elif row.iloc[0] == 'Case Referred by:':
                    referred_by = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
                elif row.iloc[0] == 'PMG':
                    pmg_sales = float(row.iloc[1]) if pd.notna(row.iloc[1]) else 0.0
                elif row.iloc[0] == 'HSD':
                    hsd_sales = float(row.iloc[1]) if pd.notna(row.iloc[1]) else 0.0
                elif row.iloc[0] == 'XTRON':
                    hobc_sales = float(row.iloc[1]) if pd.notna(row.iloc[1]) else 0.0
                elif row.iloc[0] == 'LUBE':
                    lube_sales = float(row.iloc[1]) if pd.notna(row.iloc[1]) else 0.0
            
            # Extract growth rates and margins from sales sheet
            pmg_growth_rates = {}
            hsd_growth_rates = {}
            hobc_growth_rates = {}
            lube_growth_rates = {}
            
            pmg_margins = {}
            hsd_margins = {}
            hobc_margins = {}
            lube_margins = {}
            
            # Look for product headers in sales sheet
            product_row_idx = -1
            margin_row_indices = {}
            
            for i, row in sales_df.iterrows():
                if row.iloc[0] == 'Product':
                    product_row_idx = i
                elif product_row_idx >= 0 and row.iloc[0] == 'PMG':
                    margin_row_indices['pmg'] = i + 6  # Assuming margin rows are 6 rows after product rows
                elif product_row_idx >= 0 and row.iloc[0] == 'HSD':
                    margin_row_indices['hsd'] = i + 6
                elif product_row_idx >= 0 and row.iloc[0] == 'XTRON':
                    margin_row_indices['hobc'] = i + 6
                elif product_row_idx >= 0 and row.iloc[0] == 'Lube':
                    margin_row_indices['lube'] = i + 6
            
            # Get column headers (years)
            if product_row_idx >= 0:
                year_headers = []
                for col in range(1, sales_df.shape[1]):
                    header = sales_df.iloc[product_row_idx, col]
                    if pd.notna(header) and 'Year' in str(header):
                        year_headers.append((col, str(header)))
                
                # Extract growth rates and margins
                for year_idx, (col, year_header) in enumerate(year_headers):
                    year = year_idx + 1
                    
                    if 'pmg' in margin_row_indices:
                        margin_row = margin_row_indices['pmg']
                        margin_value = sales_df.iloc[margin_row, col]
                        if pd.notna(margin_value):
                            pmg_margins[year] = float(margin_value)
                    
                    if 'hsd' in margin_row_indices:
                        margin_row = margin_row_indices['hsd']
                        margin_value = sales_df.iloc[margin_row, col]
                        if pd.notna(margin_value):
                            hsd_margins[year] = float(margin_value)
                    
                    if 'hobc' in margin_row_indices:
                        margin_row = margin_row_indices['hobc']
                        margin_value = sales_df.iloc[margin_row, col]
                        if pd.notna(margin_value):
                            hobc_margins[year] = float(margin_value)
                    
                    if 'lube' in margin_row_indices:
                        margin_row = margin_row_indices['lube']
                        margin_value = sales_df.iloc[margin_row, col]
                        if pd.notna(margin_value):
                            lube_margins[year] = float(margin_value)
            
            # Extract investment items
            investment_items = {}
            for i, row in investment_df.iterrows():
                if pd.notna(row.iloc[1]) and pd.notna(row.iloc[7]):
                    item_name = str(row.iloc[1])
                    item_cost = float(row.iloc[7]) if pd.notna(row.iloc[7]) else 0.0
                    if item_name and item_cost > 0:
                        investment_items[item_name] = item_cost
            
            # Calculate initial investment
            initial_investment = sum(investment_items.values())
            
            # Extract insurance rates
            insurance_rates = {}
            for i, row in insurance_df.iterrows():
                if pd.notna(row.iloc[1]) and row.iloc[1] == "Rate" and pd.notna(row.iloc[2]):
                    insurance_type = str(insurance_df.iloc[i-1, 1]) if pd.notna(insurance_df.iloc[i-1, 1]) else "Unknown"
                    rate = float(row.iloc[2]) if pd.notna(row.iloc[2]) else 0.0
                    if insurance_type and rate > 0:
                        insurance_rates[insurance_type] = rate
            
            # Check if essential data was extracted
            if not dealer_name or not dealer_location: # Assuming name/location are essential
                 logging.warning(f"Could not extract essential dealer info (name/location) from {file_path}")
                 # Decide if this should be a hard failure
                 # return None, None

            # Create DealerOutlet object
            dealer = DealerOutlet(
                name=dealer_name,
                location=dealer_location,
                district=district,
                feeding_point=feeding_point,
                area_executive=area_executive,
                referred_by=referred_by,
                pmg_sales=pmg_sales,
                hsd_sales=hsd_sales,
                hobc_sales=hobc_sales,
                lube_sales=lube_sales,
                pmg_growth_rate=pmg_growth_rates,
                hsd_growth_rate=hsd_growth_rates,
                hobc_growth_rate=hobc_growth_rates,
                lube_growth_rate=lube_growth_rates,
                pmg_margin=pmg_margins,
                hsd_margin=hsd_margins,
                hobc_margin=hobc_margins,
                lube_margin=lube_margins,
                initial_investment=initial_investment,
                investment_items=investment_items,
                insurance_rates=insurance_rates
            )
            
            # Create default scenario
            scenario = Scenario(
                name="Base Scenario",
                description="Based on DF format file",
                default_margins={
                    'pmg': pmg_margins,
                    'hsd': hsd_margins,
                    'hobc': hobc_margins,
                    'lube': lube_margins
                },
                insurance_rates=insurance_rates
            )
            
            return dealer, scenario

        except FileNotFoundError:
            logging.error(f"Excel file not found at {file_path}")
            raise # Re-raise file not found
        except Exception as e:
            logging.error(f"Error parsing Excel file {file_path}: {str(e)}")
            logging.error(traceback.format_exc()) # Log full traceback for debugging
            # Depending on desired behavior, either raise the error or return None
            # raise # Re-raise the exception
            return None, None # Return None on general parsing errors
    
    @staticmethod
    def get_template_path() -> str:
        """
        Get path to the template Excel file
        
        Returns:
            Path to the template file
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, 'data', 'templates', 'df_template.xlsx')
    
    @staticmethod
    def create_df_format(dealer: DealerOutlet, scenario: Scenario, output_path: str) -> None:
        """
        Create a DF format Excel file from dealer and scenario data
        
        Args:
            dealer: DealerOutlet object
            scenario: Scenario object
            output_path: Path to save the Excel file
        """
        # Get template path
        template_path = ExcelParser.get_template_path()
        
        # Check if template exists
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found at {template_path}")
        
        # Copy template
        wb = load_workbook(template_path)
        
        # TODO: Implement writing data to the Excel file
        # This would involve updating cells with dealer and scenario data
        
        # Save the file
        wb.save(output_path) 