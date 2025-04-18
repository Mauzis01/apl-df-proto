"""
Utility functions for the dealer feasibility application.
"""

import inspect
import logging
from typing import Dict, Any, Optional

# Import models - using relative imports
from src.models.dealer import DealerOutlet
from src.models.scenario import Scenario

def safely_create_scenario(**kwargs) -> Optional[Scenario]:
    """
    Safely create a Scenario with only the valid parameters
    for the Scenario class.
    
    Returns:
        Scenario: A new scenario instance
    """
    # Get valid parameters for Scenario class
    valid_params = set(inspect.signature(Scenario.__init__).parameters.keys()) - {'self'}
    
    # Filter kwargs to only include valid parameters
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}
    
    # Ensure growth rates and margins are properly formatted
    if 'default_growth_rates' in filtered_kwargs:
        growth_rates = filtered_kwargs['default_growth_rates']
        # Ensure it's a dictionary
        if not isinstance(growth_rates, dict):
            logging.error(f"Growth rates is not a dictionary: {type(growth_rates)}")
            # Initialize as empty dict if not correct type
            filtered_kwargs['default_growth_rates'] = {}
    
    if 'default_margins' in filtered_kwargs:
        margins = filtered_kwargs['default_margins']
        # Ensure it's a dictionary
        if not isinstance(margins, dict):
            logging.error(f"Margins is not a dictionary: {type(margins)}")
            # Initialize as empty dict if not correct type
            filtered_kwargs['default_margins'] = {}
    
    # Create the scenario
    scenario = Scenario(**filtered_kwargs)
    
    # Verify and fix growth rates structure if needed
    if hasattr(scenario, 'default_growth_rates'):
        growth_rates = scenario.default_growth_rates
        if not isinstance(growth_rates, dict):
            scenario.default_growth_rates = {}
            logging.warning("Fixed scenario.default_growth_rates to be a dictionary")
        else:
            # Ensure each product has a dictionary
            for product in ['pmg', 'hsd', 'hobc', 'lube']:
                if product not in growth_rates:
                    growth_rates[product] = {}
                elif not isinstance(growth_rates[product], dict):
                    growth_rates[product] = {}
    
    # Verify and fix margins structure if needed
    if hasattr(scenario, 'default_margins'):
        margins = scenario.default_margins
        if not isinstance(margins, dict):
            scenario.default_margins = {}
            logging.warning("Fixed scenario.default_margins to be a dictionary")
        else:
            # Ensure each product has a dictionary
            for product in ['pmg', 'hsd', 'hobc', 'lube']:
                if product not in margins:
                    margins[product] = {}
                elif not isinstance(margins[product], dict):
                    margins[product] = {}
    
    return scenario

def safely_create_dealer(**kwargs) -> Optional[DealerOutlet]:
    """
    Safely create a DealerOutlet with only the valid parameters
    for the DealerOutlet class.
    
    Returns:
        DealerOutlet: A new dealer instance
    """
    # Get valid parameters for DealerOutlet class
    valid_params = set(inspect.signature(DealerOutlet.__init__).parameters.keys()) - {'self'}
    
    # Filter kwargs to only include valid parameters
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}
    
    # Ensure investment_items is a list
    if 'investment_items' in filtered_kwargs and not isinstance(filtered_kwargs['investment_items'], list):
        if filtered_kwargs['investment_items'] is None:
            filtered_kwargs['investment_items'] = []
        else:
            logging.warning(f"investment_items is not a list: {type(filtered_kwargs['investment_items'])}")
            try:
                # Try to convert to list if possible
                filtered_kwargs['investment_items'] = list(filtered_kwargs['investment_items'])
            except:
                filtered_kwargs['investment_items'] = []
    
    # Create the dealer
    dealer = DealerOutlet(**filtered_kwargs)
    logging.info(f"Successfully created dealer: {dealer.name}")
    return dealer

def test_supabase_connection():
    """
    Test connection to Supabase and verify database structure.
    
    Returns:
        dict: A status report of the test
    """
    from src.database.supabase_config import get_supabase_client
    import logging
    
    results = {
        'connection': False,
        'tables': {},
        'error': None
    }
    
    try:
        # Try to get Supabase client
        supabase = get_supabase_client()
        
        # Check connection by fetching a simple query
        response = supabase.from_('dealers').select('id').limit(1).execute()
        results['connection'] = True
        
        # Check if all tables exist
        tables = [
            'dealers', 
            'investment_items', 
            'scenarios', 
            'growth_rates', 
            'margins', 
            'calculation_results'
        ]
        
        for table in tables:
            try:
                response = supabase.from_(table).select('id').limit(1).execute()
                results['tables'][table] = {
                    'exists': True,
                    'count': len(response.data)
                }
            except Exception as e:
                results['tables'][table] = {
                    'exists': False,
                    'error': str(e)
                }
        
        logging.info(f"Supabase connection test successful: {results}")
        
    except Exception as e:
        results['error'] = str(e)
        logging.error(f"Supabase connection test failed: {str(e)}")
    
    return results

# Test function
if __name__ == "__main__":
    # Set up basic logging
    import os
    os.makedirs("logs", exist_ok=True)
    
    logging.basicConfig(
        filename="logs/utils_test.log",
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    try:
        # Test scenario creation
        test_scenario = safely_create_scenario(name="Test Scenario")
        print(f"Successfully created scenario: {test_scenario.name}")
        
        # Test dealer creation
        test_dealer = safely_create_dealer(name="Test Dealer", location="Test Location")
        print(f"Successfully created dealer: {test_dealer.name}")
        
        print("All tests passed!")
    except Exception as e:
        print(f"Test failed: {str(e)}")
        logging.error(f"Test failed: {str(e)}")
        raise 