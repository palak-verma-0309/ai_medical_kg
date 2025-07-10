from neo4j import GraphDatabase

# Connect to Neo4j instance
uri = "bolt://localhost:7687"
username = "neo4j"
password = "Akgec@2026"  # ⚠️ Replace this with your actual Neo4j password

driver = GraphDatabase.driver(uri, auth=(username, password))

def fetch_disease_details(symptom):
    with driver.session(database="medical-kg") as session:
        query = """
        MATCH (s:Symptom {name: $symptom})<-[:HAS_SYMPTOM]-(d:Disease)
        OPTIONAL MATCH (d)-[:AFFECTS]->(b:BodyPart)
        OPTIONAL MATCH (d)-[:TREATED_BY]->(t:Treatment)
        RETURN d.name AS disease, collect(DISTINCT b.name) AS body_parts, collect(DISTINCT t.name) AS treatments
        """
        result = session.run(query, symptom=symptom.capitalize())
        return result.data()

def main():
    print("🔍 Medical Knowledge - Symptom to Disease Info")
    symptom = input("Enter a symptom (e.g., Fever, Cough): ").strip()
    
    data = fetch_disease_details(symptom)

    if not data or not data[0]['disease']:
        print("❌ No data found for this symptom.")
        return

    print(f"\n🔎 Results for Symptom: {symptom.capitalize()}")
    for record in data:
        print(f"\n🦠 Disease: {record['disease']}")
        if record["body_parts"]:
            print(f"   🏷 Affects: {', '.join(filter(None, record['body_parts']))}")
        if record["treatments"]:
            print(f"   💊 Treated by: {', '.join(filter(None, record['treatments']))}")

if __name__ == "__main__":
    main()