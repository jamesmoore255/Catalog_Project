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

# Connect to Database and create database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

#JSON APIs to view Catalog information.
@app.route('/catalog/JSON')

@app.route('/catalog/<int:category_id>/items/JSON')

@app.route('/catalog/<int:category_id>/items/<int:items_id>/JSON')

#login page
@app.route('/login')
def login():
	return render_template('login.html')

# Catalog main page with list of categories and latest items

@app.route('/')
@app.route('/catalog/')
def catalogHome():
	categories = session.query(Category).order_by(Category.name.desc())
	items = session.query(Items).order_by(Items.id.desc())
	# if 'username' not in login_session:
	# 	return render_template('public_category.html', categories=categories)
	# else:   REMEMBER AFTER UNCOMMENTING INDENT THE NEXT LINE!
	return render_template('catalog.html', categories=categories, items=items)

@app.route('/catalog/<int:category_id>/edit/', methods=['GET', 'POST'])
def categoryEdit(category_id):
	categoryEdit = session.query(Category).filter_by(id=category_id).one()
	# if 'username' not in login_session:
 #        return redirect('/login')
 	# if categoryEdit.user_id != login_session['user_id']:
 	# 	return "<script>function myFunction() {alert('You are not authorized to edit this category. Please create your own category in order to edit.');}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		categoryEdit.name = request.form['name']
		flash('Category Successfully Edited %s' % categoryEdit.name)
		return redirect(url_for('catalogHome'))
	else:
		return render_template('editCategory.html', category=categoryEdit)


@app.route('/catalog/<int:category_id>/delete/', methods=['GET', 'POST'])
def categoryDelete(category_id):
	categoryDelete = session.query(Category).filter_by(id=category_id).one()
	# if 'username' not in login_session:
 #        return redirect('/login')
 	# if categoryDelete.user_id != login_session['user_id']:
	 # 	return "<script>function myFunction() {alert('You are not authorized to delete this restaurant. Please create your own restaurant in order to delete.');}</script><body onload='myFunction()''>"
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
	# if 'username' not in login_session:
	# 	return redirect('/login')
	if request.method == 'POST':
		# Add this in once login is set up ", user_id=login_session['user_id']"
		newCategory = Category(name=request.form['name'])
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
	# creator = getUserInfo(category.user_id)
	items = session.query(Items).filter_by(category_id=category.id).all()
	# if 'username' not in login_session or creator.id != login_session['user_id']:
	return render_template('categoryItem.html', items=items, category=category, categories=categories)

@app.route('/catalog/<int:category_id>/<int:item_id>/item')
def specificItem(item_id, category_id):
	item = session.query(Items).filter_by(category_id=category_id, id=item_id).first()
	# creator = getUserInfo(item.user_id)
	return render_template('specificItem.html', item=item)

@app.route('/catalog/<int:category_id>/<int:item_id>/edit/', methods=['GET', 'POST'])
def itemEdit(category_id, item_id):
	# if 'username' not in login_session:
 #        return redirect('/login')
	item = session.query(Items).filter_by(category_id=category_id, id=item_id).first()
	# if login_session['user_id'] != restaurant.user_id:
 #        return "<script>function myFunction() {alert('You are not authorized to edit menu items to this restaurant. Please create your own restaurant in order to edit items.');}</script><body onload='myFunction()''>"
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
	item = session.query(Items).filter_by(category_id=category_id, id=item_id).first()
	if request.method == 'POST':
		session.delete(item)
		return redirect(url_for('categoryItems', category_id=category_id))
	else:
		return render_template('deleteItem.html', item=item)

@app.route('/catalog/<int:category_id>/create/', methods=['GET', 'POST'])
def itemCreate(category_id):
	# if 'username' not in login_session:
 #        return redirect('/login')
	category = session.query(Category).filter_by(id=category_id).one()
	# if login_session['user_id'] != category.user_id:
 #        return "<script>function myFunction() {alert('You are not authorized to add menu items to this restaurant. Please create your own restaurant in order to add items.');}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		# user_id=category.user_id    ===  add this into the brackets at the end after user_id is activated
		newItem = Items(name=request.form['name'], description=request.form['description'], category_id=category_id)
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