from flask import Flask
from neo4j import GraphDatabase
from flask import request, jsonify

app = Flask(__name__)

uri = "neo4j+s://d35e2ed0.databases.neo4j.io"
username = "neo4j"
password = "_MKRiLUfSLLLnJ6JYLdLkptY8dsr281rqMzgY5GlL2A"

driver = GraphDatabase.driver(uri, auth=(username, password))

def get_db():
    return driver.session()

@app.route('/')
def hello():
    return 'Connected to Neo4j. Flask application is running!'
    
#1.Insert the new characters information.
@app.route('/chars', methods=['POST'])
def add_character():
    data = request.json
    try:
        # Defined a separate function for running the transaction
        def create_character(tx, character_data):
            return tx.run("CREATE (c:Characters {name: $name, height: $height, mass: $mass, "
                          "skin_color: $skin_color, hair_color: $hair_color, eye_color: $eye_color, "
                          "birth_year: $birth_year, gender: $gender, homeworld: $homeworld, species: $species}) "
                          "RETURN c.name AS name", **character_data).single().get("name")

        with get_db() as session:
            # Using the defined function to run the transaction and immediately capture the result
            created_character_name = session.write_transaction(create_character, data)
            
            # If the character was successfully created, `created_character_name` should not be None
            if created_character_name:
                return jsonify({
                    "status": "success",
                    "message": "Character successfully created.",
                 }), 201
            else:
                # This case handles situations where the transaction didn't return a name, 
                # which should theoretically not occur if the CREATE query was successful
                return jsonify({"status": "Error", "message": "Character could not be created"}), 500
    except Exception as e:
        # Catch-all for any other exceptions that may occur, including potential issues with the database connection
        return jsonify({"status": "Error", "message": str(e)}), 500



# 2. Update the characters information using name. 
# (By update only name, hair_colors, height and birth_year).
@app.route('/chars/<string:fname>', methods=['PATCH'])
def update_character(fname):
    data = request.json  # Get the data sent in the request body
    try:
        with get_db() as session:
            # Dynamically construct parts of the Cypher query based on the provided JSON
            updates = []
            params = {}
            if 'name' in data:
                updates.append("c.name = $new_name")
                params['new_name'] = data['name']
            if 'hair_color' in data:
                updates.append("c.hair_color = $hair_color")
                params['hair_color'] = data['hair_color']
            if 'height' in data:
                updates.append("c.height = $height")
                params['height'] = data['height']
            if 'birth_year' in data:
                updates.append("c.birth_year = $birth_year")
                params['birth_year'] = data['birth_year']

            if not updates:
                return jsonify({"status": "Error", "message": "No valid fields provided for update"}), 400

            # Combine all update parts into a single query string
            update_query = ", ".join(updates)
            query = (
                f"MATCH (c:Characters) WHERE c.name = $fname "
                f"SET {update_query} "
                "RETURN c.name AS updated_name"
            )
            # Run the transaction
            result = session.run(query, fname=fname, **params)
            updated_name = result.single()

            if updated_name:
                return jsonify({"status": "Success", "message": f"Character updated to {updated_name['updated_name']}"}), 200
            else:
                return jsonify({"status": "Error", "message": "Character not found or no update performed."}), 404
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500


# 3. Delete the character information using name.
@app.route('/chars/<string:fname>', methods=['DELETE'])
def delete_character(fname):
    try:
        with get_db() as session:
            # Attempt to delete the character node with the given name
            result = session.write_transaction(lambda tx:
                tx.run("MATCH (c:Characters {name: $name}) "
                       "DELETE c "
                       "RETURN COUNT(c) AS count", name=fname).single().get("count"))
            
            # Check if a node was actually deleted
            if result and result > 0:
                return jsonify({"status": "Success", "message": f"Character '{fname}' deleted"}), 200
            else:
                return jsonify({"status": "Error", "message": f"Character '{fname}' not found"}), 404
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500


#4. Retrieve all the characters in database.
@app.route('/chars', methods=['GET'])
def get_characters():
    try:
        with get_db() as session:
            # Using a simpler MATCH query with a LIMIT
            result = session.read_transaction(lambda tx: 
                # tx.run("MATCH (n:Characters) RETURN n LIMIT 25").data())
                tx.run("MATCH (n:Characters) RETURN n").data())
            characters = [{
                "name": record["n"]["name"], 
                "height": record["n"]["height"],
                "mass": record["n"]["mass"],
                "skin_color": record["n"].get("skin_color", "N/A"),  # Using .get() for optional fields
                "hair_color": record["n"].get("hair_color", "N/A"),
                "eye_color": record["n"].get("eye_color", "N/A"),
                "birth_year": record["n"].get("birth_year", "N/A"),
                "gender": record["n"]["gender"],
                "homeworld": record["n"].get("homeworld", "N/A"),
                "species": record["n"].get("species", "N/A")
            } for record in result]
            
            return jsonify(characters), 200
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500


# 5. Display the characters’ details using name.
@app.route('/chars/<string:fname>', methods=['GET'])
def get_character_by_name(fname):
    try:
        with get_db() as session:
            # Query the database for a character by name
            result = session.read_transaction(lambda tx:
                tx.run("MATCH (n:Characters) WHERE n.name = $name RETURN n", name=fname).single())
            if result:
                character = result["n"]
                character_details = {
                    "name": character["name"],
                    "height": character.get("height", "N/A"),
                    "mass": character.get("mass", "N/A"),
                    "skin_color": character.get("skin_color", "N/A"),
                    "hair_color": character.get("hair_color", "N/A"),
                    "eye_color": character.get("eye_color", "N/A"),
                    "birth_year": character.get("birth_year", "N/A"),
                    "gender": character["gender"],
                    "homeworld": character.get("homeworld", "N/A"),
                    "species": character.get("species", "N/A")
                }
                return jsonify(character_details), 200
            else:
                return jsonify({"message": f"Character with name {fname} not found"}), 404
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500



