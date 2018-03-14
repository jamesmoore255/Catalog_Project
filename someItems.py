from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import User, Base, Category, Items

engine = create_engine('sqlite:///catalog.db')

Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

#Dummy user
User1 = User(name="Toby Moore", email="jimbob@email.com")
session.add(User1)
session.commit()

#Category and a few items
category1 = Category(user_id=1, name="Countries")

session.add(category1)

item1 = Items(user_id=1, name="Australia", description="A large continent in the oceania. It's a top notch country.", category=category1)

session.add(item1)
session.commit()

item2 = Items(user_id=1, name="Colombia", description="A beautiful country based located in the top of South America, connecting to Panama. It too, is a top notch country.", category=category1)

session.add(item2)
session.commit()

item3 = Items(user_id=1, name="The United States of America", description="A large country in North America, which has the most questionable president possibly in history leading it at this point in time. Apart from the President, this too is a top notch country.", category=category1)

session.add(item3)
session.commit()

print "Added your stuff!"