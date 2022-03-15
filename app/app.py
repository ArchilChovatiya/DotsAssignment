from flask import Flask, request, jsonify
import uuid
import requests
from opensearchpy import OpenSearch, RequestsHttpConnection

openSearchEndpoint = "https://search-dots-game-players-oci6hshlbaa6bwqaxarsdhkas4.us-east-1.es.amazonaws.com/"
awsRegion = 'us-east-1'
service = 'es'
awsauth = ('master', 'Master@123')

search = OpenSearch(
    hosts=openSearchEndpoint,
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

index_body = {
    'settings': {
        'index': {
            'number_of_shards': 4
        }
    }
}
# response = search.indices.create('player_details', body=index_body)
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


class BadRequest(Exception): pass
class PlayerNotFound(Exception): pass


@app.route('/api/v1/player', methods=['POST'])
def create_new_player():
    try:
        username = request.json["username"]
        player_id = username + "_" + str(uuid.uuid1())[:8]
        if username is None or username == "":
            raise BadRequest
        response = {
            "username": username,
            "player_id": player_id
        }
        search.index(
            index='player_details',
            body={
                'player_id': response["player_id"],
                'username': response["username"],
                'xp': 0,
                'gold': 0
            },
            refresh=True
        )
        return jsonify(response)
    except BadRequest:
        return {"error_message": "Invalid request body"}, 400
    except Exception:
        return {"error_message": "Some kind of unspecified error has occurred!"}, 500


@app.route('/api/player/<player_id>', methods=['GET'])
def get_player(player_id):
    try:
        if player_id is None or player_id == "":
            raise BadRequest
        query = openSearchEndpoint + 'player_details/_search'
        data={
            "query": {
                "match": {
                    "player_id": {
                        "query": str(player_id)
                     }
                }
            }
        }
        response = requests.get(query, auth=awsauth,json=data, headers={"Content-Type": "application/json"}).json()

        data = response["hits"]["hits"]
        if len(data) == 0:
            raise PlayerNotFound
        return jsonify(data[0]['_source'])
    except PlayerNotFound:
        return {"error_message": "Player not found"}, 404
    except BadRequest:
        return {"error_message": "Invalid request body"}, 400
    except Exception:
        return {"error_message": "Some kind of unspecified error has occurred!"}, 500


@app.route('/api/player/<player_id>', methods=['PUT'])
def update_player(player_id):
    try:
        data = request.json
        if player_id is None or player_id == "":
            raise BadRequest
        query = openSearchEndpoint + 'player_details/_search'
        data2 = {
            "query": {
                "match": {
                    "player_id": {
                        "query": str(player_id)
                    }
                }
            }
        }
        response = requests.get(query, auth=awsauth, json=data2, headers={"Content-Type": "application/json"}).json()
        if len(response["hits"]["hits"]) == 0:
            raise PlayerNotFound
        doc_id = response["hits"]["hits"][0]["_id"]
        url = openSearchEndpoint + 'player_details/_update/' + str(doc_id)
        print(data)
        data["player_id"] = player_id
        document = {"doc": data}
        requests.post(url, auth=awsauth, json=document, headers={"Content-Type": "application/json"}).json()
        return jsonify(data)
    except BadRequest:
        return {"error_message": "Invalid request body"}, 400
    except PlayerNotFound:
        return {"error_message": "Player not found"}, 404



@app.route('/api/leaderboards', methods=['GET'])
def get_leaderboard():
    try:
        sortby = request.args.get('sortby')
        size = request.args.get('size')
        query = openSearchEndpoint + 'player_details/_search'
        data = {
                "from": 0,
                "size": size,
                "sort":
                     {
                         sortby: {
                                    "order": "desc"
                               }
                    }
                }
        records=[]
        response = requests.get(query,json=data, auth=awsauth, headers={"Content-Type": "application/json"}).json()
        for rec in response['hits']['hits']:
            records.append(rec['_source'])
        return jsonify(records)
        if size < 0 or (sortby != 'xp' and sortby != 'gold'):
            raise BadRequest
    except BadRequest:
        return {"error_message": "Invalid request body"}, 400
    except PlayerNotFound:
        return {"error_message": "Player not found"}, 404
    except Exception:
        return {"error_message": "Some kind of unspecified error has occurred!"}, 500


@app.errorhandler(404)
def page_not_found(e):
    return {"error_message": "Page not found"}, 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
