import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

AUTH_KEY = os.getenv("AUTH_KEY")
URL = "https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON"
CSV_DIR = Path(__file__).resolve().parent / "csv_data"


def build_data_metadata(requested_date, data_date, from_cache=False):
    """화면에 표시할 데이터의 최신 상태와 출처 정보를 만듭니다."""

    is_today = requested_date == data_date

    return {
        "source": "한국수출입은행",
        "requested_date": requested_date,
        "data_date": data_date,
        "is_today": is_today,
        "from_cache": from_cache,
        "status": "today" if is_today else "recent_business_day",
        "status_label": "오늘 데이터" if is_today else "최근 영업일 데이터",
        "message": (
            "오늘 고시된 최신 환율입니다."
            if is_today
            else f"오늘 환율이 없어 {data_date}의 최근 영업일 환율을 표시합니다."
        ),
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def load_latest_exchange_data():
    """저장된 환율 CSV 중 가장 최근 날짜의 데이터를 불러옵니다."""

    csv_files = sorted(CSV_DIR.glob("exchange_*.csv"), reverse=True)

    for csv_path in csv_files:
        date = csv_path.stem.removeprefix("exchange_")

        try:
            datetime.strptime(date, "%Y%m%d")
            df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype=str)
        except (ValueError, OSError, pd.errors.ParserError, UnicodeDecodeError):
            continue

        if not df.empty:
            if "통화코드" in df.columns:
                df = df[df["통화코드"] != "KRW"]

            return df.to_dict(orient="records"), date

    return None, None


def format_exchange_data(json_data):
    """API 응답의 열 이름과 표시할 데이터를 정리합니다."""

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

    df = df[df["통화코드"] != "KRW"]

    return df


def get_saved_data_or_error(date, error_message):
    """최근 CSV가 있으면 반환하고, 없으면 전달받은 오류를 반환합니다."""

    exchange_data, saved_date = load_latest_exchange_data()

    if exchange_data:
        metadata = build_data_metadata(date, saved_date, from_cache=True)
        return exchange_data, saved_date, None, metadata

    metadata = build_data_metadata(date, date)
    return None, date, error_message, metadata


def get_exchange_data():
    """오늘의 환율을 조회하고, 없으면 가장 최근 CSV 데이터를 반환합니다."""

    date = datetime.today().strftime("%Y%m%d")
    params = {
        "authkey": AUTH_KEY,
        "searchdate": date,
        "data": "AP01",
    }

    try:
        response = requests.get(URL, params=params, timeout=10)
        response.raise_for_status()
        json_data = response.json()

        if isinstance(json_data, list) and json_data:
            df = format_exchange_data(json_data)

            CSV_DIR.mkdir(exist_ok=True)
            df.to_csv(
                CSV_DIR / f"exchange_{date}.csv",
                index=False,
                encoding="utf-8-sig",
            )

            metadata = build_data_metadata(date, date)
            return df.to_dict(orient="records"), date, None, metadata

        return get_saved_data_or_error(
            date,
            "오늘 날짜와 저장된 환율 데이터가 없습니다.",
        )

    except requests.RequestException as error:
        return get_saved_data_or_error(
            date,
            f"API 요청 중 오류가 발생했습니다: {error}",
        )

    except ValueError:
        return get_saved_data_or_error(
            date,
            "API 응답을 JSON 형식으로 변환하지 못했습니다.",
        )


if __name__ == "__main__":
    exchange_data, date, error, metadata = get_exchange_data()

    if error:
        print(error)
    else:
        print(f"기준일: {date}")
        print(metadata["message"])
        print(pd.DataFrame(exchange_data))