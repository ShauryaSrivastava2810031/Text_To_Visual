import sqlite3
import pandas as pd

# Load the dataset
df = pd.read_csv('C:/Users\shaurya.s\OneDrive - Comviva Technologies LTD\Desktop\T2S/retail_sales_dataset.csv')

# Connect to SQLite database (creates a new database file if it doesn't exist)
conn = sqlite3.connect('retails.db')

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

# Drop the EMPLOYEE table if it exists (this will avoid issues with re-running the script)
cursor.execute("DROP TABLE IF EXISTS retails_sales;")


# Define the table creation SQL based on the dataset structure
create_table_query = """
CREATE TABLE IF NOT EXISTS retails_sales (
    Transaction_ID INT PRIMARY KEY,
    Date DATE,
    Customer_ID VARCHAR(10),
    Gender VARCHAR(10),
    Age INT,
    Product_Category VARCHAR(50),
    Quantity INT,
    Price_per_Unit DECIMAL(10, 2),
    Total_Amount DECIMAL(10, 2)
);
"""

# Execute the table creation query
cursor.execute(create_table_query)

# Create an insertion query
insert_query = """
INSERT INTO retails_sales (
    Transaction_ID, Date, Customer_ID, Gender, Age, Product_category, Quantity, Price_per_Unit, Total_Amount
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

# Insert data in batches
batch_size = 1000  # Adjust the batch size as needed
for i in range(0, len(df), batch_size):
    batch_data = df.iloc[i:i + batch_size].values.tolist()
    cursor.executemany(insert_query, batch_data)
    print(f"Inserted rows {i} to {i + batch_size}")

# Commit changes
conn.commit()

# Display all records
print("The inserted records are:")
cursor.execute("SELECT * FROM retails_sales LIMIT 1;")
for row in cursor.fetchall():
    print(row)
cursor.execute("SELECT * FROM retails_sales ORDER BY Transaction_ID DESC LIMIT 1;")
for row in cursor.fetchall():
    print(row)
# Close the connection
conn.close()

print("All data successfully inserted into the SQLite database.")