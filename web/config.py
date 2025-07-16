"""
Configuration management for the ATC Conflict Analysis Web Interface.

This module centralizes all configuration settings for the web interface,
making it easier to maintain and modify settings without touching the main application code.
"""

import os
from typing import Dict, Any

class Config:
    """Centralized configuration for the web interface."""
    
    # File upload settings
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'.xml'}
    UPLOAD_FOLDER = '../xml_files'
    
    # Processing settings
    PROCESSING_TIMEOUT = 300  # 5 minutes
    STATUS_CHECK_INTERVAL = 1000  # 1 second
    MAX_RETRIES = 3
    CLEANUP_ON_FAILURE = True
    
    # Logging settings
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'app.log'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # UI settings
    AUTO_REFRESH_INTERVAL = 3000  # 3 seconds
    MESSAGE_DISPLAY_TIME = 5000  # 5 seconds
    PROGRESS_UPDATE_INTERVAL = 1000  # 1 second
    
    # Validation settings
    VALIDATE_FILES_ON_UPLOAD = True
    CACHE_VALIDATION_RESULTS = True
    VALIDATION_CACHE_TIMEOUT = 3600  # 1 hour
    
    # Error handling
    SHOW_DETAILED_ERRORS = True
    MAX_ERROR_MESSAGE_LENGTH = 200
    
    @classmethod
    def get_upload_config(cls) -> Dict[str, Any]:
        """Get upload-related configuration."""
        return {
            'max_file_size': cls.MAX_FILE_SIZE,
            'allowed_extensions': cls.ALLOWED_EXTENSIONS,
            'upload_folder': cls.UPLOAD_FOLDER
        }
    
    @classmethod
    def get_processing_config(cls) -> Dict[str, Any]:
        """Get processing-related configuration."""
        return {
            'timeout': cls.PROCESSING_TIMEOUT,
            'status_check_interval': cls.STATUS_CHECK_INTERVAL,
            'max_retries': cls.MAX_RETRIES,
            'cleanup_on_failure': cls.CLEANUP_ON_FAILURE
        }
    
    @classmethod
    def get_ui_config(cls) -> Dict[str, Any]:
        """Get UI-related configuration."""
        return {
            'auto_refresh_interval': cls.AUTO_REFRESH_INTERVAL,
            'message_display_time': cls.MESSAGE_DISPLAY_TIME,
            'progress_update_interval': cls.PROGRESS_UPDATE_INTERVAL
        }
    
    @classmethod
    def get_validation_config(cls) -> Dict[str, Any]:
        """Get validation-related configuration."""
        return {
            'validate_on_upload': cls.VALIDATE_FILES_ON_UPLOAD,
            'cache_results': cls.CACHE_VALIDATION_RESULTS,
            'cache_timeout': cls.VALIDATION_CACHE_TIMEOUT
        }

class DevelopmentConfig(Config):
    """Development-specific configuration."""
    LOG_LEVEL = 'DEBUG'
    SHOW_DETAILED_ERRORS = True

class ProductionConfig(Config):
    """Production-specific configuration."""
    LOG_LEVEL = 'WARNING'
    SHOW_DETAILED_ERRORS = False
    MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB for production

def get_config(environment: str = 'development') -> Config:
    """Get configuration based on environment."""
    if environment is None:
        environment = os.getenv('FLASK_ENV', 'development')
    
    if environment == 'production':
        return ProductionConfig()
    else:
        return DevelopmentConfig() 