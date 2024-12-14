from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime, timedelta  # Add timedelta here
import firebase_admin
from firebase_admin import credentials, firestore, auth
from werkzeug.utils import secure_filename
import os
import cloudinary
import cloudinary.uploader
import requests  # Add this import statement
import time
import tensorflow as tf
import numpy as np
from PIL import Image
import io

# Initialize Firebase Admin SDK
cred = credentials.Certificate('firebase-adminsdk.json')  # Make sure this file is in the right directory
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize Cloudinary
cloudinary.config(
    cloud_name = "dxvsu1ntf", 
    api_key = "234877946597699", 
    api_secret = "gTxc5e5fVYRx8z8LTwgPAe6RZrE", # Click 'View API Keys' above to copy your API secret
    secure=True
)

# Firebase REST API key
FIREBASE_API_KEY = 'AIzaSyB9aaQW0klcT-Dd0AX2TNORYOcFKYTZ0PA'  # Replace with your Firebase project's API key

# Initialize Flask
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management
app.config['UPLOAD_FOLDER'] = 'uploads'  # Local upload folder for files
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes session timeout
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Load the brain tumor classification model
model = tf.keras.models.load_model("brain_tumor_multiclass_model.h5")
print(f"Model input shape: {model.input_shape}")
categories = ["glioma", "meningioma", "no_tumor", "pituitary_tumor"]

def preprocess_image(image_data):
    """Preprocess image for model prediction"""
    try:
        # Convert bytes to PIL Image
        img = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if (img.mode != 'RGB'):
            img = img.convert('RGB')
            
        # Print original image size
        print(f"Original image size: {img.size}")
            
        # Resize image to match model's expected input size
        target_size = (128, 128)  # Resize to (128, 128)
        img = img.resize(target_size)
        print(f"Resized image size: {img.size}")
        
        # Convert to array and preprocess
        img_array = tf.keras.preprocessing.image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
        
        # Ensure the array shape matches the model's expected input
        print(f"Final array shape before preprocessing: {img_array.shape}")
        
        # If using a specific model like VGG16, use its preprocess_input function
        img_array = tf.keras.applications.vgg16.preprocess_input(img_array)
        
        # Flatten the array if needed to match the model's input shape
        img_array = img_array.reshape((1, 128, 128, 3))
        
        print(f"Final array shape after preprocessing: {img_array.shape}")
        return img_array
        
    except Exception as e:
        print(f"Error preprocessing image: {str(e)}")
        return None

@app.route('/')
def index():
    if 'user_email' in session:
        user_data = {
            'email': session['user_email'],
            'role': session['user_role'],
            'profile_picture': session.get('profile_picture')
        }
        return render_template('index.html', user_data=user_data)
    return render_template('index.html')

