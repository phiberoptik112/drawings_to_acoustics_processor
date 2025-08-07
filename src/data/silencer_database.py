"""
Silencer product database management and filtering system
"""

from typing import List, Dict, Optional, Any
from sqlalchemy import and_, or_
from models import get_session
from models.hvac import SilencerProduct


class SilencerDatabaseManager:
    """Manages silencer product database operations"""
    
    def __init__(self):
        self.session = get_session()
    
    def populate_database(self):
        """Populate database with known silencer products"""
        
        # Check if products already exist
        existing_count = self.session.query(SilencerProduct).count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} silencer products")
            return
        
        # Sample products from major manufacturers
        products = [
            # Kinetics Products
            {
                'manufacturer': 'Kinetics',
                'model_number': 'KSN-12-12-48',
                'silencer_type': 'dissipative',
                'length': 48, 'width': 12, 'height': 12, 'weight': 45,
                'flow_rate_min': 100, 'flow_rate_max': 2000, 'velocity_max': 2000,
                'insertion_loss_63': 8, 'insertion_loss_125': 12, 'insertion_loss_250': 18,
                'insertion_loss_500': 25, 'insertion_loss_1000': 30, 'insertion_loss_2000': 28,
                'insertion_loss_4000': 22, 'insertion_loss_8000': 15,
                'cost_estimate': 2500, 'availability': 'in_stock'
            },
            {
                'manufacturer': 'Kinetics',
                'model_number': 'KSN-16-16-60',
                'silencer_type': 'dissipative',
                'length': 60, 'width': 16, 'height': 16, 'weight': 68,
                'flow_rate_min': 200, 'flow_rate_max': 3500, 'velocity_max': 2500,
                'insertion_loss_63': 12, 'insertion_loss_125': 16, 'insertion_loss_250': 22,
                'insertion_loss_500': 28, 'insertion_loss_1000': 35, 'insertion_loss_2000': 32,
                'insertion_loss_4000': 26, 'insertion_loss_8000': 18,
                'cost_estimate': 3800, 'availability': 'in_stock'
            },
            {
                'manufacturer': 'Kinetics',
                'model_number': 'KSR-10-10-36',
                'silencer_type': 'reactive',
                'length': 36, 'width': 10, 'height': 10, 'weight': 28,
                'flow_rate_min': 50, 'flow_rate_max': 1200, 'velocity_max': 1800,
                'insertion_loss_63': 15, 'insertion_loss_125': 18, 'insertion_loss_250': 12,
                'insertion_loss_500': 8, 'insertion_loss_1000': 6, 'insertion_loss_2000': 4,
                'insertion_loss_4000': 3, 'insertion_loss_8000': 2,
                'cost_estimate': 1800, 'availability': 'in_stock'
            },
            
            # IAC Acoustics Products
            {
                'manufacturer': 'IAC Acoustics',
                'model_number': 'Type R-12-12-48',
                'silencer_type': 'dissipative',
                'length': 48, 'width': 12, 'height': 12, 'weight': 42,
                'flow_rate_min': 120, 'flow_rate_max': 2200, 'velocity_max': 2200,
                'insertion_loss_63': 10, 'insertion_loss_125': 14, 'insertion_loss_250': 20,
                'insertion_loss_500': 27, 'insertion_loss_1000': 32, 'insertion_loss_2000': 30,
                'insertion_loss_4000': 24, 'insertion_loss_8000': 16,
                'cost_estimate': 2700, 'availability': 'in_stock'
            },
            {
                'manufacturer': 'IAC Acoustics',
                'model_number': 'Type R-20-20-72',
                'silencer_type': 'dissipative',
                'length': 72, 'width': 20, 'height': 20, 'weight': 105,
                'flow_rate_min': 400, 'flow_rate_max': 6000, 'velocity_max': 2800,
                'insertion_loss_63': 15, 'insertion_loss_125': 20, 'insertion_loss_250': 26,
                'insertion_loss_500': 32, 'insertion_loss_1000': 38, 'insertion_loss_2000': 35,
                'insertion_loss_4000': 28, 'insertion_loss_8000': 20,
                'cost_estimate': 5200, 'availability': 'lead_time'
            },
            
            # Vibro-Acoustics Products
            {
                'manufacturer': 'Vibro-Acoustics',
                'model_number': 'VS-12-12-48',
                'silencer_type': 'hybrid',
                'length': 48, 'width': 12, 'height': 12, 'weight': 48,
                'flow_rate_min': 100, 'flow_rate_max': 1800, 'velocity_max': 2000,
                'insertion_loss_63': 12, 'insertion_loss_125': 15, 'insertion_loss_250': 19,
                'insertion_loss_500': 24, 'insertion_loss_1000': 28, 'insertion_loss_2000': 26,
                'insertion_loss_4000': 20, 'insertion_loss_8000': 14,
                'cost_estimate': 2900, 'availability': 'in_stock'
            },
            {
                'manufacturer': 'Vibro-Acoustics',
                'model_number': 'VR-8-8-24',
                'silencer_type': 'reactive',
                'length': 24, 'width': 8, 'height': 8, 'weight': 18,
                'flow_rate_min': 30, 'flow_rate_max': 800, 'velocity_max': 1500,
                'insertion_loss_63': 18, 'insertion_loss_125': 22, 'insertion_loss_250': 15,
                'insertion_loss_500': 10, 'insertion_loss_1000': 7, 'insertion_loss_2000': 5,
                'insertion_loss_4000': 4, 'insertion_loss_8000': 3,
                'cost_estimate': 1200, 'availability': 'in_stock'
            },
            
            # SoundAttenuators Products
            {
                'manufacturer': 'SoundAttenuators',
                'model_number': 'SA-14-14-54',
                'silencer_type': 'dissipative',
                'length': 54, 'width': 14, 'height': 14, 'weight': 58,
                'flow_rate_min': 150, 'flow_rate_max': 2800, 'velocity_max': 2300,
                'insertion_loss_63': 9, 'insertion_loss_125': 13, 'insertion_loss_250': 19,
                'insertion_loss_500': 26, 'insertion_loss_1000': 31, 'insertion_loss_2000': 29,
                'insertion_loss_4000': 23, 'insertion_loss_8000': 17,
                'cost_estimate': 3100, 'availability': 'in_stock'
            },
            {
                'manufacturer': 'SoundAttenuators',
                'model_number': 'SA-18-18-66',
                'silencer_type': 'dissipative',
                'length': 66, 'width': 18, 'height': 18, 'weight': 88,
                'flow_rate_min': 300, 'flow_rate_max': 4500, 'velocity_max': 2600,
                'insertion_loss_63': 13, 'insertion_loss_125': 17, 'insertion_loss_250': 23,
                'insertion_loss_500': 30, 'insertion_loss_1000': 36, 'insertion_loss_2000': 33,
                'insertion_loss_4000': 27, 'insertion_loss_8000': 19,
                'cost_estimate': 4200, 'availability': 'in_stock'
            }
        ]
        
        # Add products to database
        for product_data in products:
            product = SilencerProduct(**product_data)
            self.session.add(product)
        
        try:
            self.session.commit()
            print(f"Successfully added {len(products)} silencer products to database")
        except Exception as e:
            self.session.rollback()
            print(f"Error adding products to database: {e}")
    
    def get_all_products(self) -> List[SilencerProduct]:
        """Get all silencer products"""
        return self.session.query(SilencerProduct).all()
    
    def close(self):
        """Close the database session"""
        self.session.close()


