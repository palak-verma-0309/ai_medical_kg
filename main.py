from neo4j import GraphDatabase

# Connect to Neo4j instance
uri = "bolt://localhost:7687"
username = "neo4j"
password = "Akgec@2026"  # ⚠️ Replace this with your actual Neo4j password

driver = GraphDatabase.driver(uri, auth=(username, password))

def fetch_details(symptom):
    with driver.session(database="medical-kg") as session:
        query = """
        MATCH (s:Symptom {name: $symptom})<-[:HAS_SYMPTOM]-(d:Disease)
        OPTIONAL MATCH (d)-[:AFFECTS]->(b:BodyPart)
        OPTIONAL MATCH (d)-[:TREATED_BY]->(t:Treatment)
        OPTIONAL MATCH (c:Cause)-[:CAUSES]->(d)
        OPTIONAL MATCH (s)-[:RELIEVED_BY]->(m:Medication)
        RETURN d.name AS disease, 
               collect(DISTINCT b.name) AS body_parts, 
               collect(DISTINCT t.name) AS treatments,
               collect(DISTINCT c.name) AS causes,
               collect(DISTINCT m.name) AS medications
        """
        result = session.run(query, symptom=symptom.capitalize())
        return result.data()

def main():
    print("🔍 Medical Knowledge Assistant")
    symptom = input("Enter a symptom (e.g., Fever, Cough, Chest Pain): ").strip()

    data = fetch_details(symptom)

    if not data or not data[0]['disease']:
        print("❌ No disease found for this symptom.")
        return

    print(f"\n🔎 Details for Symptom: {symptom.capitalize()}")
    for record in data:
        print(f"\n🦠 Disease: {record['disease']}")
        if record["body_parts"]:
            print(f"   🏷 Affects: {', '.join(filter(None, record['body_parts']))}")
        if record["treatments"]:
            print(f"   💊 Treated by: {', '.join(filter(None, record['treatments']))}")
        if record["causes"]:
            print(f"   ⚠️ Caused by: {', '.join(filter(None, record['causes']))}")
        if record["medications"]:
            print(f"   💉 Medications for symptom: {', '.join(filter(None, record['medications']))}")

if __name__ == "__main__":
    main()