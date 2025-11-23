package com.gifpt.workspace.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
public class RestClientConfig {

    @Bean
    public RestClient workspaceRestClient() {
        // 도커 컴포즈 안에서 django 서비스 이름으로 접속
        // docker-compose.yml에서 django 서비스 이름이 'django' 이니까 이렇게 둠
        return RestClient.builder()
                .baseUrl("http://django:8000")   // 장고 서버 내부 주소
                .build();
    }
}
