package com.gifpt;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;

@SpringBootTest
@TestPropertySource(properties = {
	"spring.datasource.url=jdbc:h2:mem:testdb",
	"spring.datasource.driver-class-name=org.h2.Driver",
	"spring.jpa.database-platform=org.hibernate.dialect.H2Dialect",
	"spring.jpa.hibernate.ddl-auto=create-drop",
	"gifpt.jwt.secret=test-secret-key-for-testing-only-must-be-at-least-256-bits-long-for-hmac-sha",
	"gifpt.jwt.expires-in-ms=3600000",
	"openai.api.key=test-key",
	"gifpt.ai.base-url=http://localhost:8000",
	"gifpt.upload-dir=./test-uploads",
	"gifpt.ai-server.base-url=http://localhost:8000"
})
class GifptApplicationTests {

	@Test
	void contextLoads() {
	}

}
