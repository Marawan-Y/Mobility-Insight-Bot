from flask import render_template, session
import traceback
import logging

logger = logging.getLogger(__name__)

def handle_application_error(app):
    """Register error handlers for the Flask app"""
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        logger.error(f"Request too large: {error}")
        return "Request too large. Please reduce the input size.", 413
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.error(f"Unexpected error: {error}")
        logger.error(traceback.format_exc())
        
        # Reset session on critical errors
        if hasattr(error, 'args') and 'session' in str(error):
            session.clear()
            session["step"] = "identification"
        
        return render_template('error.html', 
                             error="An unexpected error occurred. Please try again."), 500