class SilencerFilterEngine:
    """Engine for filtering and ranking silencer products based on requirements"""
    
    def __init__(self):
        self.session = get_session()
    
    def filter_products(self, requirements: Dict[str, Any]) -> List[SilencerProduct]:
        """
        Filter products based on requirements
        
        Args:
            requirements: Dictionary with filtering criteria
            
        Returns:
            List of filtered SilencerProduct objects
        """
        query = self.session.query(SilencerProduct)
        
        # Filter by silencer type
        if requirements.get('silencer_type'):
            query = query.filter(SilencerProduct.silencer_type == requirements['silencer_type'])
        
        # Filter by manufacturer
        if requirements.get('manufacturer'):
            query = query.filter(SilencerProduct.manufacturer == requirements['manufacturer'])
        
        # Filter by insertion loss requirements (8-band)
        frequency_bands = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
        for freq in frequency_bands:
            required_loss = requirements.get(f'insertion_loss_{freq}')
            if required_loss:
                attr = getattr(SilencerProduct, f'insertion_loss_{freq}')
                query = query.filter(attr >= required_loss)
        
        # Filter by physical dimensions
        if requirements.get('max_length'):
            query = query.filter(SilencerProduct.length <= requirements['max_length'])
        if requirements.get('max_width'):
            query = query.filter(SilencerProduct.width <= requirements['max_width'])
        if requirements.get('max_height'):
            query = query.filter(SilencerProduct.height <= requirements['max_height'])
        if requirements.get('max_weight'):
            query = query.filter(SilencerProduct.weight <= requirements['max_weight'])
        
        # Filter by flow rate
        if requirements.get('flow_rate'):
            flow_rate = requirements['flow_rate']
            query = query.filter(
                and_(
                    SilencerProduct.flow_rate_min <= flow_rate,
                    SilencerProduct.flow_rate_max >= flow_rate
                )
            )
        
        # Filter by velocity
        if requirements.get('max_velocity'):
            query = query.filter(SilencerProduct.velocity_max >= requirements['max_velocity'])
        
        # Filter by cost range
        if requirements.get('min_cost'):
            query = query.filter(SilencerProduct.cost_estimate >= requirements['min_cost'])
        if requirements.get('max_cost'):
            query = query.filter(SilencerProduct.cost_estimate <= requirements['max_cost'])
        
        # Filter by availability
        if requirements.get('availability'):
            availability_options = requirements['availability']
            if isinstance(availability_options, str):
                availability_options = [availability_options]
            query = query.filter(SilencerProduct.availability.in_(availability_options))
        
        return query.all()
    
    def calculate_match_score(self, product: SilencerProduct, requirements: Dict[str, Any]) -> float:
        """
        Calculate how well a product matches requirements (0-100 score)
        
        Args:
            product: SilencerProduct to evaluate
            requirements: Requirements dictionary
            
        Returns:
            Match score from 0-100 (higher is better)
        """
        score = 100.0
        
        # Check insertion loss performance (40% of score)
        frequency_bands = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
        insertion_loss_penalty = 0
        
        for freq in frequency_bands:
            required = requirements.get(f'insertion_loss_{freq}', 0)
            if required > 0:
                actual = getattr(product, f'insertion_loss_{freq}', 0) or 0
                
                if actual < required:
                    # Penalty for insufficient performance (critical)
                    insertion_loss_penalty += (required - actual) * 3
                elif actual > required * 1.8:
                    # Small penalty for significant over-performance
                    insertion_loss_penalty += (actual - required * 1.8) * 0.3
        
        score -= min(insertion_loss_penalty, 40)  # Cap at 40% penalty
        
        # Check physical constraints (20% of score)
        physical_penalty = 0
        constraints = ['max_length', 'max_width', 'max_height', 'max_weight']
        product_attrs = ['length', 'width', 'height', 'weight']
        
        for constraint, attr in zip(constraints, product_attrs):
            if requirements.get(constraint):
                max_allowed = requirements[constraint]
                actual = getattr(product, attr, 0) or 0
                
                if actual > max_allowed:
                    # Penalty for exceeding constraints
                    physical_penalty += min((actual - max_allowed) / max_allowed * 10, 5)
        
        score -= min(physical_penalty, 20)  # Cap at 20% penalty
        
        # Check flow rate compatibility (15% of score)
        if requirements.get('flow_rate'):
            required_flow = requirements['flow_rate']
            min_flow = product.flow_rate_min or 0
            max_flow = product.flow_rate_max or float('inf')
            
            if required_flow < min_flow or required_flow > max_flow:
                score -= 15  # Flow rate incompatibility is critical
            else:
                # Bonus for optimal flow range
                flow_range = max_flow - min_flow
                if flow_range > 0:
                    optimal_position = (required_flow - min_flow) / flow_range
                    # Bonus for being in middle 60% of range
                    if 0.2 <= optimal_position <= 0.8:
                        score += 2
        
        # Check cost efficiency (15% of score)
        if requirements.get('max_cost') and product.cost_estimate:
            max_budget = requirements['max_cost']
            cost_ratio = product.cost_estimate / max_budget
            
            if cost_ratio <= 0.6:
                # Bonus for being well under budget
                score += 5
            elif cost_ratio <= 0.8:
                # Small bonus for reasonable cost
                score += 2
            elif cost_ratio > 0.95:
                # Penalty for being near budget limit
                score -= (cost_ratio - 0.95) * 20
        
        # Availability bonus/penalty (10% of score)
        availability = product.availability or 'unknown'
        if availability == 'in_stock':
            score += 5
        elif availability == 'lead_time':
            score -= 2
        elif availability == 'discontinued':
            score -= 10
        
        return max(0, min(score, 100))  # Clamp between 0-100
    
    def get_ranked_products(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get filtered products ranked by match score
        
        Args:
            requirements: Requirements dictionary
            
        Returns:
            List of dictionaries with product and match score
        """
        products = self.filter_products(requirements)
        ranked_products = []
        
        for product in products:
            match_score = self.calculate_match_score(product, requirements)
            ranked_products.append({
                'product': product,
                'match_score': match_score
            })
        
        # Sort by match score (descending)
        ranked_products.sort(key=lambda x: x['match_score'], reverse=True)
        
        return ranked_products
    
    def close(self):
        """Close the database session"""
        self.session.close()


# Convenience functions
def populate_silencer_database():
    """Populate the silencer product database"""
    manager = SilencerDatabaseManager()
    try:
        manager.populate_database()
    finally:
        manager.close()


def get_filtered_silencers(requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get filtered and ranked silencer products"""
    filter_engine = SilencerFilterEngine()
    try:
        return filter_engine.get_ranked_products(requirements)
    finally:
        filter_engine.close()