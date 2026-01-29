"""Valuation Agent prompts"""
from pathlib import Path


def load_knowledge_base() -> dict[str, str]:
    """
    knowledge/ 디렉토리에서 투자 철학 파일을 로드합니다.

    Returns:
        {
            "deep_value": "Deep Value 철학 내용",
            "quality": "Quality 철학 내용"
        }
    """
    # 프로젝트 루트의 knowledge 디렉토리
    knowledge_dir = Path(__file__).parents[4] / "knowledge"

    knowledge = {}

    # deep_value.md
    deep_value_path = knowledge_dir / "deep_value.md"
    if deep_value_path.exists():
        knowledge["deep_value"] = deep_value_path.read_text(encoding="utf-8")
    else:
        knowledge["deep_value"] = "Deep Value 투자 철학 파일을 찾을 수 없습니다."

    # quality.md
    quality_path = knowledge_dir / "quality.md"
    if quality_path.exists():
        knowledge["quality"] = quality_path.read_text(encoding="utf-8")
    else:
        knowledge["quality"] = "Quality 투자 철학 파일을 찾을 수 없습니다."

    return knowledge


SYSTEM_PROMPT = """당신은 가치투자 전문가입니다.

주어진 투자 철학을 기반으로 기업을 평가합니다:
1. Deep Value 관점 - 자산가치 대비 저평가 여부
2. Quality 관점 - 기업의 본질적 품질 및 성장성

각 관점에서 0-100점 척도로 점수를 매기고, 객관적인 근거를 제시하세요.
"""

DEEP_VALUE_PROMPT_TEMPLATE = """
## Deep Value 투자 철학

{deep_value_philosophy}

---

## 기업 정보

기업명: {company_name}
종목코드: {stock_code}

### 재무 분석
{financial_analysis}

### 주가 데이터
{stock_data}

---

위 투자 철학에 따라 **Deep Value 관점**에서 이 기업을 평가하세요.

다음 형식으로 작성:

**점수**: 0-100 (정수)

**분석**:
- 안전마진 평가
- 자산가치 대비 현재 가격
- PER, PBR 기준 충족 여부
- 재무 안정성 (부채비율, 유동비율)
- 종합 의견

**매수 신호**: (긍정 요인 3-5개)
**경고 신호**: (부정 요인 3-5개)
"""

QUALITY_PROMPT_TEMPLATE = """
## Quality 투자 철학

{quality_philosophy}

---

## 기업 정보

기업명: {company_name}
종목코드: {stock_code}

### 재무 분석
{financial_analysis}

### 뉴스 및 전망
{news_sentiment}

---

위 투자 철학에 따라 **Quality 관점**에서 이 기업을 평가하세요.

다음 형식으로 작성:

**점수**: 0-100 (정수)

**분석**:
- 경제적 해자 (경쟁 우위)
- 수익성 및 ROE 지속성
- 성장 잠재력
- 경영진 품질 (뉴스 기반 판단)
- 종합 의견

**강점**: (3-5개)
**약점**: (3-5개)
"""
