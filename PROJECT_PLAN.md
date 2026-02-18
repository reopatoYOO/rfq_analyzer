# RFQ 스펙 문서 분석기 - 프로젝트 계획

## 1. 프로젝트 개요

자동차 메이커로부터 수신한 RFQ(Request for Quotation) 스펙 문서(PDF, PPT, Excel)를 자동 분석하여,  
디스플레이 제품 개발에 필요한 **주요 수치형 스펙**을 추출하고 **사전 정의된 Excel 양식에 맞춰 정리**하는 프로그램.

### 핵심 요구사항

| # | 요구사항 | 설명 |
|---|---------|------|
| 1 | **다국어 지원** | 독일어, 프랑스어 등 다국어 문서를 영어로 번역하여 처리 |
| 2 | **LLM 기반 분석** | Google Gemini API를 활용한 스펙 추출 및 전문 용어 통합 |
| 3 | **Excel 양식 기반 출력** | 사용자가 제공한 Excel 템플릿에 스펙을 매핑하여 기입 |
| 4 | **원문 참조 추적** | 추출된 각 스펙 값의 출처(파일명, 페이지, 원문)를 함께 기록 |

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        입력 문서 폴더                            │
│              (PDF, PPT, Excel / EN, DE, FR)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
              ┌────────────────────────┐
              │  Phase 1: 문서 파싱     │
              │  (텍스트/테이블 추출)    │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  Phase 2: 언어 감지     │
              │  & 영어 번역            │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  Phase 3: LLM 분석     │
              │  (Gemini API)          │
              │  - 문서 필터링          │
              │  - 스펙 추출            │
              │  - 전문용어 통합         │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  Phase 4: Excel 출력   │
              │  (템플릿 기반 기입)      │
              │  + 원문 참조 시트        │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  결과 Excel 파일        │
              └────────────────────────┘
