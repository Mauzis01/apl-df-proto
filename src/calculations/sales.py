from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import logging

from ..models.dealer import DealerOutlet
from ..models.scenario import Scenario
from .financial import FinancialCalculator

class SalesCalculator:
    """
    Sales calculator for dealer feasibility analysis
    Calculates projected sales, revenues, and cash flows
    """
    
    @staticmethod
    def project_sales(
        dealer: DealerOutlet,
        scenario: Scenario
    ) -> Dict[str, Dict[int, Dict[str, float]]]:
        """
        Project sales volumes for all products over the analysis period
        
        Args:
            dealer: DealerOutlet object with initial sales data
            scenario: Scenario with growth rates and other parameters
            
        Returns:
            Dictionary with yearly sales projections for each product
        """
        years = range(scenario.analysis_years)
        
        # Initialize results dictionary
        sales_projection = {
            'pmg': {},
            'hsd': {},
            'hobc': {},
            'lube': {}
        }
        
        # Helper function to get growth rate
        def get_growth_rate(product: str, year: int) -> float:
            """Get the applicable growth rate for a product in a year"""
            # Check dealer-specific growth rate first
            if product == 'pmg' and year in dealer.pmg_growth_rate:
                return dealer.pmg_growth_rate[year]
            elif product == 'hsd' and year in dealer.hsd_growth_rate:
                return dealer.hsd_growth_rate[year]
            elif product == 'hobc' and year in dealer.hobc_growth_rate:
                return dealer.hobc_growth_rate[year]
            elif product == 'lube' and year in dealer.lube_growth_rate:
                return dealer.lube_growth_rate[year]
            
            # Fall back to scenario default growth rate
            return scenario.get_default_growth_rate(product, year)
        
        # Helper function to get margin
        def get_margin(product: str, year: int) -> float:
            """Get the applicable margin for a product in a year"""
            # Check dealer-specific margin first
            if product == 'pmg' and year in dealer.pmg_margin:
                return dealer.pmg_margin[year]
            elif product == 'hsd' and year in dealer.hsd_margin:
                return dealer.hsd_margin[year]
            elif product == 'hobc' and year in dealer.hobc_margin:
                return dealer.hobc_margin[year]
            elif product == 'lube' and year in dealer.lube_margin:
                return dealer.lube_margin[year]
            
            # Fall back to scenario default margin
            return scenario.get_default_margin(product, year)
        
        # Project sales for each product
        for year in years:
            # PMG sales
            if year == 0:
                sales_projection['pmg'][year] = dealer.pmg_sales * 365  # Annual sales
            else:
                growth_rate = get_growth_rate('pmg', year)
                previous_sales = sales_projection['pmg'][year-1]
                sales_projection['pmg'][year] = previous_sales * (1 + growth_rate)
            
            # HSD sales
            if year == 0:
                sales_projection['hsd'][year] = dealer.hsd_sales * 365  # Annual sales
            else:
                growth_rate = get_growth_rate('hsd', year)
                previous_sales = sales_projection['hsd'][year-1]
                sales_projection['hsd'][year] = previous_sales * (1 + growth_rate)
            
            # HOBC sales
            if year == 0:
                sales_projection['hobc'][year] = dealer.hobc_sales * 365  # Annual sales
            else:
                growth_rate = get_growth_rate('hobc', year)
                previous_sales = sales_projection['hobc'][year-1]
                sales_projection['hobc'][year] = previous_sales * (1 + growth_rate)
            
            # Lube sales
            if year == 0:
                sales_projection['lube'][year] = dealer.lube_sales * 365  # Annual sales
            else:
                growth_rate = get_growth_rate('lube', year)
                previous_sales = sales_projection['lube'][year-1]
                sales_projection['lube'][year] = previous_sales * (1 + growth_rate)
        
        return sales_projection
    
    @staticmethod
    def calculate_revenue(
        sales_projection: Dict[str, Dict[int, float]],
        dealer: DealerOutlet,
        scenario: Scenario
    ) -> Dict[str, Dict[int, float]]:
        """
        Calculate revenue from sales projections
        
        Args:
            sales_projection: Sales projections from project_sales
            dealer: DealerOutlet object
            scenario: Scenario object
            
        Returns:
            Dictionary with yearly revenue projections for each product
        """
        years = range(scenario.analysis_years)
        
        # Initialize results dictionary
        revenue_projection = {
            'pmg': {},
            'hsd': {},
            'hobc': {},
            'lube': {},
            'total': {}
        }
        
        # Helper function to get margin
        def get_margin(product: str, year: int) -> float:
            """Get the applicable margin for a product in a year"""
            # Check dealer-specific margin first
            if product == 'pmg' and year in dealer.pmg_margin:
                return dealer.pmg_margin[year]
            elif product == 'hsd' and year in dealer.hsd_margin:
                return dealer.hsd_margin[year]
            elif product == 'hobc' and year in dealer.hobc_margin:
                return dealer.hobc_margin[year]
            elif product == 'lube' and year in dealer.lube_margin:
                return dealer.lube_margin[year]
            
            # Fall back to scenario default margin
            return scenario.get_default_margin(product, year)
        
        # Calculate revenue for each product
        for year in years:
            # PMG revenue
            pmg_sales = sales_projection['pmg'].get(year, 0)
            pmg_margin = get_margin('pmg', year)
            revenue_projection['pmg'][year] = pmg_sales * pmg_margin
            
            # HSD revenue
            hsd_sales = sales_projection['hsd'].get(year, 0)
            hsd_margin = get_margin('hsd', year)
            revenue_projection['hsd'][year] = hsd_sales * hsd_margin
            
            # HOBC revenue
            hobc_sales = sales_projection['hobc'].get(year, 0)
            hobc_margin = get_margin('hobc', year)
            revenue_projection['hobc'][year] = hobc_sales * hobc_margin
            
            # Lube revenue
            lube_sales = sales_projection['lube'].get(year, 0)
            lube_margin = get_margin('lube', year)
            revenue_projection['lube'][year] = lube_sales * lube_margin
            
            # Total revenue
            revenue_projection['total'][year] = (
                revenue_projection['pmg'][year] +
                revenue_projection['hsd'][year] +
                revenue_projection['hobc'][year] +
                revenue_projection['lube'][year]
            )
        
        return revenue_projection
    
    @staticmethod
    def calculate_operating_costs(
        dealer: DealerOutlet,
        scenario: Scenario
    ) -> Dict[int, float]:
        """
        Calculate operating costs over the analysis period
        
        Args:
            dealer: DealerOutlet object
            scenario: Scenario object
            
        Returns:
            Dictionary with yearly operating costs
        """
        years = range(scenario.analysis_years)
        
        # Initialize results dictionary
        operating_costs = {}
        
        # Calculate base operating cost
        base_operating_cost = sum(dealer.operating_costs.values())
        
        # Project operating costs with inflation
        for year in years:
            operating_costs[year] = base_operating_cost * (1 + scenario.inflation_rate) ** year
            
        return operating_costs
    
    @staticmethod
    def calculate_insurance(
        dealer: DealerOutlet,
        scenario: Scenario
    ) -> Dict[int, float]:
        """
        Calculate insurance costs over the analysis period
        
        Args:
            dealer: DealerOutlet object
            scenario: Scenario object
            
        Returns:
            Dictionary with yearly insurance costs
        """
        years = range(scenario.analysis_years)
        
        # Initialize results dictionary
        insurance_costs = {}
        
        # Calculate base insurance cost
        total_assets = dealer.initial_investment
        insurance_rate = sum(dealer.insurance_rates.values()) if dealer.insurance_rates else 0.01
        base_insurance_cost = total_assets * insurance_rate
        
        # Project insurance costs with inflation
        for year in years:
            insurance_costs[year] = base_insurance_cost * (1 + scenario.inflation_rate) ** year
            
        return insurance_costs
    
    @staticmethod
    def calculate_cash_flows(
        dealer: DealerOutlet,
        scenario: Scenario
    ) -> Tuple[List[float], Dict[str, Any]]:
        """
        Calculate cash flows over the analysis period
        
        Args:
            dealer: DealerOutlet object
            scenario: Scenario object
            
        Returns:
            Tuple of (cash_flows, yearly_data)
        """
        # Project sales, revenue, costs
        sales_projection = SalesCalculator.project_sales(dealer, scenario)
        revenue_projection = SalesCalculator.calculate_revenue(sales_projection, dealer, scenario)
        operating_costs = SalesCalculator.calculate_operating_costs(dealer, scenario)
        insurance_costs = SalesCalculator.calculate_insurance(dealer, scenario)
        
        # Initialize results
        cash_flows = []
        yearly_data = {
            'pmg_sales': {},
            'hsd_sales': {},
            'hobc_sales': {},
            'lube_sales': {},
            'pmg_revenue': {},
            'hsd_revenue': {},
            'hobc_revenue': {},
            'lube_revenue': {},
            'total_revenue': {},
            'operating_costs': {},
            'insurance': {},
            'ebitda': {},  # Earnings Before Interest, Taxes, Depreciation, Amortization
            'taxes': {},
            'net_profit': {}
        }
        
        # First year cash flow is negative (investment)
        cash_flows.append(-dealer.initial_investment)
        
        # Calculate cash flows for each year
        for year in range(scenario.analysis_years):
            if year == 0:
                # Year 0 is just the initial investment
                continue
                
            # Sales data
            yearly_data['pmg_sales'][year] = sales_projection['pmg'].get(year, 0)
            yearly_data['hsd_sales'][year] = sales_projection['hsd'].get(year, 0)
            yearly_data['hobc_sales'][year] = sales_projection['hobc'].get(year, 0)
            yearly_data['lube_sales'][year] = sales_projection['lube'].get(year, 0)
            
            # Revenue data
            yearly_data['pmg_revenue'][year] = revenue_projection['pmg'].get(year, 0)
            yearly_data['hsd_revenue'][year] = revenue_projection['hsd'].get(year, 0)
            yearly_data['hobc_revenue'][year] = revenue_projection['hobc'].get(year, 0)
            yearly_data['lube_revenue'][year] = revenue_projection['lube'].get(year, 0)
            yearly_data['total_revenue'][year] = revenue_projection['total'].get(year, 0)
            
            # Costs data
            yearly_data['operating_costs'][year] = operating_costs.get(year, 0)
            yearly_data['insurance'][year] = insurance_costs.get(year, 0)
            
            # Calculate EBITDA
            yearly_data['ebitda'][year] = (
                yearly_data['total_revenue'][year] -
                yearly_data['operating_costs'][year] -
                yearly_data['insurance'][year]
            )
            
            # Calculate taxes
            yearly_data['taxes'][year] = yearly_data['ebitda'][year] * scenario.tax_rate
            
            # Calculate net profit
            yearly_data['net_profit'][year] = yearly_data['ebitda'][year] - yearly_data['taxes'][year]
            
            # Cash flow for the year
            cash_flows.append(yearly_data['net_profit'][year])
        
        return cash_flows, yearly_data
    
    @staticmethod
    def run_scenario(
        dealer: DealerOutlet,
        scenario: Scenario
    ) -> Dict[str, Any]:
        """
        Run a complete scenario and calculate financial metrics
        
        Args:
            dealer: DealerOutlet object
            scenario: Scenario object
            
        Returns:
            Dictionary with financial metrics and projections
        """
        try:
            # Ensure analysis_years is an integer
            if not hasattr(scenario, 'analysis_years') or not isinstance(scenario.analysis_years, int):
                logging.warning(f"Invalid analysis_years: {scenario.analysis_years}, using default of 15")
                scenario.analysis_years = 15
            
            # Ensure growth rates and margins are structured correctly
            for product in ['pmg', 'hsd', 'hobc', 'lube']:
                if product not in scenario.default_growth_rates:
                    scenario.default_growth_rates[product] = {1: 0.05}
                elif not isinstance(scenario.default_growth_rates[product], dict):
                    try:
                        scenario.default_growth_rates[product] = {1: float(scenario.default_growth_rates[product])}
                    except (TypeError, ValueError):
                        scenario.default_growth_rates[product] = {1: 0.05}
                
                if product not in scenario.default_margins:
                    default_values = {'pmg': 5.0, 'hsd': 4.0, 'hobc': 6.0, 'lube': 100.0}
                    scenario.default_margins[product] = {1: default_values.get(product, 5.0)}
                elif not isinstance(scenario.default_margins[product], dict):
                    try:
                        scenario.default_margins[product] = {1: float(scenario.default_margins[product])}
                    except (TypeError, ValueError):
                        default_values = {'pmg': 5.0, 'hsd': 4.0, 'hobc': 6.0, 'lube': 100.0}
                        scenario.default_margins[product] = {1: default_values.get(product, 5.0)}
            
            years = scenario.analysis_years
            
            # Calculate product sales using the new methods
            pmg_sales = SalesCalculator.calculate_product_sales(dealer.pmg_sales, scenario.default_growth_rates.get('pmg', {1: 0.05}), years)
            hsd_sales = SalesCalculator.calculate_product_sales(dealer.hsd_sales, scenario.default_growth_rates.get('hsd', {1: 0.05}), years)
            hobc_sales = SalesCalculator.calculate_product_sales(dealer.hobc_sales, scenario.default_growth_rates.get('hobc', {1: 0.06}), years)
            lube_sales = SalesCalculator.calculate_product_sales(dealer.lube_sales, scenario.default_growth_rates.get('lube', {1: 0.01}), years)
            
            # Calculate product revenues using the new methods
            pmg_revenue = SalesCalculator.calculate_product_revenue(pmg_sales, scenario.default_margins.get('pmg', {1: 5.0}), years, scenario.inflation_rate)
            hsd_revenue = SalesCalculator.calculate_product_revenue(hsd_sales, scenario.default_margins.get('hsd', {1: 4.0}), years, scenario.inflation_rate)
            hobc_revenue = SalesCalculator.calculate_product_revenue(hobc_sales, scenario.default_margins.get('hobc', {1: 6.0}), years, scenario.inflation_rate)
            lube_revenue = SalesCalculator.calculate_product_revenue(lube_sales, scenario.default_margins.get('lube', {1: 100.0}), years, scenario.inflation_rate)
            
            # Calculate total revenue
            total_revenue = {}
            for year in range(years + 1):
                total_revenue[year] = (
                    pmg_revenue.get(year, 0) +
                    hsd_revenue.get(year, 0) +
                    hobc_revenue.get(year, 0) +
                    lube_revenue.get(year, 0)
                )
            
            # Calculate operating costs with inflation
            operating_costs = {}
            monthly_costs = dealer.operating_costs
            for year in range(years + 1):
                if year == 0:
                    operating_costs[year] = 0  # No operating costs in year 0 (investment year)
                else:
                    inflation_factor = (1 + scenario.inflation_rate) ** (year - 1)
                    operating_costs[year] = monthly_costs * 12 * inflation_factor
            
            # Calculate maintenance expenses
            maintenance = {}
            for year in range(years + 1):
                maintenance[year] = 0  # Initialize with 0
                
                # Signage maintenance
                if year > 0 and year % scenario.signage_maintenance_year == 0 and year <= years:
                    inflation_factor = (1 + scenario.inflation_rate) ** (year - 1)
                    maintenance[year] += scenario.signage_maintenance * inflation_factor
                
                # Other maintenance
                if year == scenario.other_maintenance_year:
                    inflation_factor = (1 + scenario.inflation_rate) ** (year - 1)
                    maintenance[year] += scenario.other_maintenance * inflation_factor
            
            # Calculate insurance costs
            insurance = {}
            insurance_rate = scenario.insurance_rates.get('property', 0.01)  # Default 1%
            for year in range(years + 1):
                if year == 0:
                    insurance[year] = 0  # No insurance in year 0
                else:
                    inflation_factor = (1 + scenario.inflation_rate) ** (year - 1)
                    insurance[year] = dealer.initial_investment * insurance_rate * inflation_factor
            
            # Calculate rental income if any
            rental_income = {}
            for year in range(years + 1):
                rental_income[year] = 0  # Default to 0
                
                # If dealer has rental streams, calculate income
                if hasattr(dealer, 'rental_streams') and dealer.rental_streams:
                    for stream in dealer.rental_streams:
                        start_year = stream.get('start_year', 1)
                        end_year = stream.get('end_year', years)
                        monthly_rent = stream.get('monthly_rent', 0)
                        
                        if start_year <= year <= end_year:
                            inflation_factor = (1 + scenario.inflation_rate) ** (year - 1)
                            rental_income[year] += monthly_rent * 12 * inflation_factor
            
            # Calculate net cash flows
            cash_flows = []
            # Initial investment (negative cash flow at year 0)
            cash_flows.append(-dealer.initial_investment)
            
            # Cash flows for years 1 to analysis_years
            for year in range(1, years + 1):
                # Revenue - costs
                cf = (total_revenue.get(year, 0) - 
                      operating_costs.get(year, 0) - 
                      maintenance.get(year, 0) - 
                      insurance.get(year, 0) +
                      rental_income.get(year, 0))
                
                # Apply tax rate
                taxable_income = max(0, cf)  # Only positive income is taxable
                tax = taxable_income * scenario.tax_rate
                cf -= tax
                
                cash_flows.append(cf)
            
            # Calculate financial metrics
            npv, irr, payback_period, discounted_cash_flows, cumulative_cash_flows, mirr = (
                FinancialCalculator.calculate_metrics(cash_flows, scenario.discount_rate)
            )
            
            # Organize yearly data for the UI
            yearly_data = {
                "pmg_sales": pmg_sales,
                "hsd_sales": hsd_sales,
                "hobc_sales": hobc_sales,
                "lube_sales": lube_sales,
                "pmg_revenue": pmg_revenue,
                "hsd_revenue": hsd_revenue,
                "hobc_revenue": hobc_revenue,
                "lube_revenue": lube_revenue,
                "total_revenue": total_revenue,
                "operating_costs": operating_costs,
                "maintenance": maintenance,
                "insurance": insurance,
                "rental_income": rental_income
            }
            
            # Return comprehensive results
            results = {
                "npv": npv,
                "irr": irr,
                "payback_period": payback_period,
                "mirr": mirr,
                "cash_flows": cash_flows,
                "discounted_cash_flows": discounted_cash_flows,
                "cumulative_cash_flows": cumulative_cash_flows,
                "yearly_data": yearly_data,
                "initial_investment": dealer.initial_investment,
                "years": years
            }
            
            return results
        except Exception as e:
            logging.error(f"Error in SalesCalculator.run_scenario: {str(e)}")
            logging.error(f"Details: dealer={dealer.name}, scenario={scenario.name}")
            raise

    @classmethod
    def calculate_product_sales(cls, base_sales, growth_rates, years):
        """
        Calculate product sales over time based on growth rates.
        
        Parameters:
        - base_sales: Base daily sales (liters/day)
        - growth_rates: Dictionary mapping year to growth rate (as a decimal)
        - years: Number of years to project
        
        Returns:
        - Dictionary mapping year index to annual sales volume
        """
        annual_base = base_sales * 365  # Convert daily to annual
        yearly_sales = {}
        
        # Ensure growth_rates is a dictionary
        if not isinstance(growth_rates, dict):
            # If it's a single value, apply it to all years
            try:
                fixed_rate = float(growth_rates)
                growth_rates = {year: fixed_rate for year in range(1, years + 1)}
            except (ValueError, TypeError):
                # Default to 5% if conversion fails
                growth_rates = {year: 0.05 for year in range(1, years + 1)}
        
        # Create a sorted list of years that have defined growth rates
        defined_years = sorted([int(year) for year in growth_rates.keys() if int(year) <= years])
        
        if not defined_years:
            # No valid years found, use default 5%
            defined_years = [1]
            growth_rates = {1: 0.05}
        
        # Fill in missing years using linear interpolation
        all_growth_rates = {}
        
        # For each year in the projection period
        for year in range(1, years + 1):
            if year in growth_rates:
                # Use the defined rate
                all_growth_rates[year] = float(growth_rates[year])
            else:
                # Find surrounding defined years for interpolation
                lower_year = max([y for y in defined_years if y < year], default=None)
                upper_year = min([y for y in defined_years if y > year], default=None)
                
                if lower_year is None:
                    # If no lower year, use the lowest defined year
                    all_growth_rates[year] = float(growth_rates[defined_years[0]])
                elif upper_year is None:
                    # If no upper year, use the highest defined year
                    all_growth_rates[year] = float(growth_rates[defined_years[-1]])
                else:
                    # Interpolate between lower and upper years
                    lower_rate = float(growth_rates[lower_year])
                    upper_rate = float(growth_rates[upper_year])
                    ratio = (year - lower_year) / (upper_year - lower_year)
                    interpolated_rate = lower_rate + (upper_rate - lower_rate) * ratio
                    all_growth_rates[year] = interpolated_rate
        
        # Calculate sales for year 0 (base year)
        yearly_sales[0] = annual_base
        
        # Calculate sales for remaining years using compounded growth
        for year in range(1, years + 1):
            previous_sales = yearly_sales[year - 1]
            growth_rate = all_growth_rates[year]
            yearly_sales[year] = previous_sales * (1 + growth_rate)
        
        return yearly_sales

    @classmethod
    def calculate_product_revenue(cls, sales_volumes, margins, years, inflation_rate=0.03):
        """
        Calculate product revenue over time based on sales volumes and margins.
        
        Parameters:
        - sales_volumes: Dictionary mapping year to sales volume
        - margins: Dictionary mapping year to margin (PKR/liter)
        - years: Number of years to project
        - inflation_rate: Annual inflation rate (default: 3%)
        
        Returns:
        - Dictionary mapping year index to annual revenue
        """
        yearly_revenue = {}
        
        # Ensure margins is a dictionary
        if not isinstance(margins, dict):
            # If it's a single value, apply it to all years
            try:
                fixed_margin = float(margins)
                margins = {year: fixed_margin for year in range(1, years + 1)}
            except (ValueError, TypeError):
                # Default to 5 PKR if conversion fails
                margins = {year: 5.0 for year in range(1, years + 1)}
        
        # Create a sorted list of years that have defined margins
        defined_years = sorted([int(year) for year in margins.keys() if int(year) <= years])
        
        if not defined_years:
            # No valid years found, use default 5 PKR
            defined_years = [1]
            margins = {1: 5.0}
        
        # Fill in missing years using linear interpolation
        all_margins = {}
        
        # For each year in the projection period
        for year in range(1, years + 1):
            if year in margins:
                # Use the defined margin
                all_margins[year] = float(margins[year])
            else:
                # Find surrounding defined years for interpolation
                lower_year = max([y for y in defined_years if y < year], default=None)
                upper_year = min([y for y in defined_years if y > year], default=None)
                
                if lower_year is None:
                    # If no lower year, use the lowest defined year
                    all_margins[year] = float(margins[defined_years[0]])
                elif upper_year is None:
                    # If no upper year, use the highest defined year
                    all_margins[year] = float(margins[defined_years[-1]])
                else:
                    # Interpolate between lower and upper years
                    lower_margin = float(margins[lower_year])
                    upper_margin = float(margins[upper_year])
                    ratio = (year - lower_year) / (upper_year - lower_year)
                    interpolated_margin = lower_margin + (upper_margin - lower_margin) * ratio
                    all_margins[year] = interpolated_margin
        
        # Calculate revenue for each year
        for year in range(years + 1):
            if year == 0:
                # Year 0 uses first year's margin without inflation
                margin = all_margins.get(1, 5.0)
            else:
                # Apply inflation to the margin for this year
                base_margin = all_margins.get(year, all_margins.get(1, 5.0))
                margin = base_margin * (1 + inflation_rate) ** (year - 1)
            
            sales = sales_volumes.get(year, 0)
            yearly_revenue[year] = sales * margin
        
        return yearly_revenue 