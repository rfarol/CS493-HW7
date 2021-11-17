# boostrap cdn taken from: https://cdn.jsdelivr.net/npm/bootswatch@4.5.2/dist/cosmo/bootstrap.min.css
# code implentation taken from: https://developers.google.com/identity/protocols/oauth2/web-server
# skeleton code taken from HTTP/REST Implentation 

# creation of location header was taken from: https://stackoverflow.com/questions/22669447/how-to-return-a-relative-uri-location-header-with-flask
# convert JSON object to HTML table was taken from: https://stackoverflow.com/questions/49390075/how-do-i-convert-python-json-into-a-html-table-in-flask-server/49391508
from google.cloud import datastore
import flask
from flask import Flask, request, render_template
import json
import requests
import uuid
import random
import constants

CLIENT_ID = '76687485492-gfmu157sho0gop9vdg2ff2kr5vlpt42j.apps.googleusercontent.com'
CLIENT_SECRET = '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'
SCOPE = 'https://www.googleapis.com/auth/userinfo.profile'
REDIRECT_URI = 'https://cs493hw6-farolr.wl.r.appspot.com/oauth'
STATE = "State" + str(random.randint(1, 9999999)) # randomize state 

app = flask.Flask(__name__)
app.secret_key = str(uuid.uuid4())
app.debug = True
client = datastore.Client()

@app.route('/')
def index():
    return render_template('welcome.html')

@app.route('/boats', methods=['POST','GET'])
def boast_get_post():
    # post request 
    if request.method == 'POST':
        content = request.get_json()
        if content is None:
            # makes sure client sends supported MIME type
            return ('Please submit a JSON object', 415)
        else:    
            # search for all boats to find name constraint. 403 request 
            query = client.query(kind=constants.boats)
            list_boats = query.fetch()
            for boats in list_boats:
                if boats['name'] == content['name']:
                    return ("This boat already exists. Please add another one", 403)

            # check for invalid input types . 400 requests 
            if 'name' not in content.keys():
                return ('Please enter name', 400)
            if 'type' not in content.keys():
                return ('Please enter type', 400)
            if 'length' not in content.keys():
                return ('Please enter length', 400)

            new_boat = datastore.entity.Entity(key=client.key(constants.boats))
            new_boat.update({"name": content["name"], "type": content["type"],
            "length": content["length"]})
            client.put(new_boat)
            boat = client.get(key=new_boat.key)
            boat['id'] = new_boat.key.id
            boat['self'] = request.url + "/" + str(new_boat.key.id) # add self URL
            return (boat, 201) # boat is returned as a JSON object. 201 request code 
        
    # get request for all boats 
    elif request.method == 'GET':
        query = client.query(kind=constants.boats)
        results = list(query.fetch())
        for e in results:
            e["id"] = e.key.id
            e["self"] = request.url + "/" + str(e.key.id) # add self URL 
            output = {"boat": results}
        return json.dumps(output)
    
    else:
        # checks if client makes unsupported request to server.
        return ('Method not recognized', 415)
    
  


@app.route('/boats/<id>', methods=['DELETE'])
def boats_delete(id):
    # delete request to delete a specific boat 
    if request.method == 'DELETE':
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        # confirms ID before deleting. 404 request if ID doesn't exist
    else:
        return ('Method not recognized', 406)


@app.route('/userinfo')
def userinfo():
    # store date into datastore
    new_state = datastore.Entity(client.key("states"))
    new_state.update({'state': STATE})
    client.put(new_state)
    if 'credentials' not in flask.session:
        return flask.redirect(flask.url_for('oauth'))
    credentials = json.loads(flask.session['credentials'])
    if credentials['expires_in'] <= 0:
        return flask.redirect(flask.url_for('oauth'))
    else:
        headers = {'Authorization': 'Bearer {}'.format(credentials['access_token']), 'State': '{}'.format(STATE)}
        request_uri = 'https://people.googleapis.com/v1/people/me?personFields=names'
        request = requests.get(request_uri, headers=headers)
        name = json.loads(request.text)
        name = name['names']
        last_name = name[0]['familyName']
        first_name = name[0]['givenName']
        return render_template('userinfo.html', last_name=last_name, first_name=first_name, state=STATE)

@app.route('/oauth')
def oauth():
    if 'code' not in flask.request.args:
        authorization_uri = ('https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={}&redirect_uri={}&scope={}&state={}').format(CLIENT_ID, REDIRECT_URI, SCOPE, STATE)
        return flask.redirect(authorization_uri)
    else:
        authorization_code = flask.request.args.get('code')
        data = {'code': authorization_code, 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'redirect_uri': REDIRECT_URI, 'grant_type': 'authorization_code', 'State': STATE}
        # fetch all the states stored within the datastore 
        query = client.query(kind="states")
        results = list(query.fetch())
        for i in results:
           if i['state'] == STATE:
            request = requests.post('https://oauth2.googleapis.com/token', data=data)
            flask.session['credentials'] = request.text
            return flask.redirect(flask.url_for('userinfo'))
        else:
            return ("State is invalid")

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)