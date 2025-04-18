import numpy as np
from typing import List, Dict, Tuple, Optional
import pandas as pd

class FinancialCalculator:
    """
    Financial calculator for dealer feasibility analysis
    Calculates key metrics: NPV, IRR, Payback Period
    """
    
    @staticmethod
    def calculate_npv(cash_flows: List[float], discount_rate: float) -> float:
        """
        Calculate Net Present Value (NPV)
        
        Args:
            cash_flows: List of cash flows (negative for investments, positive for returns)
            discount_rate: Annual discount rate (as decimal)
            
        Returns:
            NPV value
        """
        npv = 0
        for t, cf in enumerate(cash_flows):
            npv += cf / (1 + discount_rate) ** t
        return round(npv, 2)

    @staticmethod
    def calculate_irr(cash_flows: List[float]) -> Optional[float]:
        """
        Calculate Internal Rate of Return (IRR)
        
        Args:
            cash_flows: List of cash flows (negative for investments, positive for returns)
            
        Returns:
            IRR value as percentage or None if calculation fails
        """
        try:
            # Need at least one negative and one positive cash flow for IRR to make sense
            has_negative = any(cf < 0 for cf in cash_flows)
            has_positive = any(cf > 0 for cf in cash_flows)
            
            if not (has_negative and has_positive):
                return None
                
            # Using numpy's financial function for IRR calculation
            irr = np.irr(cash_flows)
            
            # Check if IRR is a valid number
            if np.isnan(irr) or np.isinf(irr):
                return None
                
            return round(float(irr) * 100, 2)
        except:
            return None

    @staticmethod
    def calculate_payback_period(cash_flows: List[float]) -> Optional[float]:
        """
        Calculate Payback Period
        
        Args:
            cash_flows: List of cash flows (negative for investments, positive for returns)
            
        Returns:
            Payback period in years
        """
        cumulative = 0
        for i, cf in enumerate(cash_flows):
            cumulative += cf
            if cumulative >= 0:
                # Add fractional year
                if i > 0 and cash_flows[i] != 0:
                    fraction = (0 - (cumulative - cf)) / cash_flows[i]
                    return round(i - 1 + fraction, 2)
                return i
        return None

    @staticmethod
    def calculate_discounted_payback_period(cash_flows: List[float], discount_rate: float) -> Optional[float]:
        """
        Calculate Discounted Payback Period
        
        Args:
            cash_flows: List of cash flows (negative for investments, positive for returns)
            discount_rate: Annual discount rate (as decimal)
            
        Returns:
            Discounted payback period in years
        """
        discounted_flows = [cf / (1 + discount_rate) ** t for t, cf in enumerate(cash_flows)]
        cumulative = 0
        for i, cf in enumerate(discounted_flows):
            cumulative += cf
            if cumulative >= 0:
                # Add fractional year
                if i > 0 and discounted_flows[i] != 0:
                    fraction = (0 - (cumulative - cf)) / discounted_flows[i]
                    return round(i - 1 + fraction, 2)
                return i
        return None
        
    @staticmethod
    def generate_financial_summary(cash_flows: List[float], discount_rate: float) -> Dict:
        """
        Generate comprehensive financial summary
        
        Args:
            cash_flows: List of cash flows (negative for investments, positive for returns)
            discount_rate: Annual discount rate (as decimal)
            
        Returns:
            Dictionary with financial metrics
        """
        npv = FinancialCalculator.calculate_npv(cash_flows, discount_rate)
        irr = FinancialCalculator.calculate_irr(cash_flows)
        payback = FinancialCalculator.calculate_payback_period(cash_flows)
        disc_payback = FinancialCalculator.calculate_discounted_payback_period(cash_flows, discount_rate)
        
        # Initial investment (absolute value of first cash flow if negative)
        initial_investment = abs(cash_flows[0]) if cash_flows[0] < 0 else 0
        
        # Total cash inflow (sum of positive cash flows)
        total_inflow = sum(cf for cf in cash_flows[1:] if cf > 0)
        
        return {
            'npv': npv,
            'irr': irr,
            'payback_period': payback,
            'discounted_payback_period': disc_payback,
            'initial_investment': initial_investment,
            'total_cash_inflow': total_inflow,
            'profitability_index': (npv + initial_investment) / initial_investment if initial_investment else None
        }

    @staticmethod
    def calculate_metrics(cash_flows: List[float], discount_rate: float, reinvestment_rate: Optional[float] = None) -> Tuple[float, float, float, List[float], List[float], float]:
        """
        Calculate all financial metrics for a cash flow series
        
        Args:
            cash_flows: List of cash flows (negative for investments, positive for returns)
            discount_rate: Annual discount rate (as decimal)
            reinvestment_rate: Rate for MIRR calculation (defaults to discount_rate if None)
            
        Returns:
            Tuple containing (NPV, IRR, Payback Period, Discounted Cash Flows, Cumulative Cash Flows, MIRR)
        """
        # Calculate NPV
        npv = FinancialCalculator.calculate_npv(cash_flows, discount_rate)
        
        # Calculate IRR
        irr_result = FinancialCalculator.calculate_irr(cash_flows)
        irr = irr_result / 100 if irr_result is not None else 0
        
        # Calculate Payback Period
        payback = FinancialCalculator.calculate_payback_period(cash_flows)
        if payback is None:
            payback = len(cash_flows)  # If no payback, set to project duration
        
        # Calculate discounted cash flows
        discounted_cash_flows = [cf / (1 + discount_rate) ** t for t, cf in enumerate(cash_flows)]
        
        # Calculate cumulative cash flows (non-discounted)
        cumulative_cash_flows = []
        cumulative = 0
        for cf in cash_flows:
            cumulative += cf
            cumulative_cash_flows.append(cumulative)
        
        # Calculate Modified Internal Rate of Return (MIRR)
        if reinvestment_rate is None:
            reinvestment_rate = discount_rate
            
        try:
            # Separate positive and negative cash flows
            positive_flows = [max(0, cf) for cf in cash_flows]
            negative_flows = [min(0, cf) for cf in cash_flows]
            
            # Ensure we have both positive and negative flows
            if sum(positive_flows) == 0 or sum(negative_flows) == 0:
                mirr = 0
            else:
                # Calculate terminal value of positive flows
                terminal_value = 0
                for t, cf in enumerate(positive_flows):
                    if cf > 0:
                        terminal_value += cf * (1 + reinvestment_rate) ** (len(cash_flows) - 1 - t)
                
                # Calculate present value of negative flows
                pv_negative = 0
                for t, cf in enumerate(negative_flows):
                    if cf < 0:
                        pv_negative += abs(cf) / (1 + discount_rate) ** t
                
                # Calculate MIRR
                if terminal_value > 0 and pv_negative > 0:
                    mirr = (terminal_value / pv_negative) ** (1 / (len(cash_flows) - 1)) - 1
                else:
                    mirr = 0
        except:
            mirr = 0
        
        return npv, irr, payback, discounted_cash_flows, cumulative_cash_flows, mirr 