
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
                role = user_data.get('role', 'patient')  # Default to 'patient' if role is not found
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
            # Get form data
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')
            
            # Create user in Firebase Auth
            user = auth.create_user(
                email=email,
                password=password,
                display_name=name
            )

            # Handle profile picture upload
            profile_picture_url = None
            if 'profile_picture' in request.files:
                profile_pic = request.files['profile_picture']
                if profile_pic and profile_pic.filename:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            profile_pic,
                            folder=f"profile_pictures/{email}"
                        )
                        profile_picture_url = upload_result['secure_url']
                    except Exception as e:
                        print(f"Error uploading profile picture: {str(e)}")

            # Prepare user data for Firestore
            user_data = {
                'name': name,
                'email': email,
                'phone': request.form.get('phone', ''),
                'role': role,
                'profile_picture': profile_picture_url,
                'created_at': firestore.SERVER_TIMESTAMP
            }

            # Add role-specific data
            if role == 'patient':
                user_data.update({
                    'appointment_date': request.form.get('appointment_date'),
                    'appointment_time': request.form.get('appointment_time'),
                    'appointment_reason': request.form.get('appointment_reason'),
                    'doctor_email': request.form.get('doctor_email'),
                    'status': 'pending'
                })
            elif role == 'doctor':
                user_data.update({
                    'specialty': request.form.get('specialty', ''),
                    'license': request.form.get('license', '')
                })

            # Save user data in Firestore
            db.collection('users').document(user.uid).set(user_data)

            return jsonify({
                "success": True,
                "message": "Signup successful!",
                "uid": user.uid
            })

        except Exception as e:
            print(f"Error in signup: {str(e)}")
            return jsonify({
                "success": False,
                "message": str(e)
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
    if ('user_email' in session and session['user_role'] == 'patient'):
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


@app.route('/patients')
def patients():
    if 'user_email' not in session or session['user_role'] != 'doctor':
        return redirect(url_for('login'))

    try:
        # Fetch all clients/patients
        clients = []
        clients_ref = db.collection('users').where('role', '==', 'patient').stream()
        
        for client in clients_ref:
            client_data = client.to_dict()
            # Get medical images count for each client
            images_ref = db.collection('users').document(client.id)\
                         .collection('medical_images').stream()
            images_count = sum(1 for _ in images_ref)
            
            clients.append({
                'name': client_data.get('name', 'Unknown'),
                'email': client_data.get('email'),
                'profile_picture': client_data.get('profile_picture'),
                'images_count': images_count,
                'last_visit': client_data.get('last_visit', 'No visits yet')
            })

        return render_template('patients.html', clients=clients)
        
    except Exception as e:
        print(f"Error fetching patients: {str(e)}")
        return redirect(url_for('doctor_dashboard'))

@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'user_email' in session and session['user_role'] == 'doctor':
        try:
            user = auth.get_user_by_email(session['user_email'])
            user_doc = db.collection('users').document(user.uid).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                profile_picture = user_data.get('profile_picture', None)
                
                # Fetch clients
                clients = []
                clients_ref = db.collection('users').where('role', '==', 'patient').stream()
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
        sent_messages = db.collection('messages')\
            .where('sender_email', '==', user_email)\
            .where('recipient_email', '==', recipient_email)\
            .stream()

        # Get messages where current user is recipient
        received_messages = db.collection('messages')\
            .where('sender_email', '==', recipient_email)\
            .where('recipient_email', '==', user_email)\
            .stream()

        # Process sent messages
        for msg in sent_messages:
            msg_data = msg.to_dict()
            timestamp = msg_data.get('timestamp')
            if timestamp and timestamp.timestamp() > after_timestamp:
                messages.append({
                    'sender_email': user_email,
                    'sender_profile_picture': session.get('profile_picture'),
                    'message': msg_data['message'],
                    'timestamp': timestamp.timestamp()
                })

        # Process received messages
        for msg in received_messages:
            msg_data = msg.to_dict()
            timestamp = msg_data.get('timestamp')
            if timestamp and timestamp.timestamp() > after_timestamp:
                messages.append({
                    'sender_email': recipient_email,
                    'sender_profile_picture': msg_data.get('sender_profile_picture'),
                    'message': msg_data['message'],
                    'timestamp': timestamp.timestamp()
                })

        # Sort messages by timestamp
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
        # Get sender info
        sender = auth.get_user_by_email(session['user_email'])
        sender_doc = db.collection('users').document(sender.uid).get()
        sender_data = sender_doc.to_dict()

        # Generate a unique ID using timestamp and random string
        message_id = f"{int(time.time() * 1000)}-{os.urandom(4).hex()}"

        message_data = {
            'id': message_id,
            'sender': sender.uid,
            'sender_email': session['user_email'],
            'sender_name': sender_data.get('name', ''),
            'sender_profile_picture': sender_data.get('profile_picture', ''),
            'recipient_email': recipient_email,
            'message': message,
            'timestamp': firestore.SERVER_TIMESTAMP
        }

        # Add message to Firestore using the generated ID
        db.collection('messages').document(message_id).set(message_data)

        return jsonify({
            "success": True,
            "message": "Message sent successfully!",
            "message_id": message_id  # Return the message ID
        })

    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/appointments')
def appointments():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    try:
        user = auth.get_user_by_email(session['user_email'])
        user_doc = db.collection('users').document(user.uid).get()
        user_data = user_doc.to_dict()

        if session['user_role'] == 'doctor':
            # Get all patients with appointments for the logged-in doctor
            patients = db.collection('users').where('role', '==', 'patient').where('doctor_email', '==', session['user_email']).stream()
            appointments_list = []
            
            for patient in patients:
                patient_data = patient.to_dict()
                if patient_data.get('appointment_date'):  # Check if appointment exists
                    appointments_list.append({
                        'patient_name': patient_data.get('name', 'Unknown'),
                        'patient_email': patient_data.get('email', ''),
                        'date': patient_data.get('appointment_date', ''),
                        'time': patient_data.get('appointment_time', ''),
                        'reason': patient_data.get('appointment_reason', ''),
                        'profile_picture': patient_data.get('profile_picture', url_for('static', filename='images/default_profile.jpg')),
                        'status': patient_data.get('status', 'Pending')
                    })
            
            return render_template('appointments.html', 
                                   appointments=appointments_list,
                                   is_doctor=True,
                                   profile_picture=session.get('profile_picture'),
                                   user_data=user_data)
        else:
            # Get patient's own appointment
            appointment = {
                'patient_name': user_data.get('name'),
                'patient_email': user_data.get('email'),
                'date': user_data.get('appointment_date'),
                'time': user_data.get('appointment_time'),
                'reason': user_data.get('appointment_reason'),
                'profile_picture': user_data.get('profile_picture', url_for('static', filename='images/default_profile.jpg')),
                'status': user_data.get('status', 'Pending')
            }
            
            return render_template('appointments.html',
                                   appointments=[appointment],
                                   is_doctor=False,
                                   profile_picture=session.get('profile_picture'),
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
        if (session['user_role'] == 'patient'):
            return redirect(url_for('client_dashboard'))
        elif (session['user_role'] == 'doctor'):
            return redirect(url_for('doctor_dashboard'))
    
    return redirect(url_for('login'))

@app.route('/upload_medical_image', methods=['POST'])
def upload_medical_image():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Please login first"}), 401

    if 'medical_image' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    medical_image = request.files['medical_image']
    description = request.form.get('image_description', '')

    if medical_image.filename == '':
        return jsonify({"success": False, "message": "No file selected"}), 400

    try:
        # Save file temporarily and get image bytes for AI processing
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(medical_image.filename))
        medical_image.save(temp_path)
        
        # Process image with AI model
        with open(temp_path, 'rb') as img_file:
            img_bytes = img_file.read()
            processed_image = preprocess_image(img_bytes)
            if processed_image is not None:
                prediction = model.predict(processed_image)
                predicted_class = categories[np.argmax(prediction)]
                confidence = float(np.max(prediction))
            else:
                predicted_class = "Error processing image"
                confidence = 0.0

        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(temp_path,
            folder=f"medical_images/{session['user_email']}"
        )
        file_url = upload_result['secure_url']

        # Get user reference
        user = auth.get_user_by_email(session['user_email'])
        
        # Store in Firestore with AI results
        image_data = {
            'url': file_url,
            'description': description,
            'upload_date': firestore.SERVER_TIMESTAMP,
            'filename': medical_image.filename,
            'ai_prediction': predicted_class,
            'ai_confidence': confidence,
            'status': 'pending_doctor_confirmation',
            'doctor_confirmed': False
        }

        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # Add to user's medical_images collection
        db.collection('users').document(user.uid)\
          .collection('medical_images').add(image_data)

        return jsonify({
            "success": True, 
            "message": "Image uploaded and analyzed successfully",
            "prediction": predicted_class,
            "confidence": confidence,
            "redirect": url_for('upload_page')
        })

    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error uploading image: {str(e)}"
        }), 500