# Add session configuration
@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            print("Login request received") # Debug log
            data = request.get_json()
            print("Request data:", data) # Debug log
            
            if not data:
                return jsonify({
                    "success": False,
                    "message": "No data received"
                }), 400
                
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return jsonify({
                    "success": False,
                    "message": "Email and password are required."
                }), 400

            try:
                # Firebase authentication
                url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
                payload = {
                    "email": email,
                    "password": password,
                    "returnSecureToken": True
                }
                response = requests.post(url, json=payload)
                result = response.json()
                print("Firebase response:", result) # Debug log

                if response.status_code != 200:
                    error_message = result.get('error', {}).get('message', 'Invalid credentials')
                    return jsonify({
                        "success": False,
                        "message": f"Authentication failed: {error_message}"
                    }), 401

                # Get user data from Firestore
                user_uid = result['localId']
                user_doc = db.collection('users').document(user_uid).get()
                
                if not user_doc.exists:
                    return jsonify({
                        "success": False,
                        "message": "User data not found"
                    }), 404

                # Set session data with role mapping
                user_data = user_doc.to_dict()
                session['user_email'] = email
                # Map 'patient' role to 'client'
                role = user_data.get('role', 'client')
                if role == 'patient':
                    role = 'client'
                session['user_role'] = role
                session['profile_picture'] = user_data.get('profile_picture')
                
                print(f"User role set to: {session['user_role']}")  # Debug log
                
                # Return success with redirect URL
                redirect_url = url_for('doctor_dashboard') if session['user_role'] == 'doctor' else url_for('client_dashboard')
                return jsonify({
                    "success": True,
                    "redirect_url": redirect_url
                })

            except requests.exceptions.RequestException as e:
                print(f"Network error: {str(e)}") # Debug log
                return jsonify({
                    "success": False,
                    "message": f"Network error: {str(e)}"
                }), 500

        except Exception as e:
            print(f"Server error: {str(e)}") # Debug log
            return jsonify({
                "success": False,
                "message": f"Server error: {str(e)}"
            }), 500

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            # Check content type
            if not request.is_json:
                return jsonify({
                    "success": False,
                    "message": "Content-Type must be application/json"
                }), 415

            data = request.get_json()
            print("Received signup data:", data)  # Debug log

            # Create user in Firebase Auth
            try:
                user = auth.create_user(
                    email=data['email'],
                    password=data['password'],
                    display_name=data['name']
                )

                # Prepare user data for Firestore
                user_data = {
                    'name': data['name'],
                    'email': data['email'],
                    'phone': data.get('phone', ''),
                    'role': data['role'],
                    'created_at': firestore.SERVER_TIMESTAMP
                }

                # Add role-specific data
                if data['role'] == 'patient':
                    # Add appointment data
                    user_data.update({
                        'appointment_date': data.get('appointment_date'),
                        'appointment_time': data.get('appointment_time'),
                        'appointment_reason': data.get('appointment_reason'),
                        'doctor_email': data.get('doctor_email'),
                        'status': 'pending'  # Appointment status
                    })
                    
                    # Create appointment document
                    appointment_data = {
                        'patient_email': data['email'],
                        'patient_name': data['name'],
                        'doctor_email': data.get('doctor_email'),
                        'date': data.get('appointment_date'),
                        'time': data.get('appointment_time'),
                        'reason': data.get('appointment_reason'),
                        'status': 'pending',
                        'created_at': firestore.SERVER_TIMESTAMP
                    }
                    
                    # Save appointment in appointments collection
                    db.collection('appointments').add(appointment_data)

                elif data['role'] == 'doctor':
                    user_data.update({
                        'specialty': data.get('specialty', ''),
                        'experience': data.get('experience', ''),
                        'license': data.get('license', '')
                    })

                # Save user data in Firestore
                db.collection('users').document(user.uid).set(user_data)

                print(f"User created successfully: {user.uid}")  # Debug log
                return jsonify({
                    "success": True,
                    "message": "Signup successful!",
                    "uid": user.uid
                })

            except Exception as e:
                print(f"Error creating user: {str(e)}")  # Debug log
                return jsonify({
                    "success": False,
                    "message": str(e)
                }), 400

        except Exception as e:
            print(f"Server error: {str(e)}")  # Debug log
            return jsonify({
                "success": False,
                "message": f"Server error: {str(e)}"
            }), 500

    # GET request - fetch doctors for the form
    try:
        doctors = []
        doctors_ref = db.collection('users').where('role', '==', 'doctor').stream()
        for doc in doctors_ref:
            doc_data = doc.to_dict()
            doctors.append({
                'email': doc_data.get('email'),
                'name': doc_data.get('name'),
                'specialty': doc_data.get('specialty')
            })
        return render_template('signup.html', doctors=doctors)
    except Exception as e:
        print(f"Error fetching doctors: {str(e)}")
        return render_template('signup.html', doctors=[])

