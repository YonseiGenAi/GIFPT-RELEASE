package com.gifpt.workspace.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
public class RestClientConfig {

    @Bean
    public RestClient restClient() {
        // 기본 RestClient 빈 (baseUrl 없이 생성)
        // 각 서비스에서 필요에 따라 baseUrl을 설정하거나 전체 URL을 사용할 수 있음
        return RestClient.create();
    }
}
