package com.gifpt.healthcheck;

import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Map;

@RestController
public class HealthController {

    @GetMapping("/healthz")
    public ResponseEntity<Map<String, Object>> healthz() {
        Map<String, Object> body = Map.of(
                "status", "UP",
                "timestamp", Instant.now().toString()
        );

        return ResponseEntity.ok()
                // 프록시/클라이언트 캐싱 방지
                .cacheControl(CacheControl.noStore().mustRevalidate())
                .header("Pragma", "no-cache")
                .body(body);
    }
}
