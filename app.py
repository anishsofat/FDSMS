from os import name
import firebase_admin
import pyrebase
from firebase_admin import credentials, auth, firestore, storage
import json
from flask import Flask, render_template, url_for, request, redirect , session
from functools import wraps
import datetime
import requests
from requests.exceptions import HTTPError
from flask_session import Session

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD']=True
app.secret_key ='a very very very long string'

cred = credentials.Certificate('fbAdminConfig.json')
firebase = firebase_admin.initialize_app(cred,json.load(open('fbConfig.json')))
pyrebase_pb = pyrebase.initialize_app(json.load(open('fbConfig.json')))
db = firestore.client()
bucket = storage.bucket()
# storage = pyrebase_pb.storage()


def check_token(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if session['jwt_token']==None:
            session['sign_message']="No Token Provided. Try Logging In."
            return redirect(url_for('login'))
        try:
            session['jwt_token'] = pyrebase_pb.auth().refresh(session['refresh_token'])['idToken']
            user = auth.verify_id_token(session['jwt_token'])
            request.user = user
        except:
            session['sign_message']="Invalid Token Provided. Trying Logging again."
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

@app.route('/api/userinfo')
@check_token
def userinfo():
    return {'data'}, 200

@app.route('/signup/resturant', methods=['POST', 'GET'])
def restaurantsignup():
    email = request.form['email']
    password = request.form['password']
    area = request.form['area']
    name = request.form['name']
    local_file_obj = request.files['local_file_path']
    session['sign_message']="Fail"
    
    try:
        user = auth.create_user(
            email=email,
            password=password
        )
    except:
        session['sign_message']="error creating user in firebase"
        return redirect(url_for('restaurantSignup'))
    try:
        json_data = {
            "name" : name,
            "email" : email,
            "area" : area,
        }
        db.collection("restaurant").document(user.uid).set(json_data)
        db.collection("type").document(user.uid).set({"type" : "restaurant"})
        
    except:
        session['sign_message']="error adding user text data in firestore"
        return redirect(url_for('restaurantSignup'))
    try:
        storage_file_path = "restaurantProfilePics/"+user.uid+".jpg"
        blob = bucket.blob(storage_file_path)
        blob.upload_from_file(local_file_obj,content_type="image/jpeg")
        session['sign_message']="Restaurant SignedUp. Please Login"
        return redirect(url_for('login'))
    except Exception as e:
        print(e)
        session['sign_message']="error uploading photo in firebase storage"
        return redirect(url_for('restaurantSignup'))

@app.route('/signup/deliveryAgent', methods=['POST', 'GET'])
def deliveryAgentsignup():
    email = request.form['email']
    password = request.form['password']
    gender = request.form['gender']
    area = request.form['area']
    mobile = request.form['mobile']
    dob = request.form['dob']
    name = request.form['name']
    local_file_obj = request.files['local_file_path']
    session['sign_message']="Fail"
    try:
        user = auth.create_user(
            email=email,
            password=password
        )
    except:
        session['sign_message']="error creating user in firebase"
        return redirect(url_for('deliveryAgentSignup'))
    try:
        json_data = {
            "name" : name,
            "dob" : dob,
            "mobile" : mobile,
            "email" : email,
            "gender" : gender,
            "area" : area,
        }
        db.collection("deliveryAgent").document(user.uid).set(json_data)
        db.collection("type").document(user.uid).set({"type" : "deliveryAgent"})
    except:
        session['sign_message']="error adding user text data in firestore"
        return redirect(url_for('deliveryAgentSignup'))
    try:
        storage_file_path = "deliveryProfilePics/"+user.uid+".jpg"
        blob = bucket.blob(storage_file_path)
        blob.upload_from_file(local_file_obj,content_type="image/jpeg")
        session['sign_message']="Delivery Agent SignedUp. Please Login"
        return redirect(url_for('login'))
    except:
        session['sign_message']="error uploading photo in firebase storage"
        return redirect(url_for('deliveryAgentSignup'))



@app.route('/signup/customer', methods=['POST','GET'])
def signup():

    email = request.form['email']
    password = request.form['password']
    gender = request.form['gender']
    area = request.form['area']
    mobile = request.form['mobile']
    dob = request.form['dob']
    name = request.form['name']
    local_file_obj = request.files['local_file_path']

    # create user
    try:
        user = auth.create_user(
            email=email,
            password=password
        )
    except:
        session['sign_message']="error creating user in firebase"
        return redirect(url_for('customerSignup'))
    
    # add data in fire-store
    try:
        json_data = {
            "name" : name,
            "dob" : dob,
            "mobile" : mobile,
            "email" : email,
            "gender" : gender,
            "area" : area,
        }
        db.collection("customer").document(user.uid).set(json_data)
        db.collection("type").document(user.uid).set({"type" : "customer"})
    except:
        session['sign_message']="error adding user text data in firestore"
        return redirect(url_for('customerSignup'))

    # upload profile picture
    try:
        storage_file_path = "customerProfilePics/"+user.uid+".jpg"
        blob = bucket.blob(storage_file_path)
        blob.upload_from_file(local_file_obj,content_type="image/jpeg")
        return redirect(url_for('login'))
    except:
        session['sign_message']="error uploading photo in firebase storage"
        return redirect(url_for('customerSignup'))

@app.route("/temp")
def temp():
    # blob = bucket.blob("customerProfilePics/"+"YQ2pF5uHW7ZCvfpIzUD1sTcZL5n2"+".jpg")
    blob = bucket.blob("restaurantProfilePics/"+"oDtSvO2uB8UE6889JHPRFTLvHJY2"+".jpg")

    imagePublicURL = blob.generate_signed_url(datetime.timedelta(seconds=300), method='GET')
    return {"imageLink":imagePublicURL},200

@app.route('/api/token', methods=['POST','GET'])
def token():
    email = request.form['email']
    password = request.form['password']
    try:
        user = pyrebase_pb.auth().sign_in_with_email_and_password(email, password)
        # user2 = pyrebase_pb.auth().get_account_info(user['idToken'])
        user_type = db.collection('type').document(user["localId"]).get().to_dict()["type"]
        json_data = db.collection(user_type).document(user["localId"]).get().to_dict()
        session['session_user']= json_data
        session['session_user']['user_type']=user_type
        session['jwt_token']=user['idToken']
        session['refresh_token']=user['refreshToken']
        print(session['session_user']['user_type'])
        if user_type=="customer" : 
            return redirect(url_for('customerDashboard'))
        elif user_type == "restaurant" : 
            return redirect(url_for('restaurantDashboard'))
        elif user_type == "deliveryAgent" :
            return redirect(url_for('deliveryAgentDashboard'))
        elif user_type == "admin" :
            return redirect(url_for('adminDashboard'))
    except:
        session['sign_message']="Please enter the correct credentials"
        return redirect(url_for('login'))

@app.route('/')
def index():
    session['sign_message']="False"
    message=session['sign_message']
    return render_template('index.html', message=message)

@app.route('/Signup')
def signUp():
    return render_template('signup.html')



@app.route('/login')
def login():
    message=session['sign_message']
    session['sign_message']="False"
    return render_template('login.html', message=message)

@app.route('/adminLogin')
def adminLogin():
    return render_template('adminLogin.html')

@app.route('/customerSignup')
def customerSignup():
    message=session['sign_message']
    session['sign_message']="False"
    return render_template('customerSignup.html', message=message)

@app.route('/restaurantSignup')
def restaurantSignup():
    message=session['sign_message']
    session['sign_message']="False"
    return render_template('restaurantSignup.html', message=message)

@app.route('/deliveryAgentSignup')
def deliveryAgentSignup():
    message=session['sign_message']
    session['sign_message']="False"
    return render_template('deliveryAgentSignup.html', message=message)

@app.route('/customerDashboard')
@check_token
def customerDashboard():
    user=session['session_user']
    return render_template('customerDashboard.html', user=user)

@app.route('/restaurantDashboard')
@check_token
def restaurantDashboard():
    user=session['session_user']
    return render_template('restaurantDashboard.html', user=user)

@app.route('/deliveryAgentDashboard')
@check_token
def deliveryAgentDashboard():
    user=session['session_user']
    return render_template('deliveryAgentDashboard.html', user=user)

@app.route('/adminDashboard')
@check_token
def adminDashboard():
    user=session['session_user']
    return render_template('adminDashboard.html', user=user)

@app.route('/personalData')
@check_token
def personalData():
    user=session['session_user']
    return render_template('personalData.html', user=user)

@app.route('/logout')
@check_token
def logout():
    session['jwt_token']=None
    session['session_user']=None
    session['refresh_token']=None
    session['sign_message']="Successfully Logged Out"
    return redirect(url_for('login'))

@app.route('/createMenu')
def createMenu():
    user = session['session_user']
    return render_template('createMenu.html', user=user)

@app.route('/addFoodItem')
def addFoodItem():
    user = session['session_user']
    return render_template('addFoodItem.html', user=user)

@app.route('/finishMenu')
def finishMenu():
    user = session['session_user']
    return render_template('finishMenu.html', user=user)

@app.route('/addFoodItem/adder', methods=['POST','GET'])
def foodItemAdder():
    name = request.form['name']
    price = request.form['price']
    local_file_obj = request.files['local_file_path']
    
    # Add to database
    # Add to database
    # Add to database
    # Add to database
    # Add to database

    foodItem = {'name': name, 'price': price}
    print(foodItem)
    return redirect(url_for('createMenu'))
    
@app.route('/allRestaurant')
@check_token
def allRestaurant():
    user=session['session_user']
    restaurantList=[]
    docs=db.collection('restaurant').stream()
    for doc in docs:
        restaurantList.append(doc.to_dict())
        
    return render_template('allRestaurant.html', user=user, restaurantList=restaurantList)

@app.route('/allCustomers')
@check_token
def allCustomers():
    user=session['session_user']
    customerList=[]
    docs=db.collection('customer').stream()
    for doc in docs:
        customerList.append(doc.to_dict())
        
    return render_template('allCustomers.html', user=user, customerList=customerList)

@app.route('/allDeliveryAgents')
@check_token
def allDeliveryAgents():
    user=session['session_user']
    deliveryAgentList=[]
    docs=db.collection('deliveryAgent').stream()
    for doc in docs:
        deliveryAgentList.append(doc.to_dict())
        
    return render_template('allDeliveryAgents.html', user=user, deliveryAgentList=deliveryAgentList)

if __name__ == "__main__":
    # cache.init_app(app)
    app.run(debug=True)