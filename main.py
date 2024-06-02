from flask import Flask, request
import requests
from datetime import datetime, timedelta
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
import logging

app = Flask(__name__)

# ログの設定
logging.basicConfig(level=logging.INFO)

load_dotenv()

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
logging.info(f"Spreadsheet ID: {SPREADSHEET_ID}")

BASE_URL = 'https://api.binance.com'

def get_24hr_ticker(symbol):
    logging.info("Fetching 24hr ticker data...")
    endpoint = '/api/v3/ticker/24hr'
    params = {'symbol': symbol}
    url = BASE_URL + endpoint
    response = requests.get(url, params=params)
    if response.status_code == 200:
        logging.info("Ticker data fetched successfully.")
        return response.json()
    else:
        logging.error(f"Failed to get 24hr ticker data. Response: {response.text}")
        raise Exception(f"Failed to get 24hr ticker data. Response: {response.text}")

def convert_to_japan_time(unix_timestamp):
    utc_time = datetime.utcfromtimestamp(unix_timestamp / 1000)
    jst_time = utc_time + timedelta(hours=9)
    return jst_time.strftime('%Y-%m-%d %H:%M:%S')

def split_date_time(jst_time_str):
    date_time = datetime.strptime(jst_time_str, '%Y-%m-%d %H:%M:%S')
    date_str = date_time.strftime('%Y-%m-%d')
    time_str = date_time.strftime('%H:%M:%S')
    return date_str, time_str

def update_google_sheet(ticker_info):
    logging.info("Updating Google Sheet...")
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    credentials_json = 'credentials.json'

    if os.path.exists('/tmp/token.json'):
        creds = Credentials.from_authorized_user_file('/tmp/token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_json, SCOPES)
            creds = flow.run_local_server(port=8080)
        with open('/tmp/token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='Sheet1!A:A').execute()
    values = sheet.get('values', [])
    next_row = len(values) + 1
    if next_row < 3:
        next_row = 3

    close_date, close_time = split_date_time(ticker_info['closeTime'])

    RANGE_NAME = f'Sheet1!A{next_row}'
    values = [
        [close_date, close_time, ticker_info['lastPrice'], ticker_info['openPrice'], ticker_info['highPrice'], ticker_info['lowPrice'], ticker_info['volume'], ticker_info['priceChange'], ticker_info['priceChangePercent'], ticker_info['weightedAvgPrice']]
    ]
    body = {'values': values}

    result = service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME,
        valueInputOption='RAW', body=body).execute()

    logging.info(f'{result.get("updatedCells")} cells updated.')

@app.route('/', methods=['GET'])
def main():
    symbol = 'BTCUSDC'
    try:
        ticker_info = get_24hr_ticker(symbol)
        ticker_info['closeTime'] = convert_to_japan_time(ticker_info['closeTime'])
        logging.info(f"Ticker info: {ticker_info}")
        update_google_sheet(ticker_info)
        return "Success"
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return str(e)

if __name__ == '__main__':
    app.run(debug=True)
