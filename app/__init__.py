from flask import Flask, render_template
from flask_restx import Api
from config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Create necessary directories
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.TEMP_FOLDER, exist_ok=True)
    
    # Initialize Flask-RESTX
    api = Api(
        app,
        version='1.0',
        title='PDF Layout Analysis API',
        description='API for PDF layout analysis with figure and reference mapping',
        doc='/swagger/'
    )
    
    # Register namespaces
    from app.api.analyze import api as analyze_ns
    api.add_namespace(analyze_ns, path='/api/v1')
    
    # Add test page route
    @app.route('/')
    @app.route('/test')
    def test_page():
        return render_template('test.html')
    
    return app