# 1) 빌드 단계
FROM gradle:8.10.2-jdk17 AS builder
WORKDIR /app
COPY . .
RUN gradle clean build -x test

# 2) 런타임 단계
FROM eclipse-temurin:17-jre-jammy
WORKDIR /app
# 빌드 산출물 이름 확인해서 맞춰라 (SNAPSHOT이면 와일드카드)
COPY --from=builder /app/build/libs/*SNAPSHOT.jar /app/app.jar
ENV JAVA_OPTS="-Xms256m -Xmx512m"
EXPOSE 8080
ENTRYPOINT ["sh","-c","java $JAVA_OPTS -Duser.timezone=Asia/Seoul -Dspring.profiles.active=${SPRING_PROFILES_ACTIVE:-prod} -jar /app/app.jar"]
