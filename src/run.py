"""
	This module initiates the server for which the site runs on.

	Example usage:

		$ python run.py

	This will start the site on localhost:5000.
"""


from flask import Flask
from flask import render_template
from flask import request
import requests

app = Flask(__name__)

# TODO: Remove debug in production
# app.config['DEBUG'] = True
# app.config['TEMPLATES_AUTO_RELOAD'] = True

# Bad idea to leave it naked, but temporary solution
key = 'AIzaSyA_r_vCAl0BHHLwdO_jIcbgLglFy2Ppu_I'

# Base API request URL for converting address to coordinate points
geocode_base = 'https://maps.googleapis.com/maps/api/geocode/json?address={0}&key={1}'

# Base API request URL for finding a listing of nearby real estate agencies
places_base = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={0}&{1}&{2}&key={3}'

# Base API request URL for finding distance between two points. Note that this is travelling distance
dist_base = 'https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial&origins={0}&destinations={1}&key={2}'

photo_base = 'https://maps.googleapis.com/maps/api/place/photo?maxwidth=100&photoreference={0}&key={1}'

radius_str = 'radius=16093.4' # Hardcode to km since we're provided constant.
							  # In a real program, we would have an adjustable scale probably

type_str = 'type=real_estate_agency' # Reasonable constant

meters_per_mile = 1609.344 # Hardcode formula for meter to mile conversion
						   # In real application, we might want more precision

@app.route("/", methods=['GET', 'POST'])
def index():
	"""
		Handles requests for the main page. Serves the home page if get request,
		otherwise, make API calls and serve results page.

		Args: None
		Returns: render_template
	"""

	if request.method == 'POST':
		# If POST, process and serve results
		return handle_request(str(request.form['address1']), str(request.form['address2']))
	else:
		# Serve home page
		return render_template('index.html')

def handle_request(address1, address2):
	"""
		Handles the processing and API calls.
		1. Converts addresses to coordinate points
		2. Find two lists of real estate agents, assigning summed distance values
		3. Merge lists, removing duplicates
		4. Sort by summed distance
		5. Pass along sorted list to results page

		Args: 
			address1 (str): A text representation of the first address
			address2 (str): A text representation of the second address
		Returns:
			render_template
	"""

	# Typically we want much stricter error checking here (network failure, contains key, etc)
	# However, this is short term and all addresses are valid due to address picker

	lat_long1_json = requests.get(geocode_base.format(address1.replace(' ', '+'), key)).json()
	lat_long2_json = requests.get(geocode_base.format(address2.replace(' ', '+'), key)).json()

	# Grab lat/long from j son
	lat1 = lat_long1_json['results'][0]['geometry']['location']['lat']
	long1 = lat_long1_json['results'][0]['geometry']['location']['lng']
	lat2 = lat_long2_json['results'][0]['geometry']['location']['lat']
	long2 = lat_long2_json['results'][0]['geometry']['location']['lng']

	# Format into comma-delimited lat,long pairs
	lat_long_str1 = '{0},{1}'.format(lat1, long1)
	lat_long_str2 = '{0},{1}'.format(lat2, long2)

	listings = {}

	# Grab real estate agency listings as json
	listings1 = requests.get(places_base.format(lat_long_str1, radius_str, type_str, key)).json()
	listings2 = requests.get(places_base.format(lat_long_str2, radius_str, type_str, key)).json()

	# Merge sets of agency listings
	for data in listings1['results']:
		listings[data['id']] = data
	for data in listings2['results']:
		listings[data['id']] = data
		
	# Assign summed distance values to each listing
	for listing_key, listing in listings.items():
		lat = listing['geometry']['location']['lat']
		lng = listing['geometry']['location']['lng']
		listing['dist_sum'] = round(calculate_sum_dist(lat, lng, lat1, long1, lat2, long2), 2)
		if 'photos' in listing:
			listing['url'] = get_photo(listing['photos'][0]['photo_reference'])

	# Sort listings
	listing_list = list(listings.values())
	listing_list.sort(key=lambda x: x['dist_sum'])

	# Send to results page
	return render_template('results.html', places=listing_list)

def get_photo(ref):
	return photo_base.format(ref, key)
	print(photo_res)


def calculate_sum_dist(targ_lat, targ_long, lat1, long1, lat2, long2):
	"""
		Using origin and two addresses coordinates, calculates total distance
		using Google's Distance Matrix API.
		Note that this is driving distance and not absolute/manhattan distance.
		Also note that ideally, we would want coordinate objects and not just
			naked pairs. But for small scope project, this is OK.

		Args:
			targ_lat (float): Origin lat
			targ_long (float): Origin long
			lat1 (float): latitude of address 1
			long1 (float): longitude of address 1
			lat2 (float): latitude of address 2
			long2 (float): longitude of address 2

		Returns:
			float

	"""

	# Formats coordinates into comma-delimited lat, long pairs
	targ_lat_long_str = '{0},{1}'.format(targ_lat, targ_long)
	lat_long1_str = '{0},{1}'.format(lat1, long1)
	lat_long2_str = '{0},{1}'.format(lat2, long2)

	# Grab distance matrixes as JSON via Google API
	matrix1 = requests.get(dist_base.format(targ_lat_long_str, lat_long1_str, key)).json()
	matrix2 = requests.get(dist_base.format(targ_lat_long_str, lat_long2_str, key)).json()

	# Grab numerical distance values
	dist1 = matrix1['rows'][0]['elements'][0]['distance']['value']
	dist2 = matrix2['rows'][0]['elements'][0]['distance']['value']

	# Sum values
	dist_sum_m = dist1 + dist2

	# Convert to imperial (miles)
	# Note: Imprecise calculations, but we round to two digits regardless.
	return dist_sum_m / meters_per_mile

if __name__ == "__main__":
	app.run()
	#app.run(host='0.0.0.0', port=5000)