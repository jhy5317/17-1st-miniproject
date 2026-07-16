# from flask import Flask, render_template, request


# app = Flask(__name__)
# app.config["TEMPLATES_AUTO_RELORD"] = True

# @app.route('/')
# def homepage():
#     return render_template("index.html")

# @app.route('/search')
# def search():
#     return render_template("search.html")

# if __name__ == "__main__":
#     app.run(debug = True)
import os
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, render_template

load_dotenv()

app = Flask(__name__)

AUTH_KEY = os.getenv("AUTH_KEY")
URL = "https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON"


def get_exchange_data():
    """한국수출입은행 API에서 오늘의 환율 정보를 가져옵니다."""

    date = datetime.today().strftime("%Y%m%d")

    params = {
        "authkey": AUTH_KEY,
        "searchdate": date,
        "data": "AP01",
    }

    try:
        response = requests.get(
            URL,
            params=params,
            timeout=10,
        )
        response.raise_for_status()

        json_data = response.json()

        if not isinstance(json_data, list) or len(json_data) == 0:
            return None, date, "오늘 날짜의 환율 데이터가 없습니다."

        df = pd.DataFrame(json_data)

        df = df.rename(
            columns={
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
                "cur_nm": "통화명",
            }
        )

        df.drop(
            columns=["결과", "년환가료율", "10일환가료율"],
            inplace=True,
            errors="ignore",
        )

        os.makedirs("csv_data", exist_ok=True)

        csv_path = f"./csv_data/exchange_{date}.csv"

        df.to_csv(
            csv_path,
            index=False,
            encoding="utf-8-sig",
        )

        # HTML 템플릿에 전달하기 좋은 형태로 변환
        exchange_data = df.to_dict(orient="records")

        return exchange_data, date, None

    except requests.RequestException as error:
        return None, date, f"API 요청 중 오류가 발생했습니다: {error}"

    except ValueError:
        return None, date, "API 응답을 JSON 형식으로 변환하지 못했습니다."


@app.route("/")
def index():
    exchange_data, date, error = get_exchange_data()

    formatted_date = datetime.strptime(date, "%Y%m%d").strftime("%Y년 %m월 %d일")

    return render_template(
        "index.html",
        exchange_data=exchange_data,
        date=formatted_date,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True)