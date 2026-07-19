from datetime import datetime

from flask import Flask, jsonify, render_template
from ecos_api import EcosApiError, get_recent_exchange_history
from get_api import get_exchange_data

app = Flask(__name__)
PRIMARY_CURRENCIES = ["USD", "JPY(100)", "EUR", "CNH", "GBP"]
POPULAR_CURRENCIES = [
    "USD",
    "JPY(100)",
    "CNH",
    "EUR",
    "GBP",
    "CAD",
    "AUD",
    "SGD",
    "HKD",
    "THB",
    "CHF",
    "NZD",
]
CURRENCY_ALIASES = {
    "AED": "아랍에미리트 UAE 디르함",
    "AUD": "호주 달러",
    "BHD": "바레인 디나르",
    "BND": "브루나이 달러",
    "CAD": "캐나다 달러",
    "CHF": "스위스 프랑",
    "CNH": "중국 위안 위안화",
    "DKK": "덴마크 크로네",
    "EUR": "유럽 유로 유로존",
    "GBP": "영국 파운드",
    "HKD": "홍콩 달러",
    "IDR(100)": "인도네시아 루피아",
    "JPY(100)": "일본 엔 옌",
    "KWD": "쿠웨이트 디나르",
    "MYR": "말레이시아 말레이지아 링기트",
    "NOK": "노르웨이 크로네",
    "NZD": "뉴질랜드 달러",
    "SAR": "사우디아라비아 사우디 리얄",
    "SEK": "스웨덴 크로나",
    "SGD": "싱가포르 달러",
    "THB": "태국 바트",
    "USD": "미국 달러",
}


def sort_and_enrich_exchange_data(exchange_data):
    """KRW를 제외하고 검색 별칭과 자주 찾는 통화 순서를 적용합니다."""

    priority = {code: index for index, code in enumerate(POPULAR_CURRENCIES)}
    filtered_data = []

    for item in exchange_data:
        code = item.get("통화코드")

        if code == "KRW":
            continue

        enriched_item = dict(item)
        enriched_item["검색키워드"] = CURRENCY_ALIASES.get(code, "")
        filtered_data.append(enriched_item)

    return sorted(
        filtered_data,
        key=lambda item: (
            priority.get(item["통화코드"], len(priority)),
            item.get("통화명", ""),
        ),
    )


def build_calculator_currencies(exchange_data):
    """환율 계산기에 사용할 통화별 1단위 원화 가격을 만듭니다."""

    currencies = [
        {
            "code": "KRW",
            "name": "대한민국 원",
            "rate": 1.0,
        }
    ]

    for item in exchange_data:
        code = item["통화코드"]
        rate = float(str(item["매매기준율"]).replace(",", ""))

        if "(100)" in code:
            rate /= 100

        currencies.append(
            {
                "code": code.replace("(100)", ""),
                "name": item["통화명"],
                "rate": rate,
            }
        )

    return currencies


def get_page_data():
    exchange_data, date, error = get_exchange_data()
    formatted_date = datetime.strptime(date, "%Y%m%d").strftime("%Y년 %m월 %d일")
    exchange_data = sort_and_enrich_exchange_data(exchange_data or [])

    return exchange_data, formatted_date, error


@app.route("/")
def index():
    exchange_data, formatted_date, error = get_page_data()
    currency_map = {item["통화코드"]: item for item in exchange_data}
    primary_exchange_data = [
        currency_map[code] for code in PRIMARY_CURRENCIES if code in currency_map
    ]

    return render_template(
        "index.html",
        exchange_data=primary_exchange_data,
        date=formatted_date,
        error=error,
    )


@app.route("/rates")
def rates():
    exchange_data, formatted_date, error = get_page_data()

    return render_template(
        "search.html",
        exchange_data=exchange_data,
        date=formatted_date,
        error=error,
    )


@app.route("/calculator")
def calculator():
    exchange_data, formatted_date, error = get_page_data()
    currencies = build_calculator_currencies(exchange_data)

    return render_template(
        "calculator.html",
        currencies=currencies,
        date=formatted_date,
        error=error,
    )


@app.route("/api/ecos/exchange/<currency_code>")
def ecos_exchange_history(currency_code):
    try:
        history = get_recent_exchange_history(currency_code.upper(), business_days=10)
        return jsonify({"currency_code": currency_code.upper(), "history": history})
    except EcosApiError as error:
        return jsonify({"error": str(error)}), 503


if __name__ == "__main__":
    app.run(debug=True)