```

---

## 3. 기술 스택

| 구분 | 라이브러리/서비스 | 용도 |
|------|-----------------|------|
| PDF 파싱 | `pdfplumber`, `PyMuPDF(fitz)` | PDF 텍스트/테이블 추출 |
| PPT 파싱 | `python-pptx` | PowerPoint 텍스트/테이블 추출 |
| Excel 파싱 | `openpyxl`, `pandas` | Excel 데이터 읽기 |
| 언어 감지 | `langdetect` | 문서 언어 자동 감지 (DE/FR/EN 등) |
| LLM 분석 | `google-generativeai` (Gemini API) | 스펙 추출, 번역, 전문용어 통합 |
| Excel 출력 | `openpyxl` | 템플릿 기반 Excel 기입 + 서식 유지 |
| 설정 관리 | `PyYAML` | 설정 파일(config.yaml) 관리 |

---

## 4. 프로젝트 구조

```
rfq_analysis/
├── rfq_analyzer.py            # 메인 실행 파일 (CLI 진입점)
├── config.yaml                # 설정 파일 (API 키, 키워드, 경로 등)
├── requirements.txt           # 의존성 패키지 목록
├── PROJECT_PLAN.md            # 프로젝트 계획 문서 (본 파일)
│
├── parsers/                   # Phase 1: 문서 파싱 모듈
│   ├── __init__.py
│   ├── base_parser.py         # 파서 공통 인터페이스
│   ├── pdf_parser.py          # PDF 파싱
│   ├── ppt_parser.py          # PPT 파싱
│   └── excel_parser.py        # Excel 파싱
│
├── translator/                # Phase 2: 번역 모듈
│   ├── __init__.py
│   ├── language_detector.py   # 언어 감지
│   └── translator.py          # Gemini 기반 번역
│
├── analyzer/                  # Phase 3: LLM 분석 모듈
│   ├── __init__.py
│   ├── gemini_client.py       # Gemini API 클라이언트
│   ├── doc_filter.py          # 문서 관련성 필터링
│   ├── spec_extractor.py      # 스펙 추출 엔진
│   └── term_normalizer.py     # 전문용어 정규화/통합
│
├── exporter/                  # Phase 4: Excel 출력 모듈
│   ├── __init__.py
│   ├── template_mapper.py     # 템플릿 매핑 로직
│   ├── excel_writer.py        # Excel 기입
│   └── reference_tracker.py   # 원문 참조 추적
│
├── models/                    # 데이터 모델
│   ├── __init__.py
│   └── spec_models.py         # 스펙 데이터 클래스 정의
│
├── templates/                 # Excel 템플릿 폴더
│   └── spec_template.xlsx     # 사용자 제공 기본 양식
│
├── input_docs/                # 입력 문서 폴더
│
└── output/                    # 출력 결과 폴더
```

---

## 5. 상세 작업 단계

### Phase 1: 문서 파싱 엔진

> **목표**: 모든 입력 파일(PDF, PPT, Excel)에서 텍스트와 테이블을 추출한다.

| 순서 | 작업 | 상세 내용 |
|------|------|----------|
| 1-1 | 환경 구축 | Python 가상환경 생성, 의존성 패키지 설치, `requirements.txt` 작성 |
| 1-2 | 데이터 모델 정의 | `ParsedDocument` 데이터 클래스 정의 (파일명, 페이지번호, 텍스트, 테이블, 언어 등) |
| 1-3 | PDF 파서 구현 | `pdfplumber`로 페이지별 텍스트 + 테이블 추출, 페이지 번호 추적 |
| 1-4 | PPT 파서 구현 | `python-pptx`로 슬라이드별 텍스트 + 테이블 추출, 슬라이드 번호 추적 |
| 1-5 | Excel 파서 구현 | `openpyxl`로 시트별 데이터 추출, 시트명/행번호 추적 |
| 1-6 | 통합 파서 구현 | 파일 확장자 기반 자동 파서 선택 + 일괄 처리 인터페이스 |
| 1-7 | 테스트 | 샘플 문서로 파싱 결과 검증 |

**산출물**: 모든 문서에서 **페이지/슬라이드/행 단위로 추적 가능한** 텍스트 데이터

---

### Phase 2: 언어 감지 및 번역

> **목표**: 독일어/프랑스어 문서를 감지하고 영어로 번역한다.

| 순서 | 작업 | 상세 내용 |
|------|------|----------|
| 2-1 | 언어 감지 모듈 | `langdetect`로 문서/페이지별 언어 자동 감지 (EN/DE/FR 등) |
| 2-2 | 번역 모듈 구현 | Gemini API를 활용한 번역 (기술 문서 맥락 유지) |
| 2-3 | 번역 캐싱 | 동일 문서 재처리 시 번역 결과 캐싱으로 API 비용 절감 |
| 2-4 | 원문 보존 | 번역된 텍스트와 원문을 함께 저장 (원문 참조용) |
| 2-5 | 테스트 | 독일어/프랑스어 샘플 문서로 번역 품질 검증 |

**핵심 포인트**:
- 기술 용어의 정확한 번역을 위해 Gemini에 **자동차 디스플레이 도메인 컨텍스트** 제공
- 원문과 번역문을 쌍으로 보존하여 Phase 4에서 원문 참조 가능

---

### Phase 3: LLM 기반 스펙 분석 (Gemini)

> **목표**: Gemini를 활용하여 문서를 필터링하고, 스펙을 추출하며, 메이커별 전문 용어를 통합한다.

| 순서 | 작업 | 상세 내용 |
|------|------|----------|
| 3-1 | Gemini API 클라이언트 | API 키 관리, 요청/응답 처리, Rate Limit 핸들링, 재시도 로직 |
| 3-2 | 문서 필터링 | LLM에게 문서 내용을 전달하여 디스플레이 관련 문서 여부 판별 |
| 3-3 | 프롬프트 설계 | 스펙 추출을 위한 체계적인 프롬프트 작성 (Few-shot 예시 포함) |
| 3-4 | 스펙 추출 엔진 | 구조화된 JSON 형태로 스펙 값 추출 (항목명, 값, 단위, 조건) |
| 3-5 | 전문용어 정규화 | 메이커별 상이한 용어를 표준 용어로 통합 (예: Leuchtdichte → Luminance → 휘도) |
| 3-6 | 신뢰도 점수 | 추출된 각 스펙 값에 대한 신뢰도 점수 부여 |
| 3-7 | 테스트 | 다양한 메이커 문서로 추출 정확도 검증 |

**프롬프트 전략 예시**:
```
You are an automotive display specification analyst.
From the following document text, extract display-related specifications.

