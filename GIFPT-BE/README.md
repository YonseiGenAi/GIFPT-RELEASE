# GIFPT-BE

GIFPT Backend Application

## 환경 설정

### .env 파일 생성

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
DB_PASSWORD=your_mysql_password
```

`DB_PASSWORD`에 실제 MySQL 비밀번호를 입력하세요.

### 데이터베이스 설정

- 데이터베이스명: `gifpt`
- 호스트: `localhost:3306`
- 사용자: `root`

## 실행

```bash
./gradlew bootRun
```

## 테스트

```bash
./gradlew test
```

## 빌드

```bash
./gradlew build
```