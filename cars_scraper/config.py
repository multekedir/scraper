"""
Configuration file handling for the scraper.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class ScraperConfig:
    """Configuration for the scraper."""
    
    def __init__(self, config_dict: Dict[str, Any] = None):
        """
        Initialize configuration from a dictionary.
        
        Args:
            config_dict: Configuration dictionary
        """
        config = config_dict or {}
        
        # Filtering options
        self.max_price: float = config.get('max_price', 60000)
        self.max_mileage: int = config.get('max_mileage', 200)
        self.new_only: bool = config.get('new_only', True)
        self.electric_only: bool = config.get('electric_only', True)
        self.fuel_types: Optional[List[str]] = config.get('fuel_types')  # None = use electric_only
        self.min_year: Optional[int] = config.get('min_year')
        self.max_year: Optional[int] = config.get('max_year')
        
        # Make/model filters
        self.makes: Optional[List[str]] = config.get('makes')  # None = all makes
        self.models: Optional[List[str]] = config.get('models')  # None = all models
        self.exclude_makes: Optional[List[str]] = config.get('exclude_makes', [])
        self.exclude_models: Optional[List[str]] = config.get('exclude_models', [])
        
        # Drivetrain filters
        self.drivetrains: Optional[List[str]] = config.get('drivetrains')  # None = all drivetrains
        self.exclude_drivetrains: Optional[List[str]] = config.get('exclude_drivetrains', [])
        
        # Price filters
        self.min_price: Optional[float] = config.get('min_price')
        
        # Dealer filters
        self.dealers: Optional[List[str]] = config.get('dealers')  # None = all dealers
        self.exclude_dealers: Optional[List[str]] = config.get('exclude_dealers', [])
        self.cities: Optional[List[str]] = config.get('cities')  # None = all cities
        self.states: Optional[List[str]] = config.get('states')  # None = all states
        
        # Status filters
        self.availability_status: Optional[List[str]] = config.get('availability_status')  # None = all statuses
        self.exclude_status: Optional[List[str]] = config.get('exclude_status', ['sold'])
        
        # Output options
        self.output_path: str = config.get('output_path', 'cars.csv')
        self.output_format: str = config.get('output_format', 'auto')  # 'json', 'csv', 'auto'
        
        # Scraping options
        self.sites: Optional[List[str]] = config.get('sites')  # None = all sites
        self.all_sites: bool = config.get('all_sites', True)
        
        # Logging options
        self.log_level: str = config.get('log_level', 'INFO')
        self.log_file: Optional[str] = config.get('log_file')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'max_price': self.max_price,
            'max_mileage': self.max_mileage,
            'new_only': self.new_only,
            'electric_only': self.electric_only,
            'fuel_types': self.fuel_types,
            'min_year': self.min_year,
            'max_year': self.max_year,
            'makes': self.makes,
            'models': self.models,
            'exclude_makes': self.exclude_makes,
            'exclude_models': self.exclude_models,
            'drivetrains': self.drivetrains,
            'exclude_drivetrains': self.exclude_drivetrains,
            'min_price': self.min_price,
            'dealers': self.dealers,
            'exclude_dealers': self.exclude_dealers,
            'cities': self.cities,
            'states': self.states,
            'availability_status': self.availability_status,
            'exclude_status': self.exclude_status,
            'output_path': self.output_path,
            'output_format': self.output_format,
            'sites': self.sites,
            'all_sites': self.all_sites,
            'log_level': self.log_level,
            'log_file': self.log_file,
        }
    
    @classmethod
    def from_file(cls, config_path: str) -> 'ScraperConfig':
        """
        Load configuration from a JSON file.
        
        Args:
            config_path: Path to configuration file
        
        Returns:
            ScraperConfig object
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            logger.info(f"Loaded configuration from {config_path}")
            return cls(config_dict)
        
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ValueError(f"Error reading config file: {e}")
    
    def save_to_file(self, config_path: str) -> None:
        """
        Save configuration to a JSON file.
        
        Args:
            config_path: Path to save configuration file
        """
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved configuration to {config_path}")
    
    @classmethod
    def create_default(cls, config_path: str = 'scraper_config.json') -> 'ScraperConfig':
        """
        Create a default configuration file with example values.
        
        Args:
            config_path: Path to save default configuration
        
        Returns:
            ScraperConfig object with default values
        """
        # Create config with default values
        config = cls()
        config.save_to_file(config_path)
        return config

