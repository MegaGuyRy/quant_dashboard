def insert_predictions_to_db(conn, df, horizon, strategy):
    cur = conn.cursor()
    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO model_predictions (ticker, prediction_date, model_output, horizon, strategy)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            row['Symbol'],
            row['Date'],
            row['Predicted Return'],
            horizon,
            strategy
        ))
    conn.commit()
    cur.close()
