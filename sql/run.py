"""Run a .sql file of semicolon-separated statements against the `main` Snowflake connection, printing results."""
import sys

import snowflake.connector

with snowflake.connector.connect(connection_name="main") as conn:
    for cur in conn.execute_string(open(sys.argv[1]).read()):
        print(cur.query.strip().splitlines()[0][:80], "->", cur.fetchall()[:3])