For each spec found, return JSON with:
- spec_name: standardized English name
- value: numeric value
- unit: measurement unit
- condition: test condition (if any)
- confidence: 0.0 ~ 1.0
- source_text: exact original text where this spec was found
- page: page/slide number

Normalize terminology across manufacturers:
- "Leuchtdichte" (DE) = "Luminosité" (FR) = "Luminance" (EN)
- "Kontrastverhältnis" (DE) = "Rapport de contraste" (FR) = "Contrast Ratio" (EN)
...
```

**메이커별 전문용어 통합 예시**:

| 표준 용어 (EN) | 독일어 (DE) | 프랑스어 (FR) | 설명 |
|---------------|------------|--------------|------|
| Luminance | Leuchtdichte | Luminosité | 휘도 (cd/m²) |
| Contrast Ratio | Kontrastverhältnis | Rapport de contraste | 명암비 |
| Viewing Angle | Betrachtungswinkel | Angle de vision | 시야각 |
| Operating Temperature | Betriebstemperatur | Température de fonctionnement | 동작 온도 |
| Resolution | Auflösung | Résolution | 해상도 |
| Response Time | Reaktionszeit | Temps de réponse | 응답 시간 |
| Color Gamut | Farbraum | Gamut de couleurs | 색재현율 |
| Power Consumption | Leistungsaufnahme | Consommation d'énergie | 소비 전력 |

---

### Phase 4: Excel 템플릿 기반 출력 + 원문 참조

> **목표**: 사용자가 제공한 Excel 양식에 맞춰 스펙을 기입하고, 원문 참조를 제공한다.

| 순서 | 작업 | 상세 내용 |
|------|------|----------|
| 4-1 | 템플릿 분석기 | 사용자 제공 Excel 템플릿의 구조 분석 (항목명, 셀 위치, 서식) |
| 4-2 | 매핑 로직 | 추출된 스펙 항목과 템플릿 셀 위치 매핑 (LLM 기반 유사도 매칭) |
| 4-3 | Excel 기입 | 매핑된 위치에 값/단위 기입, 기존 서식 유지 |
| 4-4 | 원문 참조 시트 | 별도 "Reference" 시트에 원문 참조 기록 |
| 4-5 | 하이퍼링크 연결 | 스펙 셀에 코멘트 또는 하이퍼링크로 원문 참조 연결 |
| 4-6 | 신뢰도 표시 | 셀 배경색으로 LLM 추출 신뢰도 시각화 (녹/황/적) |
| 4-7 | 테스트 | 실제 템플릿으로 출력 결과 검증 |

**원문 참조 구조**:

각 추출된 스펙 값에 대해 다음 정보를 기록:

| 항목 | 내용 |
|------|------|
| 소스 파일명 | `BMW_Display_Spec_2026.pdf` |
| 위치 | Page 15 / Slide 8 / Sheet "Optical", Row 23 |
| 원문 (원어) | `"Leuchtdichte: ≥ 1000 cd/m² (bei 25°C)"` |
| 번역문 (영어) | `"Luminance: ≥ 1000 cd/m² (at 25°C)"` |
| 추출된 값 | 1000 cd/m² |
| 신뢰도 | 0.95 |

**Excel 출력 구조**:
```
[Sheet 1: Spec Summary]  ← 사용자 제공 템플릿 양식 그대로
  - 템플릿 항목에 맞춰 값 기입
  - 각 셀에 코멘트로 원문 참조 삽입