# Add new route for doctor confirmation
@app.route('/confirm_diagnosis', methods=['POST'])
def confirm_diagnosis():
    if 'user_email' not in session or session['user_role'] != 'doctor':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        image_id = data.get('image_id')
        diagnosis = data.get('diagnosis')
        client_email = data.get('client_email')  # Get client email from request

        if not all([image_id, diagnosis, client_email]):
            return jsonify({"success": False, "message": "Missing required data"}), 400

        # First, get the client's document
        clients = db.collection('users').where('email', '==', client_email).limit(1).stream()
        client_doc = next(clients, None)
        
        if not client_doc:
            return jsonify({"success": False, "message": "Client not found"}), 404

        # Now update the specific image in the client's medical_images subcollection
        try:
            db.collection('users').document(client_doc.id)\
              .collection('medical_images').document(image_id)\
              .update({
                  'doctor_confirmed': True,
                  'doctor_diagnosis': diagnosis,
                  'confirmed_by': session['user_email'],
                  'confirmation_date': firestore.SERVER_TIMESTAMP
              })

            return jsonify({
                "success": True,
                "message": "Diagnosis confirmed successfully"
            })
        except Exception as e:
            print(f"Error updating image: {str(e)}")
            return jsonify({"success": False, "message": "Error updating image"}), 500

    except Exception as e:
        print(f"Confirmation error: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error confirming diagnosis: {str(e)}"
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
    if 'user_email' not in session or session['user_role'] != 'doctor':
        return redirect(url_for('login'))

    try:
        clients = db.collection('users').where('email', '==', client_email).limit(1).stream()
        client_doc = next(clients, None)
        
        if not client_doc:
            return redirect(url_for('doctor_dashboard'))
            
        client_data = client_doc.to_dict()
        
        # Fetch medical images
        medical_images = []
        images_ref = db.collection('users').document(client_doc.id)\
                     .collection('medical_images')\
                     .order_by('upload_date', direction=firestore.Query.DESCENDING)\
                     .stream()
        
        for img in images_ref:
            img_data = img.to_dict()
            img_data['id'] = img.id
            
            # Handle missing values with defaults
            if img_data.get('upload_date'):
                img_data['upload_date'] = img_data['upload_date'].strftime('%Y-%m-%d %H:%M:%S')
            else:
                img_data['upload_date'] = 'Unknown'
                
            # Set default values for AI prediction and confidence
            if 'ai_prediction' not in img_data:
                img_data['ai_prediction'] = 'Not analyzed'
            if 'ai_confidence' not in img_data:
                img_data['ai_confidence'] = 0.0
                
            medical_images.append(img_data)

        return render_template('client_images.html',
                           client_name=client_data.get('name', 'Unknown'),
                           client_email=client_email,
                           medical_images=medical_images)
                           
    except Exception as e:
        print(f"Error in client_images: {str(e)}")
        return redirect(url_for('doctor_dashboard'))

@app.route('/check_session')
def check_session():
    if 'user_email' in session:
        redirect_url = url_for('doctor_dashboard') if session['user_role'] == 'doctor' else url_for('client_dashboard')
        return jsonify({
            'logged_in': True,
            'redirect_url': redirect_url
        })
    return jsonify({'logged_in': False})

@app.route('/medical_records')
def medical_records():
    if 'user_email' not in session or session['user_role'] != 'client':
        return redirect(url_for('login'))

    try:
        # Get user data
        user = auth.get_user_by_email(session['user_email'])
        user_doc = db.collection('users').document(user.uid).get()
        user_data = user_doc.to_dict()

        # Fetch medical images and diagnoses
        medical_records = []
        images_ref = db.collection('users').document(user.uid)\
                     .collection('medical_images')\
                     .order_by('upload_date', direction=firestore.Query.DESCENDING)\
                     .stream()
        
        for img in images_ref:
            img_data = img.to_dict()
            record = {
                'id': img.id,
                'url': img_data.get('url'),
                'upload_date': img_data.get('upload_date').strftime('%Y-%m-%d %H:%M:%S') if img_data.get('upload_date') else 'Unknown',
                'ai_prediction': img_data.get('ai_prediction', 'Not analyzed'),
                'ai_confidence': img_data.get('ai_confidence', 0.0),
                'doctor_diagnosis': img_data.get('doctor_diagnosis'),
                'doctor_confirmed': img_data.get('doctor_confirmed', False),
                'confirmed_by': img_data.get('confirmed_by'),
                'confirmation_date': img_data.get('confirmation_date'),
                'description': img_data.get('description', '')
            }
            medical_records.append(record)

        return render_template('medical_records.html', 
                            user_data=user_data,
                            medical_records=medical_records,
                            profile_picture=user_data.get('profile_picture'))

    except Exception as e:
        print(f"Error fetching medical records: {str(e)}")
        return redirect(url_for('client_dashboard'))

@app.route('/update_appointment', methods=['POST'])
def update_appointment():
    if 'user_email' not in session or session['user_role'] != 'patient':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        new_date = data.get('date')
        new_time = data.get('time')

        if not all([new_date, new_time]):
            return jsonify({"success": False, "message": "Date and time are required"}), 400

        # Update the appointment in Firestore
        user = auth.get_user_by_email(session['user_email'])
        db.collection('users').document(user.uid).update({
            'appointment_date': new_date,
            'appointment_time': new_time,
            'last_updated': firestore.SERVER_TIMESTAMP
        })

        # Notify the doctor about the change (optional)
        user_doc = db.collection('users').document(user.uid).get()
        user_data = user_doc.to_dict()
        doctor_email = user_data.get('doctor_email')
        
        if doctor_email:
            notification_data = {
                'type': 'appointment_update',
                'patient_name': user_data.get('name'),
                'patient_email': session['user_email'],
                'new_date': new_date,
                'new_time': new_time,
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            db.collection('notifications').add(notification_data)

        return jsonify({
            "success": True,
            "message": "Appointment updated successfully"
        })

    except Exception as e:
        print(f"Error updating appointment: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error updating appointment: {str(e)}"
        }), 500

@app.route('/change_appointment')
def change_appointment():
    if 'user_email' not in session or session['user_role'] != 'patient':
        return redirect(url_for('login'))

    user = auth.get_user_by_email(session['user_email'])
    user_doc = db.collection('users').document(user.uid).get()
    user_data = user_doc.to_dict()

    return render_template('change_appointment.html', profile_picture=user_data.get('profile_picture'))

@app.route('/predict_diabetes', methods=['GET', 'POST'])
def predict_diabetes():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Get form data
            pregnancies = int(request.form.get('pregnancies'))
            glucose = int(request.form.get('glucose'))
            blood_pressure = int(request.form.get('blood_pressure'))
            skin_thickness = int(request.form.get('skin_thickness'))
            insulin = int(request.form.get('insulin'))
            bmi = float(request.form.get('bmi'))
            diabetes_pedigree_function = float(request.form.get('diabetes_pedigree_function'))
            age = int(request.form.get('age'))

            # Prepare data for prediction
            input_data = [[pregnancies, glucose, blood_pressure, skin_thickness, insulin, bmi, diabetes_pedigree_function, age]]
            input_data_scaled = scaler.transform(input_data)  # Scale the input data
            prediction = diabetes_model.predict(input_data_scaled)
            result = 'Positive' if prediction[0] == 1 else 'Negative'

            return render_template('predict_diabetes.html', result=result)

        except Exception as e:
            print(f"Error predicting diabetes: {str(e)}")
            return render_template('predict_diabetes.html', error=str(e))

    return render_template('predict_diabetes.html')

if __name__ == '__main__':    
    app.run(debug=True, host='0.0.0.0', port=5000)
