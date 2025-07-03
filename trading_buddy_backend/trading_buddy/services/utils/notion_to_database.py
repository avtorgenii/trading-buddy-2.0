import os
from pathlib import Path
import requests
import json

from dotenv import load_dotenv

cwd = Path(__file__).resolve()
load_dotenv(dotenv_path=cwd.parent.parent.parent.parent.parent / '.env.dev')


def download_image(url, filename):
    """Download an image from a URL and save it to a file"""
    try:
        # Send GET request to download the image
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Create the file path
        file_path = Path(
            f"C:\\Users\\ashes\\PycharmProjects\\trading-buddy-2.0\\trading_buddy_backend\\media\\chart_screenshots\\user_1\\account_1\\{filename}")

        # Write the image content to file
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Image successfully downloaded: {file_path}")
        return file_path

    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return None


def download_trades():
    db_id = "1c8a445e6e6280629effd7dfa5ece817"
    db_url = f"https://api.notion.com/v1/databases/{db_id}/query"

    headers = {
        "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    response = requests.post(db_url, headers=headers)

    data = response.json()
    output = list()

    trade_num = 0

    for item in data['results'][::-1]:
        d = {}
        for property_name, property_data in item['properties'].items():
            print(property_name, property_data)
            if property_name == "Тип счета":
                d[property_name] = property_data['select']['name']
            elif property_name == "Прибыль":
                d[property_name] = property_data['number']
            elif property_name == "Выход":
                d[property_name] = (property_data.get('date') or {}).get('start')
            elif property_name == "Риск":
                d[property_name] = property_data['number']
            elif property_name == "Вход":
                d[property_name] = (property_data.get('date') or {}).get('start')
            elif property_name == "Рынок":
                d[property_name] = property_data['select']['name']
            elif property_name == "Инструмент":
                d[property_name] = property_data['title'][0]['plain_text']

        if d['Рынок'] == 'Крипта':
            trade_num += 1
            page_id = item['id'].replace('-', '')
            blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            response = requests.get(blocks_url, headers=headers)
            blocks_data = response.json()

            # We first read description of trade, and then result
            reading_description = False
            description = ''
            result = ''

            for block in blocks_data['results']:
                if block['type'] == "heading_1":
                    reading_description = not reading_description
                elif block['type'] == "paragraph":
                    if reading_description:
                        description += (
                                "\n".join([chunk['plain_text'] for chunk in block['paragraph']['rich_text']]) + "\n")
                    else:
                        result += ("\n".join([chunk['plain_text'] for chunk in block['paragraph']['rich_text']]) + "\n")
                elif block['type'] == "image":
                    # Handling image
                    download_image(block['image']['file']['url'], f"{trade_num}.png")

            d['result'] = result
            d['description'] = description

            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(d, f, indent=4, ensure_ascii=False)

            output.append(d)
        else:
            d = {}

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)


def import_trades_to_db():
    pass


if __name__ == "__main__":
    download_trades()
    import_trades_to_db()
