import requests
import time
from datetime import datetime, timedelta
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

BASE_URL = 'https://api.binance.com'


# 24時間の取引データを取得する関数
def get_24hr_ticker(symbol):
    endpoint = '/api/v3/ticker/24hr' # https://developers.binance.com/docs/binance-spot-api-docs/rest-api#24hr-ticker-price-change-statistics
    params = {
        'symbol': symbol,
    }
    url = BASE_URL + endpoint
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception("Failed to get 24hr ticker data. Response: {}".format(response.text))

# UNIXタイムスタンプを日本時間に変換する関数
def convert_to_japan_time(unix_timestamp):
    utc_time = datetime.utcfromtimestamp(unix_timestamp / 1000)  # 秒に変換
    jst_time = utc_time + timedelta(hours=9)
    return jst_time.strftime('%Y-%m-%d %H:%M:%S')

# 日付と時間に分割する関数
def split_date_time(jst_time_str):
    date_time = datetime.strptime(jst_time_str, '%Y-%m-%d %H:%M:%S')
    date_str = date_time.strftime('%Y-%m-%d')
    time_str = date_time.strftime('%H:%M:%S')
    return date_str, time_str

# Google Sheetsにデータを入力する関数
def update_google_sheet(ticker_info):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    credentials_json = 'credentials.json' 

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_json, SCOPES)
            creds = flow.run_local_server(port=8080)  # 固定ポートを指定
        # トークン情報を保存
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)


    sheet = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='Sheet1!A:A').execute()
    values = sheet.get('values', [])
    next_row = len(values) + 1
    if next_row < 3:
        next_row = 3

    # 終了時間を日付と時間に分割
    close_date, close_time = split_date_time(ticker_info['closeTime'])

    RANGE_NAME = f'Sheet1!A{next_row}'
    values = [
        [close_date, close_time, ticker_info['lastPrice'], ticker_info['openPrice'], ticker_info['highPrice'], ticker_info['lowPrice'], ticker_info['volume'], ticker_info['priceChange'], ticker_info['priceChangePercent'], ticker_info['weightedAvgPrice']]
    ]
    body = {
        'values': values
    }

    result = service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME,
        valueInputOption='RAW', body=body).execute()

    print('{0} cells updated.'.format(result.get('updatedCells')))

def main():
    symbol = 'BTCUSDC'  # 取得したい暗号資産のシンボル
    try:
        ticker_info = get_24hr_ticker(symbol)
        ticker_info['closeTime'] = convert_to_japan_time(ticker_info['closeTime'])
        print(ticker_info) #ログ

        update_google_sheet(ticker_info)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()
