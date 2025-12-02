
# GIFPT Server Infrastructure (Spring + Django + Worker + Nginx)

GIFPT는 **PDF 기반 학습 자료**를 AI로 분석하여  
**요약 + Manim 기반 애니메이션 영상**을 자동 생성하는 서비스입니다.  
본 문서는 전체 시스템 구성 요소와 데이터 흐름을 요약한 README입니다.

---

## 🚀 Architecture Overview

GIFPT 서버는 다음과 같은 멀티 컴포넌트 구조로 구성됩니다:

### **1) Spring Boot API Server**
- 유저 인증(JWT), 워크스페이스 관리, 파일 업로드
- 분석 Job 생성 및 Django/Worker 결과 콜백 처리
- RDS(MySQL)과 직접 연동

### **2) Django AI Server**
- Spring에서 전달된 PDF 분석 요청 처리
- Celery Worker에게 Vision 분석 작업 전달

### **3) Celery Worker (AI + Manim Pipeline)**
- PDF → 이미지 변환
- OpenAI Vision 기반 Summary/Video Instructions 생성
- Manim으로 MP4 애니메이션 렌더링
- S3 업로드 후 Spring API에 결과 콜백

### **4) Nginx Reverse Proxy**
- 외부 요청을 Spring으로 라우팅
- `/api/**`, `/swagger-ui/**` 요청 처리

### **5) Infrastructure Services**
- **Redis**: Celery 브로커
- **RabbitMQ**: Celery 큐
- **RDS(MySQL)**: Spring 영속 데이터 저장
- **S3**: Worker가 생성한 영상 저장  
- **Shared Volume**: Spring/Django/Worker 간 PDF·결과 파일 공유

---

## 🔄 End-to-End Flow

### **1. User → Spring**
- PDF 업로드  
- Workspace & AnalysisJob 생성  
- Django AI 서버에 `/analyze` 요청

### **2. Spring → Django**
- `{job_id, file_path, prompt}` 전달  
- Celery Worker에게 Task enqueue

### **3. Worker AI Pipeline**
- PDF 텍스트·이미지 추출  
- OpenAI Vision Summary 생성  
- Video Instructions 생성  
- Manim 영상 렌더링  
- S3에 업로드 후 URL 생성

### **4. Worker → Spring**
콜백 호출:
```
POST /api/v1/analysis/{jobId}/complete
{
  status: SUCCESS/FAILED,
  summary: "...",
  resultUrl: "https://s3/....mp4"
}
```

### **5. User → Spring**
- Workspace 조회 → 영상 & 요약 확인

---

## 📁 Shared Directory Structure

```
shared/
 ├─ uploads/   # 사용자 PDF 저장
 └─ results/   # 렌더링된 영상 임시 저장
```

---

## 🧱 Docker Compose 주요 구성

| 서비스 | 역할 |
|--------|------|
| **spring** | API 서버 (JWT, Workspace, Callback) |
| **django** | AI 분석 엔드포인트 |
| **worker** | Vision + Summary + Manim 렌더링 핵심 |
| **nginx** | Reverse Proxy |
| **redis** | Celery Broker |
| **rabbitmq** | Celery Queue |
| **rds** | Spring DB |
| **s3** | 영상 저장소 |

---

## ☁️ AWS S3 Upload Notes
- 버킷 정책: **BucketOwnerEnforced (ACL 금지)**  
- 업로드 시:
```
s3.upload_file(local_path, bucket, key, ExtraArgs={"ContentType": "video/mp4"})
```

---