@app.route('/client_dashboard')
def client_dashboard():
    if ('user_email' in session and session['user_role'] == 'client'):
        try:
            user = auth.get_user_by_email(session['user_email'])
            user_doc = db.collection('users').document(user.uid).get()
            if (user_doc.exists):
                user_data = user_doc.to_dict()
                profile_picture = user_data.get('profile_picture', None)
                
                # Fetch medical images
                medical_images = []
                images_ref = db.collection('users').document(user.uid)\
                             .collection('medical_images')\
                             .order_by('upload_date', direction=firestore.Query.DESCENDING)\
                             .stream()
                
                for img in images_ref:
                    img_data = img.to_dict()
                    img_data['upload_date'] = img_data['upload_date'].strftime('%Y-%m-%d %H:%M:%S')\
                        if (img_data.get('upload_date')) else 'Unknown'
                    medical_images.append(img_data)

                return render_template('client_dashboard.html',
                                    profile_picture=profile_picture,
                                    user_data=user_data,
                                    medical_images=medical_images)
        except Exception as e:
            print(f"Error in client dashboard: {str(e)}")
            session.pop('user_email', None)
            session.pop('user_role', None)
            return redirect(url_for('login'))
    return redirect(url_for('login'))


@app.route('/doctor_dashboard')
def doctor_dashboard():
    if ('user_email' in session and session['user_role'] == 'doctor'):
        try:
            user = auth.get_user_by_email(session['user_email'])
            user_doc = db.collection('users').document(user.uid).get()
            if (user_doc.exists):
                user_data = user_doc.to_dict()
                profile_picture = user_data.get('profile_picture', None)
                
                # Fetch clients
                clients = []
                clients_ref = db.collection('users').where('role', '==', 'client').stream()
                for client in clients_ref:
                    clients.append(client.to_dict())

                # Fetch appointments for the doctor
                appointments = db.collection('users').where('doctor_email', '==', session['user_email']).stream()
                appointments_list = [appointment.to_dict() for appointment in appointments]

                return render_template('doctor_dashboard.html',
                                       profile_picture=profile_picture,
                                       user_data=user_data,
                                       clients=clients,
                                       appointments=appointments_list)
        except Exception as e:
            print(f"Error in doctor dashboard: {str(e)}")
            session.pop('user_email', None)
            session.pop('user_role', None)
            return redirect(url_for('login'))
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop('user_email', None)
    session.pop('user_role', None)
    return redirect(url_for('login'))

