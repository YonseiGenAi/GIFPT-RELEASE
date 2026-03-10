# GIFPT

**PDF 기반 학습 자료를 AI로 분석하여 요약과 Manim 애니메이션 영상을 자동 생성하는 서비스**

---

## 서비스 개요

사용자가 PDF를 업로드하면:
1. GPT-4o Vision이 PDF 페이지를 읽고 핵심 개념과 예시를 요약
2. 알고리즘/모델 유형에 맞게 Manim 애니메이션 영상을 자동 생성
3. 생성된 영상과 요약을 워크스페이스에서 확인하고, AI 챗봇으로 추가 질문 가능

---

## 시스템 아키텍처

```
[Client]
    │
    ▼
[Nginx :80]          ← Reverse Proxy
    │
    ▼
[Spring Boot :8080]  ← REST API, JWT 인증, 워크스페이스 관리
    │
    ├─ POST /analyze ──────────────────────────▶ [Django :8000]
    │                                                  │
    │                                          Celery Task 큐
    │                                                  │
    │                                                  ▼
    │                                          [Celery Worker]
    │                                           PDF → Vision → Manim → S3
    │                                                  │
    └─ POST /api/v1/analysis/{jobId}/complete ◀────────┘
```

### 컴포넌트

| 서비스 | 역할 | 기술 |
|--------|------|------|
| **Spring Boot** | REST API, JWT 인증, 워크스페이스/파일 관리 | Java, Spring Boot, JPA, MySQL |
| **Django** | AI 분석 요청 수신, Celery Task 큐잉 | Python, Django REST Framework |
| **Celery Worker** | PDF → 이미지 → GPT Vision → Manim 렌더링 → S3 업로드 | Celery, PyMuPDF, OpenAI, Manim |
| **Nginx** | Reverse Proxy | nginx:1.27-alpine |
| **Redis** | Celery 브로커 및 결과 백엔드 | Redis 7 |
| **MySQL (RDS)** | Spring 영속 데이터 저장 | MySQL |
| **AWS S3** | 생성된 영상 저장 | boto3 |

---

## AI 파이프라인 (Celery Worker)

```
PDF 파일
  │
  ▼
[1단계] PDF → base64 이미지 변환 (PyMuPDF, 2x 해상도)
  │
  ▼
[2단계] Vision 배치 요약 (gpt-4o-mini)
         - 5페이지씩 배치 처리
         - 수식/정의/핵심 개념 추출
  │
  ▼
[3단계] 최종 JSON 생성 (gpt-4o)
         - 부분 요약 통합 → summary
         - 영상 생성 지시문 → video_instructions
  │
  ▼
[4단계] 도메인 분류 → 렌더링 분기
         ├─ cnn_param  → CNN 파라미터 시각화
         ├─ sorting    → 정렬 알고리즘 애니메이션
         └─ 일반       → Pseudocode IR → Animation IR → Manim 코드 생성 (gpt-4o)
  │
  ▼
[5단계] Manim 렌더링 → MP4 (최대 3회 재시도, fallback 포함)
  │
  ▼
[6단계] S3 업로드 → Spring 콜백 (POST /api/v1/analysis/{jobId}/complete)
```

---

## API 엔드포인트

### Spring Boot (`/api/v1`)

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/workspaces` | PDF 업로드 + 워크스페이스 생성 (multipart/form-data) |
| `POST` | `/workspaces/from-file` | 이미 업로드된 fileId로 워크스페이스 생성 |
| `GET` | `/workspaces` | 내 워크스페이스 목록 조회 (페이징) |
| `GET` | `/workspaces/{workspaceId}` | 워크스페이스 상세 조회 (요약, 영상 URL, 상태 등) |
| `POST` | `/workspaces/{workspaceId}/chat` | 워크스페이스 기반 AI 챗봇 |
| `DELETE` | `/workspaces/{workspaceId}` | 워크스페이스 삭제 |
| `POST` | `/analysis/{jobId}/complete` | Worker → Spring 결과 콜백 (내부용) |

### Django (`/`)

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/analyze` | PDF 분석 작업 큐잉 (Spring → Django 내부 호출) |
| `GET` | `/task-status/{task_id}` | Celery 작업 상태 조회 |

---

## 디렉토리 구조

```
GIFPT-RELEASE/
├── docker-compose.yml
├── shared/
│   ├── uploads/        # 사용자 PDF 저장 (Spring/Django/Worker 공유)
│   └── results/        # Manim 렌더링 영상 임시 저장
├── nginx/
│   └── conf.d/         # Nginx 설정
├── GIFPT-BE/           # Spring Boot 백엔드
│   └── src/main/java/com/gifpt/
│       ├── security/   # JWT 인증, Spring Security
│       ├── workspace/  # 워크스페이스 CRUD, 챗봇
│       ├── analysis/   # 분석 Job 관리, 콜백 수신
│       └── file/       # 파일 업로드, S3 연동
└── GIFPT_AI/           # Django AI 서버 + Celery Worker
    └── studio/
        ├── tasks.py        # Celery Task (analyze_pdf_vision)
        ├── video_render.py # Manim 렌더링 파이프라인
        ├── s3_utils.py     # S3 업로드
        └── ai/
            ├── llm_domain.py       # 도메인 분류 LLM
            ├── llm_pseudocode.py   # Pseudocode IR 생성
            ├── llm_anim_ir.py      # Animation IR 생성
            ├── llm_codegen.py      # Manim 코드 생성
            ├── render_cnn_matrix.py  # CNN 시각화
            └── render_sorting.py     # 정렬 시각화
```

---

## 실행 방법

### 사전 요구사항
- Docker, Docker Compose
- AWS 계정 (S3 버킷: `gifpt-s3`, 리전: `ap-northeast-2`)
- OpenAI API Key
- MySQL (host.docker.internal:3306, DB명: `gifpt`)

### 환경변수 설정

프로젝트 루트에 `.env` 파일 생성:

```env
DB_USER=root
DB_PASSWORD=your_mysql_password

GIFPT_JWT_SECRET=your_jwt_secret

AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

OPENAI_API_KEY=your_openai_api_key
```

### 실행

```bash
# Shared 디렉토리 생성
mkdir -p shared/uploads shared/results

# 전체 서비스 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f worker
```

### 접속

- **API 서버**: `http://localhost` (Nginx → Spring :8080)
- **Django 직접**: `http://localhost:8000`

---

## 로컬 개발 (Spring Boot 단독 실행)

```bash
cd GIFPT-BE

# .env 생성
echo "DB_PASSWORD=your_password" > .env

# 실행
./gradlew bootRun

# 테스트
./gradlew test

# 빌드
./gradlew build
```

---

## AWS S3 설정 참고

- 버킷 정책: **BucketOwnerEnforced** (ACL 비활성화)
- ContentType 지정 필수:
  ```python
  s3.upload_file(local_path, bucket, key, ExtraArgs={"ContentType": "video/mp4"})
  ```

---

## 콜백 응답 형식

Worker → Spring 콜백:
```json
POST /api/v1/analysis/{jobId}/complete
{
  "status": "SUCCESS",
  "summary": "...",
  "resultUrl": "https://s3.amazonaws.com/gifpt-s3/....mp4",
  "errorMessage": null
}
```
