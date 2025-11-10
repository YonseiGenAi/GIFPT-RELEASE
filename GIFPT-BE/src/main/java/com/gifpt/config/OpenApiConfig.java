package com.gifpt.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {
    @Bean
    public OpenAPI api() {
        return new OpenAPI().info(
            new Info()
                .title("GIFPT")
                .description("알고리즘 자동 시각화 플랫폼 api 문서")
                .version("v1.0.0")
                .contact(new Contact().name("EHHO").email("ehho0916@yonsei.ac.kr"))
        );
    }
}
