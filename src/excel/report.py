import pandas as pd
import os
from typing import Dict, List, Any, Optional
import xlsxwriter
from datetime import datetime

from ..models.dealer import DealerOutlet
from ..models.scenario import Scenario

class ReportGenerator:
    """
    Class for generating Excel reports from feasibility analysis
    """
    
    @staticmethod
    def generate_comparison_report(
        dealer: DealerOutlet,
        scenarios: Dict[str, Dict[str, Any]],
        output_path: str
    ) -> None:
        """
        Generate a comparison report for multiple scenarios
        
        Args:
            dealer: DealerOutlet object
            scenarios: Dictionary of scenario names to results
            output_path: Path to save the Excel report
        """
        # Create Excel writer
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        workbook = writer.book
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E1F2',
            'border': 1
        })
        
        number_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1
        })
        
        percent_format = workbook.add_format({
            'num_format': '0.00%',
            'border': 1
        })
        
        currency_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1
        })
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # Create summary sheet
        summary_df = pd.DataFrame({
            'Scenario': [],
            'NPV': [],
            'IRR (%)': [],
            'Payback Period (Years)': [],
            'Initial Investment': [],
            'Total Cash Inflow': []
        })
        
        # Add data for each scenario
        for scenario_name, results in scenarios.items():
            summary_df = pd.concat([summary_df, pd.DataFrame({
                'Scenario': [scenario_name],
                'NPV': [results.get('npv', 0)],
                'IRR (%)': [results.get('irr', 0)],
                'Payback Period (Years)': [results.get('payback_period', 0)],
                'Initial Investment': [results.get('initial_investment', 0)],
                'Total Cash Inflow': [results.get('total_cash_inflow', 0)]
            })], ignore_index=True)
        
        # Sort by NPV descending
        summary_df = summary_df.sort_values('NPV', ascending=False)
        
        # Write summary sheet
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        summary_sheet = writer.sheets['Summary']
        
        # Add title
        summary_sheet.merge_range('A1:F1', f'Feasibility Comparison for {dealer.name}', title_format)
        summary_sheet.write_row('A2', summary_df.columns, header_format)
        
        # Format columns
        summary_sheet.set_column('A:A', 20)
        summary_sheet.set_column('B:B', 15, currency_format)
        summary_sheet.set_column('C:C', 10, percent_format)
        summary_sheet.set_column('D:D', 20, number_format)
        summary_sheet.set_column('E:E', 20, currency_format)
        summary_sheet.set_column('F:F', 20, currency_format)
        
        # Add scenarios detail sheets
        for scenario_name, results in scenarios.items():
            # Get cash flows and yearly data
            cash_flows = results.get('cash_flows', [])
            yearly_data = results.get('yearly_data', {})
            
            # Create yearly data dataframe
            if yearly_data:
                years = list(range(len(cash_flows)))
                yearly_df = pd.DataFrame({
                    'Year': years,
                    'PMG Sales (Liters)': [yearly_data.get('pmg_sales', {}).get(year, 0) for year in years],
                    'HSD Sales (Liters)': [yearly_data.get('hsd_sales', {}).get(year, 0) for year in years],
                    'HOBC Sales (Liters)': [yearly_data.get('hobc_sales', {}).get(year, 0) for year in years],
                    'Lube Sales (Liters)': [yearly_data.get('lube_sales', {}).get(year, 0) for year in years],
                    'PMG Revenue': [yearly_data.get('pmg_revenue', {}).get(year, 0) for year in years],
                    'HSD Revenue': [yearly_data.get('hsd_revenue', {}).get(year, 0) for year in years],
                    'HOBC Revenue': [yearly_data.get('hobc_revenue', {}).get(year, 0) for year in years],
                    'Lube Revenue': [yearly_data.get('lube_revenue', {}).get(year, 0) for year in years],
                    'Total Revenue': [yearly_data.get('total_revenue', {}).get(year, 0) for year in years],
                    'Operating Costs': [yearly_data.get('operating_costs', {}).get(year, 0) for year in years],
                    'Insurance': [yearly_data.get('insurance', {}).get(year, 0) for year in years],
                    'Net Cash Flow': cash_flows
                })
                
                # Write yearly data sheet
                sheet_name = scenario_name[:31]  # Excel sheet names limited to 31 chars
                yearly_df.to_excel(writer, sheet_name=sheet_name, index=False)
                yearly_sheet = writer.sheets[sheet_name]
                
                # Add title
                yearly_sheet.merge_range('A1:L1', f'Yearly Data for {scenario_name}', title_format)
                yearly_sheet.write_row('A2', yearly_df.columns, header_format)
                
                # Format columns
                yearly_sheet.set_column('A:A', 10)
                yearly_sheet.set_column('B:E', 15, number_format)
                yearly_sheet.set_column('F:J', 15, currency_format)
                yearly_sheet.set_column('K:M', 15, currency_format)
        
        # Save the report
        writer.close()
    
    @staticmethod
    def generate_single_scenario_report(
        dealer: DealerOutlet,
        scenario: Scenario,
        results: Dict[str, Any],
        output_path: str
    ) -> None:
        """
        Generate a detailed report for a single scenario
        
        Args:
            dealer: DealerOutlet object
            scenario: Scenario object
            results: Analysis results
            output_path: Path to save the Excel report
        """
        # Create Excel writer
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        workbook = writer.book
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E1F2',
            'border': 1
        })
        
        number_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1
        })
        
        percent_format = workbook.add_format({
            'num_format': '0.00%',
            'border': 1
        })
        
        currency_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1
        })
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # Summary sheet
        summary_data = {
            'Metric': [
                'Net Present Value (NPV)',
                'Internal Rate of Return (IRR)',
                'Payback Period',
                'Discounted Payback Period',
                'Initial Investment',
                'Total Cash Inflow',
                'Profitability Index'
            ],
            'Value': [
                results.get('npv', 0),
                results.get('irr', 0) / 100 if results.get('irr') else 0,  # Convert from % to decimal
                results.get('payback_period', 0),
                results.get('discounted_payback_period', 0),
                results.get('initial_investment', 0),
                results.get('total_cash_inflow', 0),
                results.get('profitability_index', 0)
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        summary_sheet = writer.sheets['Summary']
        
        # Add title
        summary_sheet.merge_range('A1:B1', f'Feasibility Analysis for {dealer.name} - {scenario.name}', title_format)
        summary_sheet.write_row('A2', summary_df.columns, header_format)
        
        # Format columns
        summary_sheet.set_column('A:A', 30)
        summary_sheet.set_column('B:B', 20)
        
        # Apply specific formats to cells
        for row_num, (metric, value) in enumerate(zip(summary_data['Metric'], summary_data['Value']), start=2):
            # Apply appropriate format based on metric
            if 'Rate' in metric or 'Index' in metric:
                summary_sheet.write(row_num, 1, value, percent_format)
            elif 'NPV' in metric or 'Investment' in metric or 'Inflow' in metric:
                summary_sheet.write(row_num, 1, value, currency_format)
            elif 'Period' in metric:
                summary_sheet.write(row_num, 1, value, number_format)
            else:
                summary_sheet.write(row_num, 1, value)
        
        # Get cash flows and yearly data
        cash_flows = results.get('cash_flows', [])
        yearly_data = results.get('yearly_data', {})
        
        # Cash flow sheet
        if cash_flows:
            years = list(range(len(cash_flows)))
            cf_df = pd.DataFrame({
                'Year': years,
                'Cash Flow': cash_flows,
                'Discounted Cash Flow': [cf / ((1 + scenario.discount_rate) ** year) for year, cf in enumerate(cash_flows)],
                'Cumulative Cash Flow': [sum(cash_flows[:i+1]) for i in range(len(cash_flows))],
                'Cumulative Discounted Cash Flow': [sum([cf / ((1 + scenario.discount_rate) ** yr) for yr, cf in enumerate(cash_flows[:i+1])]) for i in range(len(cash_flows))]
            })
            
            cf_df.to_excel(writer, sheet_name='Cash Flows', index=False)
            cf_sheet = writer.sheets['Cash Flows']
            
            # Add title
            cf_sheet.merge_range('A1:E1', 'Cash Flow Analysis', title_format)
            cf_sheet.write_row('A2', cf_df.columns, header_format)
            
            # Format columns
            cf_sheet.set_column('A:A', 10)
            cf_sheet.set_column('B:E', 20, currency_format)
        
        # Yearly data sheet
        if yearly_data:
            years = list(range(len(cash_flows)))
            yearly_df = pd.DataFrame({
                'Year': years,
                'PMG Sales (Liters)': [yearly_data.get('pmg_sales', {}).get(year, 0) for year in years],
                'HSD Sales (Liters)': [yearly_data.get('hsd_sales', {}).get(year, 0) for year in years],
                'HOBC Sales (Liters)': [yearly_data.get('hobc_sales', {}).get(year, 0) for year in years],
                'Lube Sales (Liters)': [yearly_data.get('lube_sales', {}).get(year, 0) for year in years],
                'PMG Revenue': [yearly_data.get('pmg_revenue', {}).get(year, 0) for year in years],
                'HSD Revenue': [yearly_data.get('hsd_revenue', {}).get(year, 0) for year in years],
                'HOBC Revenue': [yearly_data.get('hobc_revenue', {}).get(year, 0) for year in years],
                'Lube Revenue': [yearly_data.get('lube_revenue', {}).get(year, 0) for year in years],
                'Total Revenue': [yearly_data.get('total_revenue', {}).get(year, 0) for year in years],
                'Operating Costs': [yearly_data.get('operating_costs', {}).get(year, 0) for year in years],
                'Insurance': [yearly_data.get('insurance', {}).get(year, 0) for year in years],
                'Net Cash Flow': cash_flows
            })
            
            yearly_df.to_excel(writer, sheet_name='Yearly Data', index=False)
            yearly_sheet = writer.sheets['Yearly Data']
            
            # Add title
            yearly_sheet.merge_range('A1:L1', 'Yearly Sales and Revenue Data', title_format)
            yearly_sheet.write_row('A2', yearly_df.columns, header_format)
            
            # Format columns
            yearly_sheet.set_column('A:A', 10)
            yearly_sheet.set_column('B:E', 15, number_format)
            yearly_sheet.set_column('F:L', 15, currency_format)
        
        # Investment sheet
        if dealer.investment_items:
            invest_df = pd.DataFrame({
                'Item': list(dealer.investment_items.keys()),
                'Cost': list(dealer.investment_items.values())
            })
            
            invest_df.to_excel(writer, sheet_name='Investment', index=False)
            invest_sheet = writer.sheets['Investment']
            
            # Add title
            invest_sheet.merge_range('A1:B1', 'Investment Details', title_format)
            invest_sheet.write_row('A2', invest_df.columns, header_format)
            
            # Format columns
            invest_sheet.set_column('A:A', 30)
            invest_sheet.set_column('B:B', 15, currency_format)
            
            # Add total row
            total_row = len(invest_df) + 2
            invest_sheet.write(total_row, 0, 'Total Investment', header_format)
            invest_sheet.write_formula(total_row, 1, f'=SUM(B3:B{total_row})', currency_format)
        
        # Save the report
        writer.close() 