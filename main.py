import urllib
import requests
import os
import numpy as np
import pandas as pd
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv
from flask import Flask, redirect, request, render_template

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_API_KEY')
session = {}

CLIENT_ID = os.getenv('SPOTIFY_API_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_API_CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')

LOGOUT_URL = 'https://accounts.spotify.com/logout'
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL =  'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('home_login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    scope = 'user-read-private user-read-email user-top-read'

    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True
    }

    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return "ERROR"

    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
    
        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()

        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() +  token_info['expires_in']

        return redirect('/results')

@app.route('/results', methods=['GET', 'POST'])
def get_results():
    # Redirect to /login endpoint if there is no access token in the session dictionary
    if 'access_token' not in session:
        return redirect('/login')

    # Check if the access token is expired. If true, redirect to /refresh-token endpoint to get a new token
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')
    
    # Get the selected filter (Monthly, Semi-annual (default), All-time)
    active_button = request.form.get('active_button', 'Semi-annual')
    
    # Create a header
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    # Map the values to what the API resource accepts
    if active_button == "Monthly":
        time_range = "short_term"
    elif active_button == "Semi-annual":
        time_range = "medium_term"
    else:
        time_range = "long_term"

    # Get the user's top 10 tracks
    response_top_tracks = requests.get(f"{API_BASE_URL}" + 'me/top/tracks' + f'?time_range={time_range}&limit=10', headers=headers)
    top_tracks = response_top_tracks.json()

    # Get the user's top 10 artists
    response_top_artists = requests.get(f"{API_BASE_URL}" + 'me/top/artists' + f'?time_range={time_range}&limit=10', headers=headers)
    top_artists = response_top_artists.json()

    # Create a list tuple of tracks and their corresponding artist(s)
    top_tracks_and_artists = []
    for track_info in top_tracks['items']:
        artists = ', '.join([artist_info['name'] for artist_info in track_info['artists']])
        top_tracks_and_artists.append((artists, track_info['name'], track_info['album']['images'][2]['url'], track_info['id']))

    top_artist_genres = []
    list_of_top_artists = []
    for artist_info in top_artists['items']:
        list_of_top_artists.append((artist_info['name'], artist_info['images'][2]['url'], artist_info['popularity']))
        top_artist_genres.extend(artist_info['genres'])
    
    sorted_list_of_top_artist_by_popularity =  sorted(list_of_top_artists, key=lambda x: x[2])
    most_popular_artist = sorted_list_of_top_artist_by_popularity[-1][0] # Get the name 
    least_popular_artist = sorted_list_of_top_artist_by_popularity[0][0] # Get the name
    popularity_range_high = sorted_list_of_top_artist_by_popularity[-1][-1]
    popularity_range_low = sorted_list_of_top_artist_by_popularity[0][-1]
    average_artist_popularity = np.mean([artist_info[-1] for artist_info in list_of_top_artists])
    artist_popularity_bar_graph_insight_data = {
        'most_popular_artist': most_popular_artist,
        'least_popular_artist': least_popular_artist,
        'popularity_range_high': popularity_range_high,
        'popularity_range_low': popularity_range_low,
        'average_artist_popularity': average_artist_popularity
    }
    

    genre_count_dict = Counter(top_artist_genres)
    top_genres = list(genre_count_dict.keys())[:10]

    top_artists_names = [artist_info[0] for artist_info in list_of_top_artists]
    top_artists_popularity = [artist_info[-1] for artist_info in list_of_top_artists]
    
    response_top_10_tracks_short_term = requests.get(f"{API_BASE_URL}" + 'me/top/tracks' + f'?time_range=short_term&limit=10', headers=headers).json()
    response_top_10_tracks_medium_term = requests.get(f"{API_BASE_URL}" + 'me/top/tracks' + f'?time_range=medium_term&limit=10', headers=headers).json()
    response_top_10_tracks_long_term = requests.get(f"{API_BASE_URL}" + 'me/top/tracks' + f'?time_range=long_term&limit=10', headers=headers).json()

    top_10_tracks_id_short_term = '%2C'.join([track_info['id'] for track_info in response_top_10_tracks_short_term['items']])
    top_10_tracks_id_medium_term = '%2C'.join([track_info['id'] for track_info in response_top_10_tracks_medium_term['items']])
    top_10_tracks_id_long_term = '%2C'.join([track_info['id'] for track_info in response_top_10_tracks_long_term['items']])

    response_audio_feat_top_10_short_term = requests.get(f"{API_BASE_URL}" + f'audio-features?ids={top_10_tracks_id_short_term}', headers=headers).json()
    response_audio_feat_top_10_medium_term = requests.get(f"{API_BASE_URL}" + f'audio-features?ids={top_10_tracks_id_medium_term}', headers=headers).json()
    response_audio_feat_top_10_long_term = requests.get(f"{API_BASE_URL}" + f'audio-features?ids={top_10_tracks_id_long_term}', headers=headers).json()

    audio_features = ['acousticness', 'danceability', 'energy', 'instrumentalness', 
                'liveness', 'loudness', 'speechiness', 'valence', 'tempo', 'duration_ms']

    audio_features_short_term = {attr: [] for attr in audio_features}
    audio_features_medium_term = {attr: [] for attr in audio_features}
    audio_features_long_term = {attr: [] for attr in audio_features}

    for audio_feature in audio_features:
        for track_audio_features in response_audio_feat_top_10_short_term['audio_features']:
            audio_features_short_term[audio_feature].append(track_audio_features[audio_feature])

        for track_audio_features in response_audio_feat_top_10_medium_term['audio_features']:
            audio_features_medium_term[audio_feature].append(track_audio_features[audio_feature])
        
        for track_audio_features in response_audio_feat_top_10_long_term['audio_features']:
            audio_features_long_term[audio_feature].append(track_audio_features[audio_feature])
    

    mean_audio_features_short_term = [sum(min_max_normalize(v))/10 for _, v in audio_features_short_term.items()]
    mean_audio_features_medium_term = [sum(min_max_normalize(v))/10 for _, v in audio_features_medium_term.items()]
    mean_audio_features_long_term = [sum(min_max_normalize(v))/10 for _, v in audio_features_long_term.items()]
    
    corr_matrix = pd.DataFrame({
        'short_term' : mean_audio_features_short_term,
        'medium_term' : mean_audio_features_medium_term,
        'long_term' : mean_audio_features_long_term
    }).transpose().corr('pearson')

    corr_matrix.columns = audio_features

    pairs = []
    columns = corr_matrix.columns
    for i in range(len(columns)):
        for j in range(i+1, len(columns)):
            if (corr_matrix.iloc[i, j] >= 0.90 or corr_matrix.iloc[i, j] <= -0.90) and abs(corr_matrix.iloc[i, j]) < 1.00:
                pairs.append((columns[i], columns[j], 'negative' if corr_matrix.iloc[i, j] < 0 else 'positive'))

    return render_template('results.html', top_artists=list_of_top_artists, top_tracks_and_artists=top_tracks_and_artists, top_genres=top_genres, active_button=active_button, top_artists_names=top_artists_names, top_artists_popularity=top_artists_popularity, mean_audio_features_short_term=mean_audio_features_short_term, mean_audio_features_medium_term=mean_audio_features_medium_term, mean_audio_features_long_term=mean_audio_features_long_term, audio_features=audio_features, correlation_insight_data=pairs, artist_popularity_bar_graph_insight_data=artist_popularity_bar_graph_insight_data)

@app.route('/refresh-token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')

    if datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type' : 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)
        new_token_info = response.json()
        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

        return redirect('/results')

@app.route('/logout', methods=['GET', 'POST'])
def logout_user():
    session = {}
    return redirect(LOGOUT_URL)


def min_max_normalize(values):
    min_val = min(values)
    max_val = max(values)
    normalized_values = [(v - min_val) / (max_val - min_val) for v in values]
    return normalized_values

if __name__ == '__main__':
    app.run()