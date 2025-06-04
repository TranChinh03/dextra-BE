from email.mime.image import MIMEImage

def build_stats_email_html(stats: list, date_from: str, date_to: str) -> str:
    # Table content
    table_rows = ""
    for row in stats:
        table_rows += f"""
        <tr>
            <td>{row['date']}</td>
            <td>{row['numberOfBicycle']}</td>
            <td>{row['numberOfMotorcycle']}</td>
            <td>{row['numberOfCar']}</td>
            <td>{row['numberOfVan']}</td>
            <td>{row['numberOfTruck']}</td>
            <td>{row['numberOfBus']}</td>
            <td>{row['numberOfFireTruck']}</td>
            <td>{row['numberOfContainer']}</td>
        </tr>
        """

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; color: #333; }}
            h2 {{ color: #4CAF50; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
            th {{ background-color: #f2f2f2; color: #333; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            tr:hover {{ background-color: #f1f1f1; }}
        </style>
    </head>
    <body>
        <h2>🚦 Traffic Detection Statistics</h2>
        <p><strong>Date range:</strong> {date_from} to {date_to}</p>
        <img src="cid:stats_chart" alt="Traffic Statistics Chart" style="width:100%; max-width:800px; margin: 20px 0;" />
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Bicycles</th>
                    <th>Motorcycles</th>
                    <th>Cars</th>
                    <th>Vans</th>
                    <th>Trucks</th>
                    <th>Buses</th>
                    <th>Fire Trucks</th>
                    <th>Containers</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        <p style="margin-top: 30px;">🚗 Stay safe and thank you for using our traffic monitoring service!</p>
    </body>
    </html>
    """
    return html

def generate_chart_image(stats: list) -> MIMEImage:
    import matplotlib.pyplot as plt
    import numpy as np
    from io import BytesIO
    from email.mime.image import MIMEImage

    dates = [s["date"] for s in stats]
    vehicle_types = {
        "Bicycle": [s["numberOfBicycle"] for s in stats],
        "Motorcycle": [s["numberOfMotorcycle"] for s in stats],
        "Car": [s["numberOfCar"] for s in stats],
        "Van": [s["numberOfVan"] for s in stats],
        "Truck": [s["numberOfTruck"] for s in stats],
        "Bus": [s["numberOfBus"] for s in stats],
        "Fire Truck": [s["numberOfFireTruck"] for s in stats],
        "Container": [s["numberOfContainer"] for s in stats],
    }

    x = np.arange(len(dates))  # the label locations
    width = 0.1  # width of each bar
    num_categories = len(vehicle_types)
    offset_range = (np.arange(num_categories) - num_categories / 2) * width + width / 2

    plt.figure(figsize=(15, 7))

    for i, (label, data) in enumerate(vehicle_types.items()):
        plt.bar(x + offset_range[i], data, width, label=label)

    plt.title("Traffic Statistics by Vehicle Type")
    plt.xlabel("Date")
    plt.ylabel("Count")
    plt.xticks(x, dates, rotation=45)
    plt.legend(loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.grid(axis="y", linestyle="--", alpha=0.6)

    # Save to BytesIO
    img_bytes = BytesIO()
    plt.savefig(img_bytes, format="png")
    plt.close()
    img_bytes.seek(0)

    image = MIMEImage(img_bytes.read())
    image.add_header("Content-ID", "<stats_chart>")
    image.add_header("Content-Disposition", "inline", filename="chart.png")
    return image

