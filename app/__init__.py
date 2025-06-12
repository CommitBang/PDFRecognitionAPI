from flask import Flask, render_template
from flask_restx import Api
from app.api.analyze import api as analyze_api
from app.api.test_site import api as test_api
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    api = Api(
        app,
        version='1.0',
        title='PDF Recognition API',
        description='API for PDF layout analysis, OCR, and figure-reference mapping',
        doc='/api/docs/'
    )
    
    api.add_namespace(analyze_api, path='/api/v1')
    api.add_namespace(test_api, path='/api/test')
    
    # Add route for test site
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app