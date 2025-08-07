"""
RUN THIS SCRIPT IN DJANGO SHELL
"""

import os
from datetime import datetime
from pathlib import Path
import requests
import json

from ...models import Trade, Tool, Account

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
        file_path = Path(cwd.parent.parent.parent.parent / 'media' / 'chart_screenshots' / 'user_1' / 'account_1' / filename)

        # Get the directory part of the file path
        dir_path = file_path.parent

        # Check if directory exists, create it if it doesn't
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)

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

    print(os.environ['NOTION_TOKEN'])

    headers = {
        "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    response = requests.post(db_url, headers=headers)

    data = response.json()
    print(data)
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

        d['side'] = 'SHORT'

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

            with open(f"{cwd.parent}/data.json", "w", encoding="utf-8") as f:
                json.dump(d, f, indent=4, ensure_ascii=False)

            output.append(d)
        else:
            d = {}

    with open(f"{cwd.parent}/data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)


def import_trades_to_db():
    """
    Assumes user id is 1, and account id is 1
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Build full path to your JSON file relative to project root
    json_path = os.path.join(BASE_DIR + '/utils', 'data.json')

    trade_dicts = json.load(open(json_path, encoding='utf-8'))

    for d in trade_dicts:
        try:
            account = Account.objects.get(pk=1)
            tool_name = d.get("Инструмент").strip() + "-USDT"
            tool, created = Tool.objects.get_or_create(name=tool_name, defaults={'account': account})

            start_time = datetime.fromisoformat(d["Вход"]) if d["Вход"] else None

            print(start_time)

            end_time = datetime.fromisoformat(d["Выход"]) if d["Выход"] else None

            risk_usd = float(d["Риск"])
            pnl_usd = float(d["Прибыль"]) if d["Прибыль"] else 0
            description = d.get("description", "")
            result = d.get("result", "")
            side = d.get("side", "")

            trade = Trade.objects.create(
                side=side,
                tool=tool,
                account=account,
                start_time=start_time,
                end_time=end_time,
                risk_percent=risk_usd,  # same as risk_percent because deposit is 100$
                risk_usd=risk_usd,  # If you want to derive this from account balance, handle separately
                pnl_usd=pnl_usd,
                commission_usd=0,
                description=description,
                result=result,
            )

            screenshot_path = f'chart_screenshots/user_{account.user_id}/account_{account.id}/{trade.pk}.png'
            full_path = Path('media') / screenshot_path  # Adjust if your MEDIA_ROOT is elsewhere
            if full_path.exists():
                trade.screenshot = screenshot_path
                print(f"Trade screenshot relative path: {trade.screenshot.name}")
            trade.save()

        except Exception as e:
            print(f"Error importing trade {d.get('Инструмент')}: {e}")

# Execute in db console before applying script
"""TRUNCATE TABLE trading_buddy_tool RESTART IDENTITY CASCADE"""
download_trades()
import_trades_to_db()
