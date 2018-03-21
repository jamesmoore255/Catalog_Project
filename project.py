from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Category, Items
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog App"


# Connect to Database and create database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token


    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]


    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the server token exchange we have to
        split the token first on commas and select the first index which gives us the key : value
        for the server access token then we split it on colons to pull out the actual token value
        and replace the remaining quotes with nothing so that it can be used directly in the graph
        api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).first()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


#JSON APIs to view Catalog information.
@app.route('/catalog/JSON')
def catalogJSON():
	catalog = session.query(Catalog).all()
	return jsonify(catalog=[c.serialize for c in catalog])

@app.route('/catalog/<int:category_id>/items/JSON')
def categoryJSON(category_id):
	catalog = session.query(Catalog).filter_by(id=catalog_id).one()
	items = session.query(Items).filter_by(catalog_id=catalog_id).all()
	return jsonify(Items=[i.serialize for i in items])

@app.route('/catalog/<int:category_id>/items/<int:item_id>/JSON')
def categoryItemJson(category_id, item_id):
	item = session.query(Items).filter_by(id=item_id).one()
	return jsonify(Items=[i.serialize for i in item])


# Catalog main page with list of categories and latest items

@app.route('/')
@app.route('/catalog/')
def catalogHome():
	categories = session.query(Category).order_by(Category.name.desc())
	items = session.query(Items).order_by(Items.id.desc())
	if 'username' not in login_session:
		return render_template('publicCatalog.html', categories=categories, items=items)
	else:
		return render_template('catalog.html', categories=categories, items=items)

@app.route('/catalog/<int:category_id>/edit/', methods=['GET', 'POST'])
def categoryEdit(category_id):
	categoryEdit = session.query(Category).filter_by(id=category_id).one()
	if 'username' not in login_session:
		return redirect('/login')
 	if categoryEdit.user_id != login_session['user_id']:
 		return "<script>function myFunction() {alert('You are not authorized to edit this category. Please create your own category in order to edit.');}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		categoryEdit.name = request.form['name']
		flash('Category Successfully Edited %s' % categoryEdit.name)
		return redirect(url_for('catalogHome'))
	else:
		return render_template('editCategory.html', category=categoryEdit)


@app.route('/catalog/<int:category_id>/delete/', methods=['GET', 'POST'])
def categoryDelete(category_id):
	categoryDelete = session.query(Category).filter_by(id=category_id).one()
	if 'username' not in login_session:
		return redirect('/login')
 	if categoryDelete.user_id != login_session['user_id']:
	 	return "<script>function myFunction() {alert('You are not authorized to delete this catalog. Please create your own catalog in order to delete.');}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		session.delete(categoryDelete)
		flash('%s Successfully Deleted' % categoryDelete.name)
		session.commit()
		return redirect(url_for('catalogHome'))
	else:
		return render_template('deleteCategory.html', category=categoryDelete)

# Create a new category

@app.route('/catalog/create/', methods=['GET', 'POST'])
def categoryCreate():
	if 'username' not in login_session:
		return redirect('/login')
	if request.method == 'POST':
		newCategory = Category(name=request.form['name'], user_id=login_session['user_id'])
		session.add(newCategory)
		flash('New Category %s Successfully Created' % newCategory.name)
		session.commit()
		return redirect(url_for('catalogHome'))
	else:
		return render_template('createCategory.html')

# Categories and items of specific category

@app.route('/catalog/<int:category_id>/')
@app.route('/catalog/<int:category_id>/items/')
def categoryItems(category_id):
	categories = session.query(Category).order_by(asc(Category.name))
	category = session.query(Category).filter_by(id=category_id).first()
	items = session.query(Items).filter_by(category_id=category.id).all()
	if 'username' not in login_session:
		return render_template('publicCategory.html', items=items, category=category, categories=categories)
	else:
		return render_template('categoryItem.html', items=items, category=category, categories=categories)


@app.route('/catalog/<int:category_id>/<int:item_id>/item')
def specificItem(item_id, category_id):
	item = session.query(Items).filter_by(category_id=category_id, id=item_id).first()
	if 'username' not in login_session:
		return render_template('publicSpecific.html', item=item)
	else:
		return render_template('specificItem.html', item=item)

@app.route('/catalog/<int:category_id>/<int:item_id>/edit/', methods=['GET', 'POST'])
def itemEdit(category_id, item_id):
	if 'username' not in login_session:
		return redirect('/login')
	item = session.query(Items).filter_by(category_id=category_id, id=item_id).first()
	if login_session['user_id'] != item.user_id:
		return "<script>function myFunction() {alert('You are not authorized to edit this item. Please create your own catalog in order to edit items.');}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		if request.form['name']:
			item.name = request.form['name']
		if request.form['description']:
			item.description = request.form['description']
		session.add(item)
		session.commit()
		return redirect(url_for('specificItem', category_id=category_id, item_id=item_id))
	else:
		return render_template('editItem.html', item=item)

@app.route('/catalog/<int:category_id>/<int:item_id>/delete/', methods=['GET', 'POST'])
def itemDelete(category_id, item_id):
	if 'username' not in login_session:
		return redirect('/login')
	item = session.query(Items).filter_by(category_id=category_id, id=item_id).first()
	if login_session['user_id'] != item.user_id:
		return "<script>function myFunction() {alert('You are not authorized to delete items in this catalog. Please create your own catalog in order to delete items.');}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		session.delete(item)
		return redirect(url_for('categoryItems', category_id=category_id))
	else:
		return render_template('deleteItem.html', item=item)

@app.route('/catalog/<int:category_id>/create/', methods=['GET', 'POST'])
def itemCreate(category_id):
	if 'username' not in login_session:
		return redirect('/login')
	category = session.query(Category).filter_by(id=category_id).one()
	if login_session['user_id'] != category.user_id:
		return "<script>function myFunction() {alert('You are not authorized to add items. Please create your own catalog in order to add items.');}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		newItem = Items(name=request.form['name'], description=request.form['description'], user_id=category.user_id, category_id=category_id)
		session.add(newItem)
		session.commit()
		flash('New Item, %s, Successfully Created' % (newItem.name))
		return redirect(url_for('categoryItems', category_id=category_id))
	else:
		return render_template('createItem.html', category_id=category_id, category=category)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)