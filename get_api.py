import requests
import os
import pandas as pd

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

AUTH_KEY = os.getenv("AUTH_KEY")
DATE = datetime.today().strftime("%Y%m%d")

URL = f"https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON"

params = {
        "authkey": AUTH_KEY,
        "searchdate": DATE,
        "data": "AP01"
    }

response = requests.get(URL, params=params)

json_data = response.json()

df = pd.DataFrame(json_data)

df = df.rename(columns={
    "result": "결과",
    "cur_unit": "통화코드",
    "ttb": "전신환매입률",
    "tts": "전신환매도율",
    "deal_bas_r": "매매기준율",
    "bkpr": "장부가격",
    "yy_efee_r": "년환가료율",
    "ten_dd_efee_r": "10일환가료율",
    "kftc_bkpr": "서울외국환중개장부가격",
    "kftc_deal_bas_r": "서울외국환중개매매기준율",
    "cur_nm": "통화명"
}) # column의 이름을 한글로 변환
df.drop(
    columns=["결과", "년환가료율", "10일환가료율"],
    inplace=True
) # 필요없는 부분 삭제

df.to_csv(f"./csv_data/exchange_{DATE}.csv", index=False, encoding="utf-8-sig")
print(df)

