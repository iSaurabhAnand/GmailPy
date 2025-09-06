import os
from app import app
from app.logger import setup_logger

if __name__ == '__main__':
    # Enable debug mode if DEBUG environment variable is set
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Setup logger
    setup_logger(debug_mode)
    
    # Run the application
    app.run(debug=debug_mode, port=5000)
