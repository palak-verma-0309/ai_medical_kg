from neo4j import GraphDatabase

# Connect to Neo4j instance
uri = "bolt://localhost:7687"
username = "neo4j"
password = "Akgec@2026"  # ⚠️ Replace this with your actual Neo4j password

driver = GraphDatabase.driver(uri, auth=(username, password))

def find_disease_from_symptom(symptom):
    query = """
    MATCH (s:Symptom {name: $symptom})<-[:HAS_SYMPTOM]-(d:Disease)
    RETURN d.name AS disease
    """
    with driver.session(database="medical-kg") as session:
        result = session.run(query, symptom=symptom.capitalize())
        diseases = [record["disease"] for record in result]
        return diseases

def main():
    print("🔍 Medical Knowledge Assistant")
    user_input = input("Enter a symptom (e.g., Fever, Cough, Chest Pain): ")
    diseases = find_disease_from_symptom(user_input)
    
    if diseases:
        print("🦠 Possible diseases for symptom '{}':".format(user_input))
        for disease in diseases:
            print(" -", disease)
    else:
        print("❌ No disease found for this symptom.")

if __name__ == "__main__":
    main()