[Sheet 2: Reference]  ← 자동 생성
  - 모든 추출 스펙의 원문 참조 테이블
  - 소스파일, 페이지, 원문, 번역문, 신뢰도
  
[Sheet 3: Unmatched]  ← 자동 생성
  - 템플릿에 매핑되지 않은 추가 발견 스펙
  - 수동 검토 필요 항목
```

---

### Phase 5: 통합 및 사용자 인터페이스

| 순서 | 작업 | 상세 내용 |
|------|------|----------|
| 5-1 | CLI 인터페이스 | 명령줄 기반 실행 (입력폴더, 템플릿, 출력경로 지정) |
| 5-2 | 설정 파일 | `config.yaml`로 API 키, 키워드, 경로 등 관리 |
| 5-3 | 로깅 | 처리 진행 상황 및 오류 로깅 |
| 5-4 | 에러 핸들링 | 파싱 실패, API 오류 등 예외 처리 |
| 5-5 | 통합 테스트 | 전체 파이프라인 End-to-End 테스트 |

---

## 6. 작업 우선순위 및 일정

```
Week 1  ──── Phase 1: 문서 파싱 엔진
               ├── 환경 구축 + 데이터 모델
               ├── PDF / PPT / Excel 파서
               └── 통합 파서 + 테스트

Week 2  ──── Phase 2: 언어 감지 및 번역
               ├── 언어 감지 모듈
               ├── Gemini 번역 모듈
               └── 원문 보존 + 캐싱

Week 3  ──── Phase 3: LLM 기반 스펙 분석
               ├── Gemini 클라이언트 + 프롬프트 설계
               ├── 스펙 추출 엔진
               └── 전문용어 정규화

Week 4  ──── Phase 4: Excel 출력
               ├── 템플릿 분석 + 매핑
               ├── Excel 기입 + 원문 참조
               └── 신뢰도 표시

Week 5  ──── Phase 5: 통합 및 테스트
               ├── CLI / 설정 파일
               ├── 에러 핸들링 / 로깅
               └── End-to-End 테스트
```

---

## 7. 실행 흐름 요약

```
사용자 실행
    │
    ├── 1) 입력 폴더 스캔 → PDF, PPT, Excel 파일 수집
    │
    ├── 2) 파일별 파싱 → 텍스트 + 테이블 추출 (페이지/슬라이드/행 추적)
    │
    ├── 3) 언어 감지 → DE/FR이면 Gemini로 영어 번역 (원문 보존)
    │
    ├── 4) Gemini 분석
    │      ├── 디스플레이 관련 문서 필터링
    │      ├── 스펙 항목 추출 (JSON 구조화)
    │      └── 전문용어 정규화 (메이커별 → 표준)
    │
    ├── 5) Excel 템플릿 읽기 → 항목-셀 매핑
    │
    ├── 6) 스펙 값 기입
    │      ├── 템플릿 셀에 값 기입
    │      ├── 셀 코멘트로 원문 참조 삽입
    │      └── 신뢰도 기반 셀 색상 표시
    │
    └── 7) 결과 저장
           ├── Sheet 1: Spec Summary (템플릿 양식)
           ├── Sheet 2: Reference (원문 참조)
           └── Sheet 3: Unmatched (미매핑 항목)
```

---

## 8. 필요 사전 준비

- [ ] **Google Gemini API 키** 발급
- [ ] **샘플 RFQ 문서** 준비 (PDF/PPT/Excel, 영어/독일어/프랑스어)
- [ ] **Excel 스펙 템플릿** 준비 (기입할 양식)
- [ ] Python 3.10+ 환경
