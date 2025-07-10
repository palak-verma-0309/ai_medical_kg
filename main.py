from neo4j import GraphDatabase

# Connect to Neo4j instance
uri = "bolt://localhost:7687"
username = "neo4j"
password = "Akgec@2026"  # ⚠️ Replace this with your actual Neo4j password

driver = GraphDatabase.driver(uri, auth=(username, password))

def fetch_diseases_and_bodyparts(symptom):
    with driver.session(database="medical-kg") as session:
        query = """
        MATCH (s:Symptom {name: $symptom})<-[:HAS_SYMPTOM]-(d:Disease)-[:AFFECTS]->(b:BodyPart)
        RETURN d.name AS disease, b.name AS body_part
        """
        result = session.run(query, symptom=symptom.capitalize())
        data = result.data()
        return data

def main():
    print("🔍 Medical Knowledge - Symptom to Disease Info")
    symptom = input("Enter a symptom (e.g., Fever, Cough): ").strip()
    
    results = fetch_diseases_and_bodyparts(symptom)

    if not results:
        print("❌ No data found for this symptom.")
        return

    print(f"\n🔎 Results for Symptom: {symptom.capitalize()}")
    for record in results:
        print(f"🦠 Disease: {record['disease']} → 🏷 Affects: {record['body_part']}")

if __name__ == "__main__":
    main()