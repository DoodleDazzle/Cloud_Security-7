from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import ibm_boto3
from ibm_botocore.client import Config, ClientError
import logging
import os
from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_watson.natural_language_understanding_v1 import Features, EntitiesOptions, KeywordsOptions
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Secret Key for session security
app.secret_key = os.getenv('FLASK_SECRET_KEY', '7ef46bb33e976716696f445cbd430af4')  # Keep your secret key safe

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Specify the login view

# Define User class for Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Load user by ID
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# IBM Cloud Object Storage (COS) credentials
cos_api_key = '09Pdtt_HTiP6_y-ivTW4x3w9EnbKviO_b1ipi3kdoXx_'
cos_instance_id = 'crn:v1:bluemix:public:cloud-object-storage:global:a/816004080f334097a854cb90d8101731:020a4a5f-4d8d-4bc4-972e-403f4d4c448a::'
cos_endpoint = 'https://s3.us.cloud-object-storage.appdomain.cloud'
bucket_name = 'project-7'

# Initialize IBM COS client
cos = ibm_boto3.client('s3',
    ibm_api_key_id=cos_api_key,
    ibm_service_instance_id=cos_instance_id,
    config=Config(signature_version='oauth'),
    endpoint_url=cos_endpoint
)

# Allowed file extensions for upload validation
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'jpg', 'png', 'docx'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Allow files up to 16MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Watson NLU setup
authenticator = IAMAuthenticator('GgihzRGYw86UTy-jrl0L4j5UYeuiErV4JBJi1PFYZQ3I')
nlu = NaturalLanguageUnderstandingV1(version='2021-08-01', authenticator=authenticator)
nlu.set_service_url('https://api.au-syd.natural-language-understanding.watson.cloud.ibm.com/instances/86660d6c-fce1-4816-a52b-798ba6175cea')

def analyze_text(text):
    try:
        response = nlu.analyze(
            text=text,
            features=Features(
                entities=EntitiesOptions(),
                keywords=KeywordsOptions()
            )
        ).get_result()
        return response
    except Exception as e:
        return {"error": str(e)}

# Home route redirects to login
@app.route('/')
def home():
    return redirect(url_for('login'))  # Always redirect to login by default

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Simple admin authentication check
        if username == 'admin' and password == 'sejalDIPAK@05012004':
            user = User(username)
            login_user(user)
            return redirect(url_for('secure_upload'))  # Redirect to upload after login
        
        flash('Invalid username or password.', 'error')  # Invalid login feedback
    
    return render_template('login.html')

# File Upload route
@app.route('/upload', methods=['GET', 'POST'])
@login_required  # Ensure login is required
def secure_upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and allowed_file(file.filename):
            try:
                # Analyze file content using Watson NLU (if applicable)
                file_content = file.read().decode('utf-8', 'ignore')  # Assuming the file content is text
                nlu_result = analyze_text(file_content)
                logging.info(f'NLU Result: {nlu_result}')
                
                # Upload file to IBM Cloud Object Storage
                cos.upload_fileobj(file, bucket_name, file.filename)
                logging.info(f'File uploaded successfully: {file.filename}')
                return jsonify({"message": "File uploaded successfully"})
            except ClientError as e:
                logging.error(f'Upload failed: {e}')
                return jsonify({"error": f"Upload failed: {str(e)}"}), 500
            except Exception as e:
                logging.error(f'File processing error: {e}')
                return jsonify({"error": f"File processing failed: {str(e)}"}), 500
        return jsonify({"error": "Invalid file type or no file selected"}), 400
    
    return render_template('secure_upload.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)