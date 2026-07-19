import os
from datetime import date, datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

ECOS_API_KEY = os.getenv("ECOS_API_KEY")
ECOS_BASE_URL = "https://ecos.bok.or.kr/api"
EXCHANGE_STAT_CODE = "731Y001"

# 한국은행 ECOS: 3.1.1.1. 주요국 통화의 대원화환율
ECOS_CURRENCY_ITEMS = {
    "USD": "0000001",
    "JPY(100)": "0000002",
    "EUR": "0000003",
    "CNH": "0000053",
    "GBP": "0000012",
    "CAD": "0000013",
    "CHF": "0000014",
    "HKD": "0000015",
    "AUD": "0000017",
    "NZD": "0000026",
}


class EcosApiError(Exception):
    """ECOS API 조회 또는 응답 처리에 실패했을 때 발생합니다."""


def _format_date(value):
    if isinstance(value, datetime):
        value = value.date()

    if isinstance(value, date):
        return value.strftime("%Y%m%d")

    datetime.strptime(value, "%Y%m%d")
    return value


def get_exchange_history(currency_code, start_date, end_date, api_key=None):
    """선택한 통화의 일별 대원화 환율을 조회합니다."""

    key = api_key or ECOS_API_KEY

    if not key:
        raise EcosApiError("ECOS_API_KEY가 설정되어 있지 않습니다.")

    item_code = ECOS_CURRENCY_ITEMS.get(currency_code)

    if not item_code:
        raise EcosApiError(f"ECOS 환율 항목이 등록되지 않은 통화입니다: {currency_code}")

    start = _format_date(start_date)
    end = _format_date(end_date)
    url = (
        f"{ECOS_BASE_URL}/StatisticSearch/{key}/json/kr/1/100/"
        f"{EXCHANGE_STAT_CODE}/D/{start}/{end}/{item_code}"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        raise EcosApiError(f"ECOS API 요청에 실패했습니다: {error}") from error
    except ValueError as error:
        raise EcosApiError("ECOS API 응답을 JSON으로 변환하지 못했습니다.") from error

    if "RESULT" in payload:
        result = payload["RESULT"]
        raise EcosApiError(result.get("MESSAGE", "ECOS API에서 오류를 반환했습니다."))

    rows = payload.get("StatisticSearch", {}).get("row", [])

    return [
        {
            "date": row["TIME"],
            "value": float(row["DATA_VALUE"].replace(",", "")),
            "currency_code": currency_code,
            "item_name": row["ITEM_NAME1"],
            "unit": row["UNIT_NAME"],
            "source": "한국은행 ECOS",
        }
        for row in rows
    ]


def get_recent_exchange_history(currency_code, business_days=10, end_date=None):
    """최근 영업일 환율을 지정한 개수만큼 반환합니다."""

    end = end_date or date.today()

    if isinstance(end, str):
        end = datetime.strptime(end, "%Y%m%d").date()

    start = end - timedelta(days=max(business_days * 3, 30))
    history = get_exchange_history(currency_code, start, end)

    return history[-business_days:]