@app.route('/change_name', methods=['POST'])
def change_name():
    if ('user_email' not in session):
        return redirect(url_for('login'))

    new_name = request.form.get('new_name')
    if (not new_name):
        return jsonify({"success": False, "message": "Name cannot be empty."})

    try:
        user = auth.get_user_by_email(session['user_email'])
        auth.update_user(user.uid, display_name=new_name)
        db.collection('users').document(user.uid).update({'name': new_name})

        return jsonify({"success": True, "message": "Name updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/change_password', methods=['POST'])
def change_password():
    if ('user_email' not in session):
        return redirect(url_for('login'))

    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if (not new_password or not confirm_password):
        return jsonify({"success": False, "message": "Both password fields are required."})
    if (new_password != confirm_password):
        return jsonify({"success": False, "message": "Passwords do not match."})

    try:
        user = auth.get_user_by_email(session['user_email'])
        auth.update_user(user.uid, password=new_password)

        return jsonify({"success": True, "message": "Password updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})



@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    if ('user_email' not in session):
        return redirect(url_for('login'))

    profile_picture = request.files.get('profile_picture')
    if (not profile_picture or profile_picture.filename == ''):
        return jsonify({"success": False, "message": "No file selected."})

    try:
        user_email = session['user_email']
        # Upload to Cloudinary with the user's email as the public ID
        upload_result = cloudinary.uploader.upload(profile_picture, public_id=f"profile_pictures/{user_email}")
        file_url = upload_result['secure_url']

        user = auth.get_user_by_email(user_email)
        db.collection('users').document(user.uid).update({'profile_picture': file_url})

        return jsonify({"success": True, "message": "Profile picture updated successfully!", "file_url": file_url})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/chat')
def chat():
    if 'user_email' not in session:
        return redirect(url_for('login'))
        
    try:
        # Fetch all users except current user
        users = []
        users_ref = db.collection('users').stream()
        current_user_email = session['user_email']
        
        for user_doc in users_ref:
            user_data = user_doc.to_dict()
            if user_data.get('email') != current_user_email:
                users.append({
                    'email': user_data.get('email'),
                    'name': user_data.get('name'),
                    'profile_picture': user_data.get('profile_picture', url_for('static', filename='images/default_profile.jpg'))
                })
        
        # Get current user data
        user = auth.get_user_by_email(current_user_email)
        user_doc = db.collection('users').document(user.uid).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        
        return render_template('chat.html', users=users, user_data=user_data)
        
    except Exception as e:
        print(f"Error in chat route: {str(e)}")
        return redirect(url_for('login'))

@app.route('/get_messages')
def get_messages():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    recipient_email = request.args.get('recipient')
    after_timestamp = float(request.args.get('after', 0))
    
    if not recipient_email:
        return jsonify([])

    try:
        user_email = session['user_email']
        messages = []
        
        # Get messages where current user is sender
        sent_query = db.collection('messages')\
            .where('sender_email', '==', user_email)\
            .where('recipient_email', '==', recipient_email)\
            .stream()
            
        # Get messages where current user is recipient
        received_query = db.collection('messages')\
            .where('sender_email', '==', recipient_email)\
            .where('recipient_email', '==', user_email)\
            .stream()

        for msg in sent_query:
            msg_data = msg.to_dict()
            timestamp = msg_data.get('timestamp', 0)
            if timestamp > after_timestamp:
                messages.append({
                    'sender_email': user_email,
                    'sender_profile_picture': session.get('profile_picture'),
                    'message': msg_data['message'],
                    'timestamp': timestamp
                })

        for msg in received_query:
            msg_data = msg.to_dict()
            timestamp = msg_data.get('timestamp', 0)
            if timestamp > after_timestamp:
                sender_doc = db.collection('users').where('email', '==', recipient_email).limit(1).get()
                sender_data = next(iter(sender_doc)).to_dict() if sender_doc else {}
                messages.append({
                    'sender_email': recipient_email,
                    'sender_profile_picture': sender_data.get('profile_picture'),
                    'message': msg_data['message'],
                    'timestamp': timestamp
                })

        messages.sort(key=lambda x: x['timestamp'])
        return jsonify(messages)

    except Exception as e:
        print(f"Error fetching messages: {str(e)}")
        return jsonify([])

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    data = request.get_json()
    message = data.get('message')
    recipient_email = data.get('recipient')

    if not message or not recipient_email:
        return jsonify({"success": False, "message": "Message and recipient are required."})

    try:
        sender = auth.get_user_by_email(session['user_email'])
        sender_doc = db.collection('users').document(sender.uid).get()
        sender_data = sender_doc.to_dict()

        message_data = {
            'sender': sender.uid,
            'sender_email': session['user_email'],
            'sender_name': sender_data.get('name', ''),
            'sender_profile_picture': sender_data.get('profile_picture', ''),
            'recipient_email': recipient_email,
            'message': message,
            'timestamp': firestore.SERVER_TIMESTAMP
        }

        # Add message to Firestore
        db.collection('messages').add(message_data)

        return jsonify({
            "success": True,
            "message": "Message sent successfully!",
            "data": {
                "sender_email": session['user_email'],
                "sender_profile_picture": sender_data.get('profile_picture'),
                "message": message,
                "timestamp": datetime.now().timestamp()
            }
        })

    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/appointments')
def appointments():
    if ('user_email' not in session):
        return redirect(url_for('login'))
    
    try:
        user = auth.get_user_by_email(session['user_email'])
        user_doc = db.collection('users').document(user.uid).get()
        user_data = user_doc.to_dict()

        if (session['user_role'] == 'doctor'):
            # Get all clients with appointments for the logged-in doctor
            clients = db.collection('users').where('role', '==', 'client').where('doctor_email', '==', session['user_email']).stream()
            appointments_list = []
            
            for client in clients:
                client_data = client.to_dict()
                if (client_data.get('appointment_date')):  # Check if appointment exists
                    appointments_list.append({
                        'client_name': client_data.get('name', 'Unknown'),
                        'client_email': client_data.get('email', ''),
                        'date': client_data.get('appointment_date', ''),
                        'time': client_data.get('appointment_time', ''),
                        'reason': client_data.get('appointment_reason', '')
                    })
            
            return render_template('appointments.html', 
                                appointments=appointments_list,
                                is_doctor=True,
                                user_data=user_data)
        else:
            # Get client's own appointment
            appointment = {
                'client_name': user_data.get('name'),
                'client_email': user_data.get('email'),
                'date': user_data.get('appointment_date'),
                'time': user_data.get('appointment_time'),
                'reason': user_data.get('appointment_reason')
            }
            
            return render_template('appointments.html',
                                appointments=[appointment],
                                is_doctor=False,
                                user_data=user_data)

    except Exception as e:
        print(f"Error in appointments route: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/upload_diagnostic_photo', methods=['POST'])
def upload_diagnostic_photo():
    if ('user_email' in session):
        file = request.files.get('diagnostic_photo')

        if (file and file.filename != ''):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(file_path)
            file_url = upload_result['secure_url']

            user = auth.get_user_by_email(session['user_email'])
            db.collection('users').document(user.uid).update({'diagnostic_photo': file_url})

            return jsonify({"success": True, "message": "Diagnostic photo uploaded successfully!"})

        return jsonify({"success": False, "message": "No file selected."})

    return redirect(url_for('login'))


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if ('user_email' not in session):
        return redirect(url_for('login'))

    try:
        user = auth.get_user_by_email(session['user_email'])
        user_doc = db.collection('users').document(user.uid).get()
        
        if (not user_doc.exists):
            return redirect(url_for('login'))
            
        user_data = user_doc.to_dict()
        messages = {}

        if (request.method == 'POST'):
            if ('new_name' in request.form):
                new_name = request.form.get('new_name')
                if (new_name):
                    try:
                        auth.update_user(user.uid, display_name=new_name)
                        db.collection('users').document(user.uid).update({'name': new_name})
                        messages['name'] = "Name updated successfully!"
                    except Exception as e:
                        messages['name'] = f"Error updating name: {str(e)}"
            
            # Handle password change
            if ('new_password' in request.form and 'confirm_password' in request.form):
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')
                if (new_password and new_password == confirm_password):
                    try:
                        auth.update_user(user.uid, password=new_password)
                        messages['password'] = "Password updated successfully!"
                    except Exception as e:
                        messages['password'] = f"Error updating password: {str(e)}"
        
        return render_template('settings.html', user_data=user_data, messages=messages)

    except Exception as e:
        print(f"Error in settings route: {str(e)}")
        return redirect(url_for('login'))


def upload_to_firebase(file_path):
    bucket = storage.bucket()
    blob = bucket.blob(file_path)
    blob.upload_from_filename(file_path)
    blob.make_public()
    return blob.public_url


@app.route('/dashboard')
def dashboard():
    if ('user_email' in session):
        if (session['user_role'] == 'client'):
            return redirect(url_for('client_dashboard'))
        elif (session['user_role'] == 'doctor'):
            return redirect(url_for('doctor_dashboard'))
    
    return redirect(url_for('login'))

@app.route('/upload_medical_image', methods=['POST'])
def upload_medical_image():
    if ('user_email' not in session):
        return jsonify({"success": False, "message": "Please login first"}), 401

    if ('medical_image' not in request.files):
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    medical_image = request.files['medical_image']
    description = request.form.get('image_description', '')

    if (medical_image.filename == ''):
        return jsonify({"success": False, "message": "No file selected"}), 400

    try:
        # Read the image file
        image_bytes = medical_image.read()
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            medical_image,
            folder=f"medical_images/{session['user_email']}"
        )
        file_url = upload_result['secure_url']

        # Get user reference
        user = auth.get_user_by_email(session['user_email'])
        
        # Store in Firestore
        image_data = {
            'url': file_url,
            'description': description,
            'upload_date': firestore.SERVER_TIMESTAMP,
            'filename': medical_image.filename,
            'status': 'pending_analysis'
        }

        # Add to user's medical_images collection
        db.collection('users').document(user.uid)\
          .collection('medical_images').add(image_data)

        return jsonify({
            "success": True, 
            "message": "Image uploaded successfully",
            "redirect": url_for('upload_page')
        })

    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error uploading image: {str(e)}"
        }), 500

@app.route('/upload')
def upload_page():
    if ('user_email' not in session):
        return redirect(url_for('login'))

    try:
        # Get user data
        user = auth.get_user_by_email(session['user_email'])
        user_doc = db.collection('users').document(user.uid).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        
        # Fetch existing medical images
        medical_images = []
        images_ref = db.collection('users').document(user.uid)\
                     .collection('medical_images')\
                     .order_by('upload_date', direction=firestore.Query.DESCENDING)\
                     .stream()
        
        for img in images_ref:
            img_data = img.to_dict()
            if ('upload_date' in img_data and img_data['upload_date']):
                img_data['upload_date'] = img_data['upload_date'].strftime('%Y-%m-%d %H:%M:%S')
            medical_images.append(img_data)

        return render_template('upload.html',
                            user_data=user_data,
                            medical_images=medical_images,
                            profile_picture=user_data.get('profile_picture'))
                            
    except Exception as e:
        print(f"Error in upload page: {str(e)}")
        return redirect(url_for('client_dashboard'))

@app.route('/confirm_analysis', methods=['POST'])
def confirm_analysis():
    if ('user_email' not in session or session['user_role'] != 'doctor'):
        return redirect(url_for('login'))

    image_id = request.form.get('image_id')
    if (not image_id):
        return jsonify({"success": False, "message": "Image ID is required."})

    try:
        # Update the analysis confirmation status in Firestore
        db.collection('users').document(user.uid)\
          .collection('medical_images').document(image_id)\
          .update({'analysis_confirmed': True})

        return redirect(url_for('doctor_dashboard'))

    except Exception as e:
        print(f"Error confirming analysis: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/client_images/<client_email>')
def client_images(client_email):
    if ('user_email' in session and session['user_role'] == 'doctor'):
        try:
            client_doc = db.collection('users').where('email', '==', client_email).limit(1).get()
            if (client_doc):
                client_data = client_doc[0].to_dict()
                client_name = client_data.get('name', 'Unknown')

                # Fetch medical images
                medical_images = []
                images_ref = db.collection('users').document(client_doc[0].id)\
                             .collection('medical_images')\
                             .order_by('upload_date', direction=firestore.Query.DESCENDING)\
                             .stream()
                
                for img in images_ref:
                    img_data = img.to_dict()
                    img_data['id'] = img.id
                    img_data['upload_date'] = img_data['upload_date'].strftime('%Y-%m-%d %H:%M:%S')\
                        if (img_data.get('upload_date')) else 'Unknown'
                    medical_images.append(img_data)

                return render_template('client_images.html',
                                       client_name=client_name,
                                       medical_images=medical_images)
        except Exception as e:
            print(f"Error fetching client images: {str(e)}")
            return redirect(url_for('doctor_dashboard'))
    return redirect(url_for('login'))

@app.route('/check_session')
def check_session():
    if 'user_email' in session:
        redirect_url = url_for('doctor_dashboard') if session['user_role'] == 'doctor' else url_for('client_dashboard')
        return jsonify({
            'logged_in': True,
            'redirect_url': redirect_url
        })
    return jsonify({'logged_in': False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
