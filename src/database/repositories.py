import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..models.dealer import DealerOutlet
from ..models.scenario import Scenario
from .supabase_config import get_supabase_client

class DealerRepository:
    """Repository for dealer data in Supabase"""
    
    @staticmethod
    def save(dealer: DealerOutlet) -> str:
        """
        Save dealer to Supabase.
        Returns the dealer ID.
        """
        try:
            supabase = get_supabase_client()
            
            # Prepare data for Supabase
            dealer_data = {
                "name": dealer.name,
                "location": dealer.location,
                "district": dealer.district if hasattr(dealer, 'district') else None,
                "feeding_point": dealer.feeding_point if hasattr(dealer, 'feeding_point') else None,
                "area_executive": dealer.area_executive if hasattr(dealer, 'area_executive') else None,
                "referred_by": dealer.referred_by if hasattr(dealer, 'referred_by') else None,
                "pmg_sales": float(dealer.pmg_sales) if hasattr(dealer, 'pmg_sales') else 0,
                "hsd_sales": float(dealer.hsd_sales) if hasattr(dealer, 'hsd_sales') else 0,
                "hobc_sales": float(dealer.hobc_sales) if hasattr(dealer, 'hobc_sales') else 0,
                "lube_sales": float(dealer.lube_sales) if hasattr(dealer, 'lube_sales') else 0,
                "initial_investment": float(dealer.initial_investment) if hasattr(dealer, 'initial_investment') else 0,
                "operating_costs": float(dealer.operating_costs) if hasattr(dealer, 'operating_costs') else 0,
                "rental_streams": json.dumps(dealer.rental_streams) if hasattr(dealer, 'rental_streams') and dealer.rental_streams else None,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Insert or update dealer
            if hasattr(dealer, 'id') and dealer.id:
                response = supabase.table('dealers').update(dealer_data).eq('id', dealer.id).execute()
                dealer_id = dealer.id
            else:
                response = supabase.table('dealers').insert(dealer_data).execute()
                dealer_id = response.data[0]['id']
            
            # Save investment items if they exist
            if hasattr(dealer, 'investment_items') and dealer.investment_items:
                # Delete existing items for this dealer
                if hasattr(dealer, 'id') and dealer.id:
                    supabase.table('investment_items').delete().eq('dealer_id', dealer_id).execute()
                
                # Insert new items
                for item in dealer.investment_items:
                    item_data = {
                        "dealer_id": dealer_id,
                        "name": item['name'],
                        "cost": float(item['cost']),
                        "quantity": int(item['quantity'])
                    }
                    supabase.table('investment_items').insert(item_data).execute()
            
            logging.info(f"Saved dealer {dealer.name} with ID {dealer_id}")
            return dealer_id
            
        except Exception as e:
            logging.error(f"Error saving dealer: {str(e)}")
            raise
    
    @staticmethod
    def get_all() -> List[Dict]:
        """
        Get all dealers from Supabase.
        Returns a list of dealer dictionaries.
        """
        try:
            supabase = get_supabase_client()
            response = supabase.table('dealers').select('*').execute()
            return response.data
        except Exception as e:
            logging.error(f"Error getting all dealers: {str(e)}")
            return []
    
    @staticmethod
    def get_by_id(dealer_id: str) -> Optional[DealerOutlet]:
        """
        Get dealer by ID.
        Returns a DealerOutlet object or None if not found.
        """
        try:
            supabase = get_supabase_client()
            
            # Get dealer data
            response = supabase.table('dealers').select('*').eq('id', dealer_id).execute()
            if not response.data:
                logging.warning(f"Dealer with ID {dealer_id} not found")
                return None
            
            dealer_data = response.data[0]
            
            # Get investment items
            items_response = supabase.table('investment_items').select('*').eq('dealer_id', dealer_id).execute()
            investment_items = items_response.data if items_response.data else []
            
            # Create and return dealer object
            dealer = DealerOutlet(
                name=dealer_data['name'],
                location=dealer_data['location']
            )
            
            # Add id
            dealer.id = dealer_data['id']
            
            # Add other attributes
            for key, value in dealer_data.items():
                if key not in ['id', 'name', 'location', 'created_at', 'updated_at', 'rental_streams']:
                    if value is not None:
                        setattr(dealer, key, value)
            
            # Parse rental streams if present
            if dealer_data.get('rental_streams'):
                try:
                    dealer.rental_streams = json.loads(dealer_data['rental_streams'])
                except:
                    dealer.rental_streams = {}
            
            # Add investment items
            if investment_items:
                dealer.investment_items = [{
                    'name': item['name'],
                    'cost': item['cost'],
                    'quantity': item['quantity']
                } for item in investment_items]
            
            return dealer
            
        except Exception as e:
            logging.error(f"Error getting dealer by ID: {str(e)}")
            return None
    
    @staticmethod
    def delete(dealer_id: str) -> bool:
        """
        Delete dealer by ID.
        Returns True if successful, False otherwise.
        """
        try:
            supabase = get_supabase_client()
            response = supabase.table('dealers').delete().eq('id', dealer_id).execute()
            logging.info(f"Deleted dealer with ID {dealer_id}")
            return True
        except Exception as e:
            logging.error(f"Error deleting dealer: {str(e)}")
            return False


class ScenarioRepository:
    """Repository for scenario data in Supabase"""
    
    @staticmethod
    def save(scenario: Scenario) -> str:
        """
        Save scenario to Supabase.
        Returns the scenario ID.
        """
        try:
            supabase = get_supabase_client()
            
            # Prepare scenario data
            scenario_data = {
                "name": scenario.name,
                "description": scenario.description if hasattr(scenario, 'description') else None,
                "discount_rate": float(scenario.discount_rate) if hasattr(scenario, 'discount_rate') else 0.1,
                "inflation_rate": float(scenario.inflation_rate) if hasattr(scenario, 'inflation_rate') else 0.05,
                "tax_rate": float(scenario.tax_rate) if hasattr(scenario, 'tax_rate') else 0.35,
                "analysis_years": int(scenario.analysis_years) if hasattr(scenario, 'analysis_years') else 10,
                "signage_maintenance": float(scenario.signage_maintenance) if hasattr(scenario, 'signage_maintenance') else 0,
                "signage_maintenance_year": int(scenario.signage_maintenance_year) if hasattr(scenario, 'signage_maintenance_year') else 3,
                "other_maintenance": float(scenario.other_maintenance) if hasattr(scenario, 'other_maintenance') else 0,
                "other_maintenance_year": int(scenario.other_maintenance_year) if hasattr(scenario, 'other_maintenance_year') else 3,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Insert or update scenario
            if hasattr(scenario, 'id') and scenario.id:
                response = supabase.table('scenarios').update(scenario_data).eq('id', scenario.id).execute()
                scenario_id = scenario.id
            else:
                response = supabase.table('scenarios').insert(scenario_data).execute()
                scenario_id = response.data[0]['id']
            
            # Save growth rates
            if hasattr(scenario, 'default_growth_rates') and scenario.default_growth_rates:
                # Delete existing growth rates for this scenario
                if hasattr(scenario, 'id') and scenario.id:
                    supabase.table('growth_rates').delete().eq('scenario_id', scenario_id).execute()
                
                # Insert new growth rates
                for product, years in scenario.default_growth_rates.items():
                    if isinstance(years, dict):
                        for year, rate in years.items():
                            growth_data = {
                                "scenario_id": scenario_id,
                                "product": product,
                                "year": int(year),
                                "rate": float(rate)
                            }
                            supabase.table('growth_rates').insert(growth_data).execute()
            
            # Save margins
            if hasattr(scenario, 'default_margins') and scenario.default_margins:
                # Delete existing margins for this scenario
                if hasattr(scenario, 'id') and scenario.id:
                    supabase.table('margins').delete().eq('scenario_id', scenario_id).execute()
                
                # Insert new margins
                for product, years in scenario.default_margins.items():
                    if isinstance(years, dict):
                        for year, margin in years.items():
                            margin_data = {
                                "scenario_id": scenario_id,
                                "product": product,
                                "year": int(year),
                                "margin": float(margin)
                            }
                            supabase.table('margins').insert(margin_data).execute()
            
            logging.info(f"Saved scenario {scenario.name} with ID {scenario_id}")
            return scenario_id
            
        except Exception as e:
            logging.error(f"Error saving scenario: {str(e)}")
            raise
    
    @staticmethod
    def get_all() -> List[Dict]:
        """
        Get all scenarios from Supabase.
        Returns a list of scenario dictionaries.
        """
        try:
            supabase = get_supabase_client()
            response = supabase.table('scenarios').select('*').execute()
            return response.data
        except Exception as e:
            logging.error(f"Error getting all scenarios: {str(e)}")
            return []
    
    @staticmethod
    def get_by_id(scenario_id: str) -> Optional[Scenario]:
        """
        Get scenario by ID.
        Returns a Scenario object or None if not found.
        """
        try:
            supabase = get_supabase_client()
            
            # Get scenario data
            response = supabase.table('scenarios').select('*').eq('id', scenario_id).execute()
            if not response.data:
                logging.warning(f"Scenario with ID {scenario_id} not found")
                return None
            
            scenario_data = response.data[0]
            
            # Get growth rates
            growth_response = supabase.table('growth_rates').select('*').eq('scenario_id', scenario_id).execute()
            growth_rates_data = growth_response.data if growth_response.data else []
            
            # Get margins
            margins_response = supabase.table('margins').select('*').eq('scenario_id', scenario_id).execute()
            margins_data = margins_response.data if margins_response.data else []
            
            # Prepare growth rates dictionary
            growth_rates = {}
            for item in growth_rates_data:
                product = item['product']
                year = item['year']
                rate = item['rate']
                
                if product not in growth_rates:
                    growth_rates[product] = {}
                
                growth_rates[product][year] = rate
            
            # Prepare margins dictionary
            margins = {}
            for item in margins_data:
                product = item['product']
                year = item['year']
                margin = item['margin']
                
                if product not in margins:
                    margins[product] = {}
                
                margins[product][year] = margin
            
            # Create scenario
            scenario = Scenario(
                name=scenario_data['name'],
                description=scenario_data.get('description'),
                discount_rate=scenario_data.get('discount_rate', 0.1),
                inflation_rate=scenario_data.get('inflation_rate', 0.05),
                tax_rate=scenario_data.get('tax_rate', 0.35),
                analysis_years=scenario_data.get('analysis_years', 10),
                default_growth_rates=growth_rates,
                default_margins=margins,
                signage_maintenance=scenario_data.get('signage_maintenance'),
                signage_maintenance_year=scenario_data.get('signage_maintenance_year'),
                other_maintenance=scenario_data.get('other_maintenance'),
                other_maintenance_year=scenario_data.get('other_maintenance_year')
            )
            
            # Add ID
            scenario.id = scenario_id
            
            return scenario
            
        except Exception as e:
            logging.error(f"Error getting scenario by ID: {str(e)}")
            return None
    
    @staticmethod
    def delete(scenario_id: str) -> bool:
        """
        Delete scenario by ID.
        Returns True if successful, False otherwise.
        """
        try:
            supabase = get_supabase_client()
            response = supabase.table('scenarios').delete().eq('id', scenario_id).execute()
            logging.info(f"Deleted scenario with ID {scenario_id}")
            return True
        except Exception as e:
            logging.error(f"Error deleting scenario: {str(e)}")
            return False


class ResultsRepository:
    """Repository for calculation results in Supabase"""
    
    @staticmethod
    def save_result(dealer_id: str, scenario_id: str, results: Dict) -> str:
        """
        Save calculation results to Supabase.
        Returns the result ID.
        """
        try:
            supabase = get_supabase_client()
            
            # Prepare data
            result_data = {
                "dealer_id": dealer_id,
                "scenario_id": scenario_id,
                "npv": float(results.get('npv', 0)),
                "irr": float(results.get('irr', 0)),
                "payback_period": float(results.get('payback_period', 0)),
                "cash_flows": json.dumps(results.get('cash_flows', [])),
                "yearly_data": json.dumps(results.get('yearly_data', {})),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Check if result already exists
            existing = supabase.table('calculation_results').select('id').eq('dealer_id', dealer_id).eq('scenario_id', scenario_id).execute()
            
            if existing.data:
                # Update existing result
                result_id = existing.data[0]['id']
                response = supabase.table('calculation_results').update(result_data).eq('id', result_id).execute()
            else:
                # Insert new result
                response = supabase.table('calculation_results').insert(result_data).execute()
                result_id = response.data[0]['id']
            
            logging.info(f"Saved calculation result with ID {result_id}")
            return result_id
            
        except Exception as e:
            logging.error(f"Error saving calculation result: {str(e)}")
            raise
    
    @staticmethod
    def get_result(dealer_id: str, scenario_id: str) -> Optional[Dict]:
        """
        Get calculation result for a dealer and scenario.
        Returns a dictionary with the result or None if not found.
        """
        try:
            supabase = get_supabase_client()
            response = supabase.table('calculation_results').select('*').eq('dealer_id', dealer_id).eq('scenario_id', scenario_id).execute()
            
            if not response.data:
                return None
            
            result = response.data[0]
            
            # Parse JSON fields
            if result.get('cash_flows'):
                result['cash_flows'] = json.loads(result['cash_flows'])
            
            if result.get('yearly_data'):
                result['yearly_data'] = json.loads(result['yearly_data'])
            
            return result
            
        except Exception as e:
            logging.error(f"Error getting calculation result: {str(e)}")
            return None 