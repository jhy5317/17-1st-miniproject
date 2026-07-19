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
    exchange_data, date, error, metadata = get_exchange_data()
    formatted_date = datetime.strptime(date, "%Y%m%d").strftime("%Y년 %m월 %d일")
    exchange_data = sort_and_enrich_exchange_data(exchange_data or [])

    return exchange_data, formatted_date, error, metadata


@app.route("/")
def index():
    exchange_data, formatted_date, error, metadata = get_page_data()
    currency_map = {item["통화코드"]: item for item in exchange_data}
    primary_exchange_data = [
        currency_map[code] for code in PRIMARY_CURRENCIES if code in currency_map
    ]

    return render_template(
        "index.html",
        exchange_data=primary_exchange_data,
        date=formatted_date,
        error=error,
        metadata=metadata,
    )


@app.route("/rates")
def rates():
    exchange_data, formatted_date, error, metadata = get_page_data()

    return render_template(
        "search.html",
        exchange_data=exchange_data,
        date=formatted_date,
        error=error,
        metadata=metadata,
    )

@app.route("/rates/download.csv")
def download_rates_csv():
    """전체 환율 데이터를 엑셀에서도 열 수 있는 UTF-8 CSV로 제공합니다."""

    exchange_data, date, error, _metadata = get_exchange_data()

    if error or not exchange_data:
        return Response(
            error or "다운로드할 환율 데이터가 없습니다.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    exchange_data = sort_and_enrich_exchange_data(exchange_data)
    fieldnames = [
        "통화코드",
        "통화명",
        "전신환매입률",
        "전신환매도율",
        "매매기준율",
        "장부가격",
    ]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(exchange_data)
    csv_content = "\ufeff" + output.getvalue()

    return Response(
        csv_content,
        content_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="exchange_rates_{date}.csv"'
            )
        },
    )

@app.route("/calculator")
def calculator():
    exchange_data, formatted_date, error, metadata = get_page_data()
    currencies = build_calculator_currencies(exchange_data)

    return render_template(
        "calculator.html",
        currencies=currencies,
        date=formatted_date,
        error=error,
        metadata=metadata,
    )


@app.route("/api/ecos/exchange/<currency_code>")
def ecos_exchange_history(currency_code):
    try:
        history, cache_info = get_recent_exchange_history(
            currency_code.upper(),
            business_days=10,
            include_cache_info=True,
        )
        latest_date = history[-1]["date"] if history else None
        today = datetime.today().strftime("%Y%m%d")
        is_today = latest_date == today
        metadata = {
            "source": "한국은행 ECOS",
            "requested_date": today,
            "data_date": latest_date,
            "is_today": is_today,
            "status": "today" if is_today else "recent_business_day",
            "status_label": "오늘 데이터" if is_today else "최근 영업일 데이터",
            "message": (
                "오늘 공표된 최신 ECOS 환율입니다."
                if is_today
                else f"ECOS에서 확인되는 가장 최근 영업일({latest_date}) 데이터입니다."
            ),
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "from_cache": cache_info["from_cache"],
            "cache_is_stale": cache_info["is_stale"],
            "cache_saved_at": cache_info["saved_at"],
            "cache_message": cache_info["message"],
        }
        return jsonify(
            {
                "currency_code": currency_code.upper(),
                "history": history,
                "metadata": metadata,
            }
        )
    except EcosApiError as error:
        return jsonify({"error": str(error)}), 503


if __name__ == "__main__":
    app.run(debug=True)