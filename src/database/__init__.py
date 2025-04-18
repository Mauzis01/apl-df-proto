"""
Database module for Supabase integration.
"""

from .supabase_config import get_supabase_client
from .repositories import DealerRepository, ScenarioRepository, ResultsRepository

__all__ = [
    'get_supabase_client',
    'DealerRepository',
    'ScenarioRepository',
    'ResultsRepository'
] 